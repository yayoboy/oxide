"""
Cluster Coordinator for Multi-Machine Task Distribution

Enables multiple Oxide instances to cooperate and distribute tasks:
- Service discovery via mDNS/broadcast
- Load-based task routing
- Remote task execution
- Result synchronization
"""
import asyncio
import socket
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

from ..utils.logging import get_logger
from ..utils.task_storage import get_task_storage
from ..utils.config_storage_sqlite import ConfigStorageSQLite

logger = get_logger(__name__)


@dataclass
class NodeInfo:
    """Information about a cluster node"""
    node_id: str
    hostname: str
    ip_address: str
    port: int
    services: Dict[str, Dict[str, Any]]  # Service name -> detailed info (models, capabilities, etc.)
    cpu_percent: float
    memory_percent: float
    active_tasks: int
    total_tasks: int
    last_seen: float
    healthy: bool = True
    enabled: bool = True  # Can be disabled from UI
    oxide_version: Optional[str] = None
    features: List[str] = None  # Supported features

    def __post_init__(self):
        """Initialize default values"""
        if self.features is None:
            self.features = []


class ClusterCoordinator:
    """
    Coordinates task distribution across multiple Oxide instances.

    Features:
    - Auto-discover Oxide instances on LAN
    - Load-aware task routing
    - Remote task execution
    - Health monitoring
    """

    def __init__(
        self,
        node_id: str,
        broadcast_port: int = 8888,
        api_port: int = 8000,
        discovery_interval: int = 30
    ):
        """
        Initialize cluster coordinator.

        Args:
            node_id: Unique identifier for this node
            broadcast_port: Port for discovery broadcasts
            api_port: Port for Oxide API
            discovery_interval: Seconds between discovery broadcasts
        """
        self.logger = get_logger(__name__)
        self.node_id = node_id
        self.broadcast_port = broadcast_port
        self.api_port = api_port
        self.discovery_interval = discovery_interval

        # Cluster state
        self.nodes: Dict[str, NodeInfo] = {}
        self.local_node: Optional[NodeInfo] = None

        # Discovery tasks
        self._discovery_task: Optional[asyncio.Task] = None
        self._broadcast_task: Optional[asyncio.Task] = None
        self._health_check_task: Optional[asyncio.Task] = None

        # SQLite persistence for discovered nodes
        self.config_storage = ConfigStorageSQLite()

        self.logger.info(f"Cluster coordinator initialized: {node_id}")

    async def start(self, orchestrator):
        """
        Start cluster coordination.

        Args:
            orchestrator: Local Orchestrator instance
        """
        # Create local node info
        self.local_node = await self._create_local_node_info(orchestrator)

        # Load previously discovered nodes from database
        await self._load_persisted_nodes()

        # Start background tasks
        self._discovery_task = asyncio.create_task(self._listen_for_nodes())
        self._broadcast_task = asyncio.create_task(self._broadcast_presence())
        self._health_check_task = asyncio.create_task(self._monitor_node_health())

        self.logger.info("Cluster coordinator started")

    async def stop(self):
        """Stop cluster coordination"""
        if self._discovery_task:
            self._discovery_task.cancel()
        if self._broadcast_task:
            self._broadcast_task.cancel()
        if self._health_check_task:
            self._health_check_task.cancel()

        self.logger.info("Cluster coordinator stopped")

    async def _create_local_node_info(self, orchestrator) -> NodeInfo:
        """Create NodeInfo for local instance with detailed service information"""
        import psutil

        # Get local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip_address = s.getsockname()[0]
        except Exception:
            ip_address = "127.0.0.1"
        finally:
            s.close()

        # Get detailed service information
        services = {}
        if orchestrator:
            for service_name, adapter in orchestrator.adapters.items():
                service_info = {
                    "type": getattr(adapter, "adapter_type", "unknown"),
                    "models": [],
                    "capabilities": [],
                    "base_url": None
                }

                # Try to get models list
                if hasattr(adapter, "get_available_models"):
                    try:
                        service_info["models"] = await adapter.get_available_models()
                    except:
                        pass

                # Get capabilities from config if available
                if hasattr(adapter, "config"):
                    service_info["capabilities"] = getattr(adapter.config, "capabilities", [])

                # Get base URL for HTTP adapters
                if hasattr(adapter, "base_url"):
                    service_info["base_url"] = adapter.base_url

                services[service_name] = service_info

        # Get Oxide version
        try:
            import importlib.metadata
            oxide_version = importlib.metadata.version("oxide")
        except:
            oxide_version = "unknown"

        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory_percent = psutil.virtual_memory().percent

        # Get task counts
        task_storage = get_task_storage()
        tasks = task_storage.get_all_tasks()
        active_tasks = len([t for t in tasks if t.get("status") == "running"])

        # Define supported features
        features = [
            "cluster_discovery",
            "remote_execution",
            "load_balancing",
            "persistent_discovery"
        ]

        return NodeInfo(
            node_id=self.node_id,
            hostname=socket.gethostname(),
            ip_address=ip_address,
            port=self.api_port,
            services=services,
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            active_tasks=active_tasks,
            total_tasks=len(tasks),
            last_seen=time.time(),
            healthy=True,
            oxide_version=oxide_version,
            features=features
        )

    async def _load_persisted_nodes(self):
        """Load previously discovered nodes from database"""
        try:
            persisted_nodes = self.config_storage.list_nodes(enabled_only=True)

            for node_data in persisted_nodes:
                # Skip ourselves
                if node_data['node_id'] == self.node_id:
                    continue

                # Create NodeInfo from persisted data
                node = NodeInfo(
                    node_id=node_data['node_id'],
                    hostname=node_data['hostname'],
                    ip_address=node_data['ip_address'],
                    port=node_data['port'],
                    services=node_data['services'],
                    cpu_percent=node_data['cpu_percent'],
                    memory_percent=node_data['memory_percent'],
                    active_tasks=node_data['active_tasks'],
                    total_tasks=node_data['total_tasks'],
                    last_seen=node_data['last_seen'],
                    healthy=node_data['healthy'],
                    enabled=node_data['enabled'],
                    oxide_version=node_data.get('oxide_version'),
                    features=node_data.get('features', [])
                )

                self.nodes[node.node_id] = node
                self.logger.info(f"Loaded persisted node: {node.hostname} ({node.ip_address})")

            if persisted_nodes:
                self.logger.info(f"Loaded {len(persisted_nodes)} persisted nodes from database")
        except Exception as e:
            self.logger.warning(f"Failed to load persisted nodes: {e}")

    async def _broadcast_presence(self):
        """Broadcast local node presence to LAN"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        try:
            while True:
                if self.local_node:
                    # Update local node stats
                    import psutil
                    self.local_node.cpu_percent = psutil.cpu_percent(interval=0.1)
                    self.local_node.memory_percent = psutil.virtual_memory().percent
                    self.local_node.last_seen = time.time()

                    # Update task counts
                    task_storage = get_task_storage()
                    tasks = task_storage.get_all_tasks()
                    self.local_node.active_tasks = len([t for t in tasks if t.get("status") == "running"])
                    self.local_node.total_tasks = len(tasks)

                    # Broadcast
                    message = {
                        "type": "oxide_node",
                        "node": asdict(self.local_node)
                    }
                    data = json.dumps(message).encode()

                    try:
                        sock.sendto(data, ("<broadcast>", self.broadcast_port))
                        self.logger.debug(f"Broadcasted presence to port {self.broadcast_port}")
                    except Exception as e:
                        self.logger.warning(f"Failed to broadcast presence: {e}")

                await asyncio.sleep(self.discovery_interval)

        except asyncio.CancelledError:
            self.logger.info("Broadcast task cancelled")
        finally:
            sock.close()

    async def _listen_for_nodes(self):
        """Listen for node discovery broadcasts"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", self.broadcast_port))
        sock.setblocking(False)

        try:
            while True:
                try:
                    data, addr = await asyncio.get_event_loop().sock_recvfrom(sock, 4096)
                    message = json.loads(data.decode())

                    if message.get("type") == "oxide_node":
                        node_data = message["node"]
                        node_id = node_data["node_id"]

                        # Don't add ourselves
                        if node_id == self.node_id:
                            continue

                        # Update or add node in memory
                        node = NodeInfo(**node_data)
                        self.nodes[node_id] = node

                        # Persist to database
                        try:
                            self.config_storage.upsert_node(node_data)
                        except Exception as e:
                            self.logger.warning(f"Failed to persist node {node.hostname}: {e}")

                        self.logger.debug(f"Discovered node: {node.hostname} ({node.ip_address})")

                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    self.logger.debug(f"Error receiving broadcast: {e}")

                await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            self.logger.info("Discovery task cancelled")
        finally:
            sock.close()

    async def _monitor_node_health(self):
        """Monitor health of discovered nodes and prune stale entries"""
        try:
            while True:
                current_time = time.time()
                timeout = self.discovery_interval * 3  # 3 missed broadcasts

                # Mark nodes as unhealthy if not seen recently
                for node_id, node in list(self.nodes.items()):
                    if current_time - node.last_seen > timeout:
                        if node.healthy:
                            self.logger.warning(f"Node {node.hostname} appears offline")
                            node.healthy = False

                        # Remove if offline for too long
                        if current_time - node.last_seen > timeout * 2:
                            self.logger.info(f"Removing offline node: {node.hostname}")
                            del self.nodes[node_id]

                # Prune stale nodes from database (6 missed broadcasts)
                try:
                    max_age_seconds = self.discovery_interval * 6
                    pruned_count = self.config_storage.prune_stale_nodes(max_age_seconds)
                    if pruned_count > 0:
                        self.logger.info(f"Pruned {pruned_count} stale nodes from database")
                except Exception as e:
                    self.logger.warning(f"Failed to prune stale nodes from database: {e}")

                await asyncio.sleep(self.discovery_interval)

        except asyncio.CancelledError:
            self.logger.info("Health check task cancelled")

    def get_cluster_status(self) -> Dict[str, Any]:
        """Get cluster status"""
        return {
            "local_node": asdict(self.local_node) if self.local_node else None,
            "cluster_nodes": [asdict(node) for node in self.nodes.values()],
            "total_nodes": len(self.nodes) + (1 if self.local_node else 0),
            "healthy_nodes": len([n for n in self.nodes.values() if n.healthy]) + (1 if self.local_node and self.local_node.healthy else 0)
        }

    def get_best_node_for_task(
        self,
        task_type: str,
        required_service: Optional[str] = None
    ) -> Optional[NodeInfo]:
        """
        Select best node for executing a task.

        Args:
            task_type: Type of task
            required_service: Specific service required

        Returns:
            Best node, or None if no suitable node found
        """
        candidates = []

        # Include local node
        if self.local_node and self.local_node.healthy:
            if not required_service or required_service in self.local_node.services:
                candidates.append(self.local_node)

        # Include remote nodes
        for node in self.nodes.values():
            if not node.healthy or not node.enabled:
                continue
            if required_service and required_service not in node.services:
                continue
            candidates.append(node)

        if not candidates:
            return None

        # Score nodes based on load
        def score_node(node: NodeInfo) -> float:
            # Lower score is better
            load_score = (node.cpu_percent + node.memory_percent) / 2
            task_score = node.active_tasks * 10
            return load_score + task_score

        best_node = min(candidates, key=score_node)

        self.logger.debug(
            f"Selected node for task: {best_node.hostname} "
            f"(CPU: {best_node.cpu_percent}%, Active: {best_node.active_tasks})"
        )

        return best_node

    async def execute_task_on_node(
        self,
        node: NodeInfo,
        prompt: str,
        files: Optional[List[str]] = None,
        preferences: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute task on a remote node.

        Args:
            node: Target node
            prompt: Task prompt
            files: Optional file paths
            preferences: Task preferences

        Returns:
            Task result
        """
        import aiohttp

        url = f"http://{node.ip_address}:{node.port}/api/tasks/execute"

        payload = {
            "prompt": prompt,
            "files": files or [],
            "preferences": preferences or {}
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=300)) as response:
                    if response.status == 200:
                        result = await response.json()
                        self.logger.info(f"Task completed on node: {node.hostname}")
                        return result
                    else:
                        error = await response.text()
                        self.logger.error(f"Task failed on node {node.hostname}: {error}")
                        return {"error": error, "status": "failed"}

        except Exception as e:
            self.logger.error(f"Failed to execute task on {node.hostname}: {e}")
            return {"error": str(e), "status": "failed"}

    def enable_node(self, node_id: str) -> bool:
        """
        Enable a discovered node.

        Args:
            node_id: Node identifier

        Returns:
            True if successful, False otherwise
        """
        try:
            # Enable in database
            if not self.config_storage.enable_node(node_id):
                return False

            # Enable in memory if present
            if node_id in self.nodes:
                self.nodes[node_id].enabled = True

            self.logger.info(f"Enabled node: {node_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to enable node {node_id}: {e}")
            return False

    def disable_node(self, node_id: str) -> bool:
        """
        Disable a discovered node.

        Args:
            node_id: Node identifier

        Returns:
            True if successful, False otherwise
        """
        try:
            # Disable in database
            if not self.config_storage.disable_node(node_id):
                return False

            # Disable in memory if present
            if node_id in self.nodes:
                self.nodes[node_id].enabled = False

            self.logger.info(f"Disabled node: {node_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to disable node {node_id}: {e}")
            return False

    def get_all_nodes(self) -> List[NodeInfo]:
        """
        Get all discovered nodes (including disabled ones).

        Returns:
            List of all NodeInfo objects
        """
        nodes = list(self.nodes.values())
        if self.local_node:
            nodes.insert(0, self.local_node)
        return nodes


# Global coordinator instance
_cluster_coordinator: Optional[ClusterCoordinator] = None


def get_cluster_coordinator() -> Optional[ClusterCoordinator]:
    """Get global cluster coordinator instance"""
    return _cluster_coordinator


def init_cluster_coordinator(
    node_id: str,
    broadcast_port: int = 8888,
    api_port: int = 8000
) -> ClusterCoordinator:
    """Initialize global cluster coordinator"""
    global _cluster_coordinator
    _cluster_coordinator = ClusterCoordinator(node_id, broadcast_port, api_port)
    return _cluster_coordinator
