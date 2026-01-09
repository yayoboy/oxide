"""
SQLite-based configuration storage for Oxide.

Replaces YAML file configuration with database storage for:
- Runtime configuration updates via UI
- Configuration versioning and history
- Thread-safe concurrent access
- API key encryption
"""
import sqlite3
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import threading
from contextlib import contextmanager
from cryptography.fernet import Fernet

from .logging import logger
from ..config.loader import (
    Config, ServiceConfig, RoutingRuleConfig, ExecutionConfig,
    ServiceType, APIType
)


class ConfigStorageSQLite:
    """
    Thread-safe configuration storage using SQLite.

    Provides database-backed configuration management with:
    - CRUD operations for services, routing rules, execution settings
    - API key encryption with Fernet
    - WAL mode for concurrent access
    - Configuration history and versioning
    """

    def __init__(self, storage_path: Optional[Path] = None, encryption_key: Optional[bytes] = None):
        """
        Initialize SQLite config storage.

        Args:
            storage_path: Path to SQLite database file (defaults to ~/.oxide/config.db)
            encryption_key: Encryption key for API keys (auto-generated if None)
        """
        if storage_path is None:
            storage_path = Path.home() / ".oxide" / "config.db"

        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Thread-local connections for thread safety
        self._local = threading.local()

        # Initialize logger first
        self.logger = logger.getChild("config_storage_sqlite")

        # Setup encryption for API keys
        self._setup_encryption(encryption_key)

        # Initialize database schema
        self._init_schema()

        self.logger.info(f"SQLite config storage initialized: {self.storage_path}")

    def _setup_encryption(self, encryption_key: Optional[bytes] = None):
        """Setup Fernet encryption for API keys."""
        if encryption_key is None:
            # Try to load from env var
            env_key = os.getenv("OXIDE_ENCRYPTION_KEY")
            if env_key:
                encryption_key = env_key.encode()
            else:
                # Try to load from file
                key_path = self.storage_path.parent / "encryption.key"
                if key_path.exists():
                    with open(key_path, 'rb') as f:
                        encryption_key = f.read()
                else:
                    # Generate new key and save
                    encryption_key = Fernet.generate_key()
                    with open(key_path, 'wb') as f:
                        f.write(encryption_key)
                    self.logger.info(f"Generated new encryption key: {key_path}")

        self.cipher = Fernet(encryption_key)

    @contextmanager
    def _get_connection(self):
        """Get thread-local database connection with WAL mode."""
        # Each thread gets its own connection
        if not hasattr(self._local, 'conn'):
            self._local.conn = sqlite3.connect(
                str(self.storage_path),
                check_same_thread=False
            )
            # Enable WAL mode for concurrent reads/writes
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            # Return dicts instead of tuples
            self._local.conn.row_factory = sqlite3.Row

        try:
            yield self._local.conn
        except Exception as e:
            self._local.conn.rollback()
            raise
        else:
            self._local.conn.commit()

    def _init_schema(self):
        """Initialize database schema with indexes."""
        with self._get_connection() as conn:
            # Services table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS services (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    type TEXT NOT NULL,
                    enabled BOOLEAN DEFAULT 1,

                    -- CLI specific
                    executable TEXT,

                    -- HTTP specific
                    base_url TEXT,
                    api_type TEXT,
                    api_key_encrypted TEXT,
                    default_model TEXT,

                    -- Common fields
                    max_context_tokens INTEGER,
                    capabilities TEXT,  -- JSON array
                    models TEXT,  -- JSON array

                    -- Advanced fields
                    preferred_models TEXT,  -- JSON array
                    fallback_models TEXT,  -- JSON array
                    use_free_only BOOLEAN,
                    max_retries INTEGER,
                    retry_delay INTEGER,
                    site_url TEXT,
                    site_name TEXT,
                    auto_start BOOLEAN,
                    auto_detect_model BOOLEAN,

                    -- Metadata
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,

                    -- Node association (NULL = local service)
                    node_id TEXT,
                    FOREIGN KEY (node_id) REFERENCES discovered_nodes(node_id) ON DELETE CASCADE
                )
            """)

            # Routing rules table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS routing_rules (
                    task_type TEXT PRIMARY KEY,
                    primary_service TEXT NOT NULL,
                    fallback_services TEXT,  -- JSON array
                    parallel_threshold_files INTEGER,
                    timeout_seconds INTEGER,

                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,

                    FOREIGN KEY (primary_service) REFERENCES services(id)
                )
            """)

            # Execution settings table (singleton)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS execution_settings (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    max_parallel_workers INTEGER DEFAULT 3,
                    timeout_seconds INTEGER DEFAULT 120,
                    streaming BOOLEAN DEFAULT 1,
                    retry_on_failure BOOLEAN DEFAULT 1,
                    max_retries INTEGER DEFAULT 2,
                    updated_at REAL NOT NULL
                )
            """)

            # Discovered nodes table (for cluster discovery persistence)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS discovered_nodes (
                    node_id TEXT PRIMARY KEY,
                    hostname TEXT NOT NULL,
                    ip_address TEXT NOT NULL,
                    port INTEGER NOT NULL,
                    services TEXT NOT NULL,  -- JSON: detailed service info with models/capabilities
                    cpu_percent REAL,
                    memory_percent REAL,
                    active_tasks INTEGER DEFAULT 0,
                    total_tasks INTEGER DEFAULT 0,
                    healthy BOOLEAN DEFAULT 1,
                    enabled BOOLEAN DEFAULT 1,  -- User can disable nodes from UI

                    -- Discovery metadata
                    first_seen REAL NOT NULL,
                    last_seen REAL NOT NULL,
                    oxide_version TEXT,
                    features TEXT,  -- JSON array: supported features

                    UNIQUE(ip_address, port)
                )
            """)

            # Configuration history table (for versioning)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS config_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_snapshot TEXT NOT NULL,  -- JSON snapshot of entire config
                    change_description TEXT,
                    created_at REAL NOT NULL
                )
            """)

            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_services_enabled ON services(enabled)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_services_type ON services(type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_services_node ON services(node_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_routing_primary ON routing_rules(primary_service)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_healthy ON discovered_nodes(healthy)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_enabled ON discovered_nodes(enabled)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_last_seen ON discovered_nodes(last_seen DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_history_created ON config_history(created_at DESC)")

            # Initialize execution_settings with defaults if empty
            count = conn.execute("SELECT COUNT(*) FROM execution_settings").fetchone()[0]
            if count == 0:
                conn.execute("""
                    INSERT INTO execution_settings (id, updated_at)
                    VALUES (1, ?)
                """, (datetime.now().timestamp(),))

    def has_config(self) -> bool:
        """Check if database has any configuration."""
        with self._get_connection() as conn:
            service_count = conn.execute("SELECT COUNT(*) FROM services").fetchone()[0]
            rule_count = conn.execute("SELECT COUNT(*) FROM routing_rules").fetchone()[0]
            return service_count > 0 or rule_count > 0

    # ==================== Services CRUD ====================

    def add_service(
        self,
        service_id: str,
        service_config: Dict[str, Any],
        node_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add a new service to configuration.

        Args:
            service_id: Unique service identifier
            service_config: Service configuration dict
            node_id: Optional node association for remote services

        Returns:
            Created service record
        """
        now = datetime.now().timestamp()

        # Extract and encrypt API key if present
        api_key_encrypted = None
        if 'api_key' in service_config and service_config['api_key']:
            api_key_encrypted = self._encrypt_api_key(service_config['api_key'])

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO services (
                    id, name, type, enabled,
                    executable, base_url, api_type, api_key_encrypted, default_model,
                    max_context_tokens, capabilities, models,
                    preferred_models, fallback_models, use_free_only,
                    max_retries, retry_delay, site_url, site_name,
                    auto_start, auto_detect_model,
                    created_at, updated_at, node_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                service_id,
                service_config.get('name', service_id),
                service_config['type'],
                service_config.get('enabled', True),
                service_config.get('executable'),
                service_config.get('base_url'),
                service_config.get('api_type'),
                api_key_encrypted,
                service_config.get('default_model'),
                service_config.get('max_context_tokens'),
                json.dumps(service_config.get('capabilities', [])),
                json.dumps(service_config.get('models', [])),
                json.dumps(service_config.get('preferred_models', [])),
                json.dumps(service_config.get('fallback_models', [])),
                service_config.get('use_free_only'),
                service_config.get('max_retries'),
                service_config.get('retry_delay'),
                service_config.get('site_url'),
                service_config.get('site_name'),
                service_config.get('auto_start'),
                service_config.get('auto_detect_model'),
                now,
                now,
                node_id
            ))

        self.logger.info(f"Added service: {service_id}")
        return self.get_service(service_id)

    def get_service(self, service_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific service by ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM services WHERE id = ?",
                (service_id,)
            ).fetchone()

            if not row:
                return None

            return self._service_row_to_dict(row)

    def list_services(
        self,
        enabled_only: bool = False,
        node_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List all services with optional filtering.

        Args:
            enabled_only: Only return enabled services
            node_id: Filter by node association (None = local services)

        Returns:
            List of service records
        """
        with self._get_connection() as conn:
            query = "SELECT * FROM services WHERE 1=1"
            params = []

            if enabled_only:
                query += " AND enabled = 1"

            if node_id is not None:
                query += " AND node_id = ?"
                params.append(node_id)
            else:
                # Local services only
                query += " AND node_id IS NULL"

            query += " ORDER BY created_at ASC"

            rows = conn.execute(query, params).fetchall()
            return [self._service_row_to_dict(row) for row in rows]

    def update_service(
        self,
        service_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update service fields.

        Args:
            service_id: Service identifier
            updates: Dict of fields to update

        Returns:
            Updated service record or None if not found
        """
        with self._get_connection() as conn:
            # Check if service exists
            exists = conn.execute(
                "SELECT COUNT(*) FROM services WHERE id = ?",
                (service_id,)
            ).fetchone()[0]

            if not exists:
                self.logger.warning(f"Service not found: {service_id}")
                return None

            # Build update query
            set_clauses = []
            params = []

            # Handle API key encryption
            if 'api_key' in updates:
                updates['api_key_encrypted'] = self._encrypt_api_key(updates.pop('api_key'))

            # Handle JSON fields
            json_fields = ['capabilities', 'models', 'preferred_models', 'fallback_models']
            for field in json_fields:
                if field in updates:
                    updates[field] = json.dumps(updates[field])

            for key, value in updates.items():
                set_clauses.append(f"{key} = ?")
                params.append(value)

            # Always update updated_at
            set_clauses.append("updated_at = ?")
            params.append(datetime.now().timestamp())

            params.append(service_id)

            query = f"UPDATE services SET {', '.join(set_clauses)} WHERE id = ?"
            conn.execute(query, params)

        self.logger.info(f"Updated service: {service_id}")
        return self.get_service(service_id)

    def delete_service(self, service_id: str) -> bool:
        """
        Delete a service from configuration.

        Args:
            service_id: Service identifier

        Returns:
            True if deleted, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM services WHERE id = ?",
                (service_id,)
            )
            deleted = cursor.rowcount > 0

        if deleted:
            self.logger.info(f"Deleted service: {service_id}")

        return deleted

    # ==================== Routing Rules CRUD ====================

    def add_routing_rule(
        self,
        task_type: str,
        rule_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add or update a routing rule."""
        now = datetime.now().timestamp()

        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO routing_rules (
                    task_type, primary_service, fallback_services,
                    parallel_threshold_files, timeout_seconds,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?,
                    COALESCE((SELECT created_at FROM routing_rules WHERE task_type = ?), ?),
                    ?)
            """, (
                task_type,
                rule_config['primary'],
                json.dumps(rule_config.get('fallback', [])),
                rule_config.get('parallel_threshold_files'),
                rule_config.get('timeout_seconds'),
                task_type,  # For COALESCE to preserve created_at
                now,
                now
            ))

        self.logger.info(f"Added/updated routing rule: {task_type}")
        return self.get_routing_rule(task_type)

    def get_routing_rule(self, task_type: str) -> Optional[Dict[str, Any]]:
        """Get a specific routing rule by task type."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM routing_rules WHERE task_type = ?",
                (task_type,)
            ).fetchone()

            if not row:
                return None

            return self._routing_rule_row_to_dict(row)

    def list_routing_rules(self) -> List[Dict[str, Any]]:
        """List all routing rules."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM routing_rules ORDER BY task_type ASC"
            ).fetchall()
            return [self._routing_rule_row_to_dict(row) for row in rows]

    def delete_routing_rule(self, task_type: str) -> bool:
        """Delete a routing rule."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM routing_rules WHERE task_type = ?",
                (task_type,)
            )
            deleted = cursor.rowcount > 0

        if deleted:
            self.logger.info(f"Deleted routing rule: {task_type}")

        return deleted

    # ==================== Execution Settings ====================

    def get_execution_settings(self) -> Dict[str, Any]:
        """Get execution settings (singleton)."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM execution_settings WHERE id = 1"
            ).fetchone()

            return {
                'max_parallel_workers': row['max_parallel_workers'],
                'timeout_seconds': row['timeout_seconds'],
                'streaming': bool(row['streaming']),
                'retry_on_failure': bool(row['retry_on_failure']),
                'max_retries': row['max_retries'],
                'updated_at': row['updated_at']
            }

    def update_execution_settings(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update execution settings."""
        with self._get_connection() as conn:
            set_clauses = []
            params = []

            for key in ['max_parallel_workers', 'timeout_seconds', 'streaming', 'retry_on_failure', 'max_retries']:
                if key in updates:
                    set_clauses.append(f"{key} = ?")
                    params.append(updates[key])

            set_clauses.append("updated_at = ?")
            params.append(datetime.now().timestamp())

            query = f"UPDATE execution_settings SET {', '.join(set_clauses)} WHERE id = 1"
            conn.execute(query, params)

        self.logger.info("Updated execution settings")
        return self.get_execution_settings()

    # ==================== Full Config Load/Save ====================

    def load_config(self) -> Config:
        """
        Load complete configuration from database.

        Returns:
            Config object populated from database
        """
        services_dict = {}
        for service in self.list_services():
            service_id = service.pop('id')
            service.pop('created_at')
            service.pop('updated_at')
            service.pop('node_id')
            service.pop('name', None)

            # Convert to ServiceConfig
            services_dict[service_id] = ServiceConfig(**service)

        routing_rules_dict = {}
        for rule in self.list_routing_rules():
            task_type = rule.pop('task_type')
            rule.pop('created_at')
            rule.pop('updated_at')

            # Convert to RoutingRuleConfig
            routing_rules_dict[task_type] = RoutingRuleConfig(**rule)

        exec_settings = self.get_execution_settings()
        exec_settings.pop('updated_at')
        execution_config = ExecutionConfig(**exec_settings)

        return Config(
            services=services_dict,
            routing_rules=routing_rules_dict,
            execution=execution_config
        )

    def save_config_snapshot(self, description: str = "Manual save"):
        """
        Save a snapshot of current configuration to history.

        Args:
            description: Description of changes
        """
        config = self.load_config()
        snapshot = config.model_dump(mode="json")

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO config_history (config_snapshot, change_description, created_at)
                VALUES (?, ?, ?)
            """, (
                json.dumps(snapshot),
                description,
                datetime.now().timestamp()
            ))

        self.logger.info(f"Saved config snapshot: {description}")

    # ==================== Helper Methods ====================

    def _encrypt_api_key(self, api_key: str) -> str:
        """Encrypt API key using Fernet."""
        return self.cipher.encrypt(api_key.encode()).decode()

    def _decrypt_api_key(self, encrypted: str) -> str:
        """Decrypt API key using Fernet."""
        return self.cipher.decrypt(encrypted.encode()).decode()

    def _service_row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert SQLite row to service dictionary."""
        service_dict = {
            'id': row['id'],
            'name': row['name'],
            'type': row['type'],
            'enabled': bool(row['enabled']),
            'executable': row['executable'],
            'base_url': row['base_url'],
            'api_type': row['api_type'],
            'default_model': row['default_model'],
            'max_context_tokens': row['max_context_tokens'],
            'capabilities': json.loads(row['capabilities']) if row['capabilities'] else [],
            'models': json.loads(row['models']) if row['models'] else [],
            'preferred_models': json.loads(row['preferred_models']) if row['preferred_models'] else [],
            'fallback_models': json.loads(row['fallback_models']) if row['fallback_models'] else [],
            'use_free_only': bool(row['use_free_only']) if row['use_free_only'] is not None else None,
            'max_retries': row['max_retries'],
            'retry_delay': row['retry_delay'],
            'site_url': row['site_url'],
            'site_name': row['site_name'],
            'auto_start': bool(row['auto_start']) if row['auto_start'] is not None else None,
            'auto_detect_model': bool(row['auto_detect_model']) if row['auto_detect_model'] is not None else None,
            'created_at': row['created_at'],
            'updated_at': row['updated_at'],
            'node_id': row['node_id']
        }

        # Decrypt API key if present
        if row['api_key_encrypted']:
            service_dict['api_key'] = self._decrypt_api_key(row['api_key_encrypted'])

        return service_dict

    def _routing_rule_row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert SQLite row to routing rule dictionary."""
        return {
            'task_type': row['task_type'],
            'primary': row['primary_service'],
            'fallback': json.loads(row['fallback_services']) if row['fallback_services'] else [],
            'parallel_threshold_files': row['parallel_threshold_files'],
            'timeout_seconds': row['timeout_seconds'],
            'created_at': row['created_at'],
            'updated_at': row['updated_at']
        }

    # ==================== Discovered Nodes Management ====================

    def upsert_node(self, node_data: Dict[str, Any]) -> None:
        """
        Insert or update a discovered node.

        Args:
            node_data: Node information dictionary with keys:
                - node_id: Unique node identifier
                - hostname: Node hostname
                - ip_address: Node IP address
                - port: Node port
                - services: Dict with detailed service info (will be JSON serialized)
                - cpu_percent: CPU usage percentage
                - memory_percent: Memory usage percentage
                - active_tasks: Number of active tasks
                - total_tasks: Total tasks processed
                - healthy: Node health status
                - oxide_version: Oxide version string
                - features: List of supported features (will be JSON serialized)
        """
        conn = self._get_connection()
        now = time.time()

        # Serialize complex fields
        services_json = json.dumps(node_data.get('services', {}))
        features_json = json.dumps(node_data.get('features', []))

        # Check if node already exists
        existing = conn.execute(
            "SELECT first_seen, enabled FROM discovered_nodes WHERE node_id = ?",
            (node_data['node_id'],)
        ).fetchone()

        if existing:
            # Update existing node, preserve first_seen and enabled
            conn.execute("""
                UPDATE discovered_nodes SET
                    hostname = ?,
                    ip_address = ?,
                    port = ?,
                    services = ?,
                    cpu_percent = ?,
                    memory_percent = ?,
                    active_tasks = ?,
                    total_tasks = ?,
                    healthy = ?,
                    last_seen = ?,
                    oxide_version = ?,
                    features = ?
                WHERE node_id = ?
            """, (
                node_data['hostname'],
                node_data['ip_address'],
                node_data['port'],
                services_json,
                node_data.get('cpu_percent', 0.0),
                node_data.get('memory_percent', 0.0),
                node_data.get('active_tasks', 0),
                node_data.get('total_tasks', 0),
                node_data.get('healthy', True),
                now,
                node_data.get('oxide_version'),
                features_json,
                node_data['node_id']
            ))
        else:
            # Insert new node
            conn.execute("""
                INSERT INTO discovered_nodes (
                    node_id, hostname, ip_address, port, services,
                    cpu_percent, memory_percent, active_tasks, total_tasks,
                    healthy, enabled, first_seen, last_seen,
                    oxide_version, features
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                node_data['node_id'],
                node_data['hostname'],
                node_data['ip_address'],
                node_data['port'],
                services_json,
                node_data.get('cpu_percent', 0.0),
                node_data.get('memory_percent', 0.0),
                node_data.get('active_tasks', 0),
                node_data.get('total_tasks', 0),
                node_data.get('healthy', True),
                True,  # enabled by default
                now,
                now,
                node_data.get('oxide_version'),
                features_json
            ))

        conn.commit()
        self.logger.debug(f"Upserted node: {node_data['node_id']}")

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a discovered node by ID.

        Args:
            node_id: Node identifier

        Returns:
            Node data dictionary or None if not found
        """
        conn = self._get_connection()
        row = conn.execute(
            "SELECT * FROM discovered_nodes WHERE node_id = ?",
            (node_id,)
        ).fetchone()

        if not row:
            return None

        return self._node_row_to_dict(row)

    def list_nodes(
        self,
        enabled_only: bool = False,
        healthy_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        List all discovered nodes.

        Args:
            enabled_only: Only return enabled nodes
            healthy_only: Only return healthy nodes

        Returns:
            List of node data dictionaries
        """
        conn = self._get_connection()

        query = "SELECT * FROM discovered_nodes WHERE 1=1"
        params = []

        if enabled_only:
            query += " AND enabled = ?"
            params.append(True)

        if healthy_only:
            query += " AND healthy = ?"
            params.append(True)

        query += " ORDER BY last_seen DESC"

        rows = conn.execute(query, params).fetchall()
        return [self._node_row_to_dict(row) for row in rows]

    def enable_node(self, node_id: str) -> bool:
        """
        Enable a discovered node.

        Args:
            node_id: Node identifier

        Returns:
            True if node was found and enabled, False otherwise
        """
        conn = self._get_connection()
        cursor = conn.execute(
            "UPDATE discovered_nodes SET enabled = ? WHERE node_id = ?",
            (True, node_id)
        )
        conn.commit()

        if cursor.rowcount > 0:
            self.logger.info(f"Enabled node: {node_id}")
            return True

        return False

    def disable_node(self, node_id: str) -> bool:
        """
        Disable a discovered node.

        Args:
            node_id: Node identifier

        Returns:
            True if node was found and disabled, False otherwise
        """
        conn = self._get_connection()
        cursor = conn.execute(
            "UPDATE discovered_nodes SET enabled = ? WHERE node_id = ?",
            (False, node_id)
        )
        conn.commit()

        if cursor.rowcount > 0:
            self.logger.info(f"Disabled node: {node_id}")
            return True

        return False

    def prune_stale_nodes(self, max_age_seconds: int = 300) -> int:
        """
        Remove nodes that haven't been seen recently.

        Args:
            max_age_seconds: Maximum age in seconds (default: 5 minutes)

        Returns:
            Number of nodes removed
        """
        conn = self._get_connection()
        cutoff_time = time.time() - max_age_seconds

        cursor = conn.execute(
            "DELETE FROM discovered_nodes WHERE last_seen < ?",
            (cutoff_time,)
        )
        conn.commit()

        if cursor.rowcount > 0:
            self.logger.info(f"Pruned {cursor.rowcount} stale nodes")

        return cursor.rowcount

    def delete_node(self, node_id: str) -> bool:
        """
        Delete a discovered node.

        Args:
            node_id: Node identifier

        Returns:
            True if node was found and deleted, False otherwise
        """
        conn = self._get_connection()
        cursor = conn.execute(
            "DELETE FROM discovered_nodes WHERE node_id = ?",
            (node_id,)
        )
        conn.commit()

        if cursor.rowcount > 0:
            self.logger.info(f"Deleted node: {node_id}")
            return True

        return False

    def _node_row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert SQLite row to node dictionary."""
        return {
            'node_id': row['node_id'],
            'hostname': row['hostname'],
            'ip_address': row['ip_address'],
            'port': row['port'],
            'services': json.loads(row['services']) if row['services'] else {},
            'cpu_percent': row['cpu_percent'],
            'memory_percent': row['memory_percent'],
            'active_tasks': row['active_tasks'],
            'total_tasks': row['total_tasks'],
            'healthy': bool(row['healthy']),
            'enabled': bool(row['enabled']),
            'first_seen': row['first_seen'],
            'last_seen': row['last_seen'],
            'oxide_version': row['oxide_version'],
            'features': json.loads(row['features']) if row['features'] else []
        }

    def close(self):
        """Close database connection."""
        if hasattr(self._local, 'conn'):
            self._local.conn.close()
            delattr(self._local, 'conn')


# Global singleton instance
_config_storage_sqlite: Optional[ConfigStorageSQLite] = None


def get_config_storage_sqlite() -> ConfigStorageSQLite:
    """Get the global ConfigStorageSQLite instance."""
    global _config_storage_sqlite
    if _config_storage_sqlite is None:
        _config_storage_sqlite = ConfigStorageSQLite()
    return _config_storage_sqlite
