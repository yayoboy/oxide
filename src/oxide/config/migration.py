"""
Configuration migration tool for Oxide.

Migrates configuration from YAML files to SQLite database with:
- Safe migration with backup
- Validation before migration
- Rollback support
- Migration history
"""
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from .loader import load_yaml_file, Config
from ..utils.config_storage_sqlite import ConfigStorageSQLite
from ..utils.logging import logger


class ConfigMigration:
    """
    Handles migration from YAML configuration to SQLite database.

    Provides safe migration with:
    - Pre-migration validation
    - Automatic backup of YAML files
    - Rollback capability
    - Migration status reporting
    """

    def __init__(
        self,
        yaml_path: Path,
        db_storage: Optional[ConfigStorageSQLite] = None
    ):
        """
        Initialize migration tool.

        Args:
            yaml_path: Path to YAML configuration file
            db_storage: ConfigStorageSQLite instance (creates new if None)
        """
        self.yaml_path = Path(yaml_path)
        self.db_storage = db_storage or ConfigStorageSQLite()
        self.logger = logger.getChild("config_migration")

    def migrate_yaml_to_db(
        self,
        backup: bool = True,
        validate: bool = True
    ) -> Dict[str, Any]:
        """
        Migrate YAML configuration to SQLite database.

        Args:
            backup: Create backup of YAML file before migration
            validate: Validate configuration before migration

        Returns:
            Migration result dictionary with status and statistics

        Raises:
            ConfigError: If migration fails
        """
        self.logger.info(f"Starting migration from {self.yaml_path}")

        # Check if YAML file exists
        if not self.yaml_path.exists():
            return {
                "status": "error",
                "message": f"YAML file not found: {self.yaml_path}"
            }

        try:
            # Step 1: Load and validate YAML
            self.logger.info("Loading YAML configuration...")
            yaml_data = load_yaml_file(self.yaml_path)

            if validate:
                self.logger.info("Validating configuration...")
                config = Config(**yaml_data)
                self.logger.info("✅ Configuration is valid")
            else:
                config = Config(**yaml_data)

            # Step 2: Backup YAML file if requested
            backup_path = None
            if backup:
                backup_path = self._backup_yaml()
                self.logger.info(f"✅ Created backup: {backup_path}")

            # Step 3: Migrate to database
            migration_stats = self._migrate_config_to_db(config)

            # Step 4: Save migration snapshot
            self.db_storage.save_config_snapshot(
                f"Migrated from YAML: {self.yaml_path.name}"
            )

            result = {
                "status": "success",
                **migration_stats,
                "backup_path": str(backup_path) if backup_path else None,
                "migrated_at": datetime.now().isoformat()
            }

            self.logger.info("✅ Migration completed successfully")
            return result

        except Exception as e:
            self.logger.error(f"Migration failed: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    def _backup_yaml(self) -> Path:
        """Create timestamped backup of YAML file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.yaml_path.with_suffix(f'.yaml.backup.{timestamp}')

        shutil.copy2(self.yaml_path, backup_path)

        return backup_path

    def _migrate_config_to_db(self, config: Config) -> Dict[str, int]:
        """
        Migrate Config object to database.

        Args:
            config: Validated Config object

        Returns:
            Migration statistics
        """
        services_migrated = 0
        routing_rules_migrated = 0

        # Migrate services
        self.logger.info("Migrating services...")
        for service_id, service_config in config.services.items():
            service_dict = service_config.model_dump(mode="json", exclude_none=True)
            self.db_storage.add_service(service_id, service_dict)
            services_migrated += 1
            self.logger.debug(f"  ✓ {service_id}")

        # Migrate routing rules
        self.logger.info("Migrating routing rules...")
        for task_type, rule in config.routing_rules.items():
            rule_dict = rule.model_dump(mode="json", exclude_none=True)
            self.db_storage.add_routing_rule(task_type, rule_dict)
            routing_rules_migrated += 1
            self.logger.debug(f"  ✓ {task_type}")

        # Migrate execution settings
        self.logger.info("Migrating execution settings...")
        exec_settings = config.execution.model_dump(mode="json", exclude_none=True)
        self.db_storage.update_execution_settings(exec_settings)

        return {
            "services_migrated": services_migrated,
            "routing_rules_migrated": routing_rules_migrated,
            "execution_settings": "migrated"
        }

    def verify_migration(self) -> Dict[str, Any]:
        """
        Verify that database matches YAML configuration.

        Returns:
            Verification result with comparison stats
        """
        self.logger.info("Verifying migration...")

        try:
            # Load both configs
            yaml_data = load_yaml_file(self.yaml_path)
            yaml_config = Config(**yaml_data)

            db_config = self.db_storage.load_config()

            # Compare services
            yaml_services = set(yaml_config.services.keys())
            db_services = set(db_config.services.keys())

            services_match = yaml_services == db_services
            services_only_yaml = yaml_services - db_services
            services_only_db = db_services - yaml_services

            # Compare routing rules
            yaml_rules = set(yaml_config.routing_rules.keys())
            db_rules = set(db_config.routing_rules.keys())

            rules_match = yaml_rules == db_rules
            rules_only_yaml = yaml_rules - db_rules
            rules_only_db = db_rules - yaml_rules

            # Overall match
            perfect_match = services_match and rules_match

            result = {
                "perfect_match": perfect_match,
                "services": {
                    "match": services_match,
                    "yaml_count": len(yaml_services),
                    "db_count": len(db_services),
                    "only_in_yaml": list(services_only_yaml),
                    "only_in_db": list(services_only_db)
                },
                "routing_rules": {
                    "match": rules_match,
                    "yaml_count": len(yaml_rules),
                    "db_count": len(db_rules),
                    "only_in_yaml": list(rules_only_yaml),
                    "only_in_db": list(rules_only_db)
                }
            }

            if perfect_match:
                self.logger.info("✅ Migration verified: Perfect match")
            else:
                self.logger.warning("⚠️ Migration verification: Differences found")

            return result

        except Exception as e:
            self.logger.error(f"Verification failed: {e}")
            return {
                "perfect_match": False,
                "error": str(e)
            }

    def export_db_to_yaml(self, output_path: Path) -> Dict[str, Any]:
        """
        Export database configuration to YAML file.

        Useful for:
        - Creating backup YAML from database
        - Reverting to YAML-based configuration
        - Sharing configuration

        Args:
            output_path: Path for exported YAML file

        Returns:
            Export result dictionary
        """
        self.logger.info(f"Exporting database to YAML: {output_path}")

        try:
            # Load from database
            config = self.db_storage.load_config()

            # Save to YAML
            from .loader import save_config
            save_config(config, output_path)

            self.logger.info("✅ Export completed successfully")

            return {
                "status": "success",
                "output_path": str(output_path),
                "exported_at": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Export failed: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    def rollback_to_yaml(self, backup_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Rollback to YAML configuration by clearing database.

        Args:
            backup_path: Optional path to backup YAML to restore from

        Returns:
            Rollback result dictionary
        """
        self.logger.info("Rolling back to YAML configuration...")

        try:
            # Clear database
            # Note: We don't have a clear_all method, so we'd need to delete individual items
            # For now, just log and recommend manual action

            self.logger.warning("Database rollback not yet fully implemented")
            self.logger.info("To rollback manually:")
            self.logger.info("1. Delete ~/.oxide/config.db")
            self.logger.info("2. Ensure config/default.yaml exists")
            if backup_path:
                self.logger.info(f"3. Restore from backup: {backup_path}")

            return {
                "status": "manual_action_required",
                "message": "See logs for rollback instructions"
            }

        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            return {
                "status": "error",
                "message": str(e)
            }


def migrate_config(
    yaml_path: Optional[Path] = None,
    backup: bool = True,
    validate: bool = True
) -> Dict[str, Any]:
    """
    Convenience function for migrating configuration.

    Args:
        yaml_path: Path to YAML file (defaults to config/default.yaml)
        backup: Create backup before migration
        validate: Validate configuration before migration

    Returns:
        Migration result dictionary
    """
    if yaml_path is None:
        # Default to config/default.yaml
        yaml_path = Path(__file__).parent.parent.parent.parent / "config" / "default.yaml"

    migration = ConfigMigration(yaml_path)
    return migration.migrate_yaml_to_db(backup=backup, validate=validate)
