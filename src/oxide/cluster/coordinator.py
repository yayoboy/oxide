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

logger = get_logger(__name__)


@dataclass
class NodeInfo:
    """Information about a cluster node"""
    node_id: str
    hostname: str
    ip_address: str
    port: int
    services: List[str]  # Available LLM services
    cpu_percent: float
    memory_percent: float
    active_tasks: int
    total_tasks: int
    last_seen: float
    healthy: bool = True


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

        self.logger.info(f"Cluster coordinator initialized: {node_id}")

    async def start(self, orchestrator):
        """
        Start cluster coordination.

        Args:
            orchestrator: Local Orchestrator instance
        """
        # Create local node info
        self.local_node = await self._create_local_node_info(orchestrator)

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
        """Create NodeInfo for local instance"""
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

        # Get available services
        services = list(orchestrator.adapters.keys()) if orchestrator else []

        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory_percent = psutil.virtual_memory().percent

        # Get task counts
        task_storage = get_task_storage()
        tasks = task_storage.get_all_tasks()
        active_tasks = len([t for t in tasks if t.get("status") == "running"])

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
            healthy=True
        )

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

                        # Update or add node
                        node = NodeInfo(**node_data)
                        self.nodes[node_id] = node

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
        """Monitor health of discovered nodes"""
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
            if not node.healthy:
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
