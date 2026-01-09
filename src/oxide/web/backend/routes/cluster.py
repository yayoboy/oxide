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


@router.get("/health")
async def cluster_health():
    """
    Health check endpoint for cluster nodes.

    This endpoint is used by other Oxide nodes to verify connectivity.
    Returns basic node information and health status.
    """
    coordinator = get_cluster_coordinator()

    if not coordinator or not coordinator.local_node:
        return {
            "status": "unhealthy",
            "message": "Cluster coordinator not initialized"
        }

    return {
        "status": "healthy",
        "node_id": coordinator.node_id,
        "hostname": coordinator.local_node.hostname,
        "services": list(coordinator.local_node.services.keys()),
        "cpu_percent": coordinator.local_node.cpu_percent,
        "memory_percent": coordinator.local_node.memory_percent,
        "active_tasks": coordinator.local_node.active_tasks,
        "oxide_version": coordinator.local_node.oxide_version
    }


@router.post("/nodes/{node_id}/enable")
async def enable_node(node_id: str):
    """
    Enable a discovered node.

    Args:
        node_id: Node identifier

    Returns:
        Success message or error
    """
    coordinator = get_cluster_coordinator()

    if not coordinator:
        raise HTTPException(
            status_code=503,
            detail="Cluster coordination not enabled"
        )

    success = coordinator.enable_node(node_id)

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Node '{node_id}' not found"
        )

    return {
        "status": "success",
        "node_id": node_id,
        "enabled": True,
        "message": f"Node '{node_id}' enabled successfully"
    }


@router.post("/nodes/{node_id}/disable")
async def disable_node(node_id: str):
    """
    Disable a discovered node.

    Args:
        node_id: Node identifier

    Returns:
        Success message or error
    """
    coordinator = get_cluster_coordinator()

    if not coordinator:
        raise HTTPException(
            status_code=503,
            detail="Cluster coordination not enabled"
        )

    success = coordinator.disable_node(node_id)

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Node '{node_id}' not found"
        )

    return {
        "status": "success",
        "node_id": node_id,
        "enabled": False,
        "message": f"Node '{node_id}' disabled successfully"
    }


@router.get("/services-matrix")
async def get_services_matrix():
    """
    Get service availability matrix across all nodes.

    Returns a matrix showing which services are available on which nodes,
    useful for understanding cluster capabilities and load distribution.
    """
    coordinator = get_cluster_coordinator()

    if not coordinator:
        raise HTTPException(
            status_code=503,
            detail="Cluster coordination not enabled"
        )

    # Collect all nodes
    all_nodes = coordinator.get_all_nodes()

    # Build services matrix
    matrix = {}
    for node in all_nodes:
        is_local = node.node_id == coordinator.node_id
        node_info = {
            "hostname": node.hostname,
            "ip_address": node.ip_address,
            "port": node.port,
            "healthy": node.healthy,
            "enabled": node.enabled,
            "local": is_local,
            "cpu_percent": node.cpu_percent,
            "memory_percent": node.memory_percent,
            "active_tasks": node.active_tasks
        }

        # Add services with details
        for service_name, service_details in node.services.items():
            if service_name not in matrix:
                matrix[service_name] = {
                    "nodes": [],
                    "total_nodes": 0,
                    "healthy_nodes": 0,
                    "enabled_nodes": 0
                }

            matrix[service_name]["nodes"].append({
                **node_info,
                "service_details": service_details
            })
            matrix[service_name]["total_nodes"] += 1
            if node.healthy:
                matrix[service_name]["healthy_nodes"] += 1
            if node.enabled:
                matrix[service_name]["enabled_nodes"] += 1

    return {
        "services": matrix,
        "total_nodes": len(all_nodes),
        "total_services": len(matrix)
    }


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

    url = f"http://{node.ip_address}:{node.port}/api/cluster/health"

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
