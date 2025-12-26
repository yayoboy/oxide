"""
Cluster Management API Endpoints

Provides REST API for cluster operations:
- Get cluster status
- List nodes
- Execute distributed tasks
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from ....cluster import get_cluster_coordinator
from ....utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/cluster", tags=["cluster"])


# Request/Response models
class TaskExecuteRequest(BaseModel):
    """Request to execute a distributed task"""
    prompt: str
    files: Optional[List[str]] = None
    preferences: Optional[Dict[str, Any]] = None
    node_id: Optional[str] = None  # Specific node, or auto-select


class ClusterStatus(BaseModel):
    """Cluster status response"""
    enabled: bool
    local_node: Optional[Dict[str, Any]]
    cluster_nodes: List[Dict[str, Any]]
    total_nodes: int
    healthy_nodes: int


# API Endpoints

@router.get("/status", response_model=ClusterStatus)
async def get_status():
    """
    Get cluster status.

    Returns information about all nodes in the cluster.
    """
    coordinator = get_cluster_coordinator()

    if not coordinator:
        return ClusterStatus(
            enabled=False,
            local_node=None,
            cluster_nodes=[],
            total_nodes=0,
            healthy_nodes=0
        )

    status = coordinator.get_cluster_status()

    return ClusterStatus(
        enabled=True,
        local_node=status["local_node"],
        cluster_nodes=status["cluster_nodes"],
        total_nodes=status["total_nodes"],
        healthy_nodes=status["healthy_nodes"]
    )


@router.get("/nodes")
async def list_nodes():
    """
    List all nodes in the cluster.

    Returns detailed information about each node.
    """
    coordinator = get_cluster_coordinator()

    if not coordinator:
        return {
            "local_node": None,
            "remote_nodes": [],
            "message": "Cluster coordination not enabled"
        }

    status = coordinator.get_cluster_status()

    return {
        "local_node": status["local_node"],
        "remote_nodes": status["cluster_nodes"],
        "total_nodes": status["total_nodes"],
        "healthy_nodes": status["healthy_nodes"]
    }


@router.post("/tasks/execute")
async def execute_distributed_task(request: TaskExecuteRequest):
    """
    Execute task with cluster-aware routing.

    If node_id is specified, task is routed to that node.
    Otherwise, automatically selects the best available node.
    """
    coordinator = get_cluster_coordinator()

    if not coordinator:
        raise HTTPException(
            status_code=503,
            detail="Cluster coordination not enabled"
        )

    try:
        # Select target node
        if request.node_id:
            # Specific node requested
            if request.node_id == coordinator.node_id:
                target_node = coordinator.local_node
            else:
                target_node = coordinator.nodes.get(request.node_id)

            if not target_node:
                raise HTTPException(
                    status_code=404,
                    detail=f"Node '{request.node_id}' not found"
                )

            if not target_node.healthy:
                raise HTTPException(
                    status_code=503,
                    detail=f"Node '{request.node_id}' is unhealthy"
                )
        else:
            # Auto-select best node
            required_service = request.preferences.get("preferred_service") if request.preferences else None
            target_node = coordinator.get_best_node_for_task(
                task_type="general",
                required_service=required_service
            )

            if not target_node:
                raise HTTPException(
                    status_code=503,
                    detail="No healthy nodes available"
                )

        # Execute on target node
        if target_node == coordinator.local_node:
            # Execute locally (return task ID for streaming)
            return {
                "status": "executing",
                "node": {
                    "id": target_node.node_id,
                    "hostname": target_node.hostname,
                    "local": True
                },
                "message": "Task executing on local node (use /api/tasks endpoints for streaming)"
            }
        else:
            # Execute remotely
            logger.info(f"Routing task to remote node: {target_node.hostname}")

            result = await coordinator.execute_task_on_node(
                node=target_node,
                prompt=request.prompt,
                files=request.files,
                preferences=request.preferences
            )

            return {
                "status": "completed" if "error" not in result else "failed",
                "node": {
                    "id": target_node.node_id,
                    "hostname": target_node.hostname,
                    "local": False
                },
                "result": result
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute distributed task: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Task execution failed: {str(e)}"
        )


@router.get("/nodes/{node_id}")
async def get_node_info(node_id: str):
    """
    Get detailed information about a specific node.

    Args:
        node_id: Node identifier
    """
    coordinator = get_cluster_coordinator()

    if not coordinator:
        raise HTTPException(
            status_code=503,
            detail="Cluster coordination not enabled"
        )

    # Check local node
    if node_id == coordinator.node_id and coordinator.local_node:
        return coordinator.local_node

    # Check remote nodes
    node = coordinator.nodes.get(node_id)
    if not node:
        raise HTTPException(
            status_code=404,
            detail=f"Node '{node_id}' not found"
        )

    return node


@router.post("/nodes/{node_id}/ping")
async def ping_node(node_id: str):
    """
    Ping a specific node to check connectivity.

    Args:
        node_id: Node identifier
    """
    coordinator = get_cluster_coordinator()

    if not coordinator:
        raise HTTPException(
            status_code=503,
            detail="Cluster coordination not enabled"
        )

    # Find node
    if node_id == coordinator.node_id:
        return {
            "node_id": node_id,
            "reachable": True,
            "local": True,
            "latency_ms": 0
        }

    node = coordinator.nodes.get(node_id)
    if not node:
        raise HTTPException(
            status_code=404,
            detail=f"Node '{node_id}' not found"
        )

    # Try to ping
    import aiohttp
    import time

    url = f"http://{node.ip_address}:{node.port}/health"

    try:
        start = time.time()
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                latency_ms = (time.time() - start) * 1000
                reachable = response.status == 200

                return {
                    "node_id": node_id,
                    "reachable": reachable,
                    "local": False,
                    "latency_ms": round(latency_ms, 2)
                }
    except Exception as e:
        logger.warning(f"Failed to ping node {node_id}: {e}")
        return {
            "node_id": node_id,
            "reachable": False,
            "local": False,
            "error": str(e)
        }
