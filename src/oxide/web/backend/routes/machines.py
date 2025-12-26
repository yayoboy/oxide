"""
Machine monitoring API routes.

Endpoints for multi-machine metrics and monitoring.
"""
import asyncio
import psutil
from typing import Dict, Any, List
from urllib.parse import urlparse
from fastapi import APIRouter, Depends
import aiohttp

from ....core.orchestrator import Orchestrator
from ....utils.logging import logger


router = APIRouter()


def get_orchestrator() -> Orchestrator:
    """Dependency to get orchestrator instance."""
    from ..main import get_orchestrator
    return get_orchestrator()


@router.get("/")
async def list_machines(orchestrator: Orchestrator = Depends(get_orchestrator)) -> Dict[str, Any]:
    """
    Get list of all machines with their metrics.

    Returns:
        Dictionary with machine information and metrics
    """
    try:
        machines = {}

        # Local machine
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()

        machines['local'] = {
            "id": "local",
            "name": "Local Machine",
            "location": "localhost",
            "status": "online",
            "metrics": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used_mb": round(memory.used / (1024 * 1024), 2),
                "memory_total_mb": round(memory.total / (1024 * 1024), 2),
            },
            "services": [],
        }

        # Extract remote machines from HTTP services
        service_status = await orchestrator.get_service_status()

        for service_name, status in service_status.items():
            info = status.get("info", {})
            service_type = str(info.get("type", "")).lower()

            # Check if it's an HTTP service (handles both "http" and "servicetype.http")
            if "http" in service_type:
                base_url = info.get("base_url", "")
                if base_url:
                    parsed = urlparse(base_url)
                    hostname = parsed.hostname or "unknown"
                    port = parsed.port or 80

                    # Check if it's localhost
                    is_local = hostname in ["localhost", "127.0.0.1", "::1"]

                    if is_local:
                        # Add to local machine services
                        machines['local']['services'].append({
                            "name": service_name,
                            "healthy": status.get("healthy", False),
                            "endpoint": base_url,
                        })
                    else:
                        # Create or update remote machine entry
                        machine_id = f"remote_{hostname.replace('.', '_')}"

                        if machine_id not in machines:
                            machines[machine_id] = {
                                "id": machine_id,
                                "name": f"Remote Server ({hostname})",
                                "location": hostname,
                                "status": "online" if status.get("healthy") else "offline",
                                "metrics": {
                                    "cpu_percent": None,  # Unknown
                                    "memory_percent": None,  # Unknown
                                },
                                "services": [],
                            }

                        machines[machine_id]['services'].append({
                            "name": service_name,
                            "healthy": status.get("healthy", False),
                            "endpoint": base_url,
                        })

                        # Update machine status based on any healthy service
                        if status.get("healthy"):
                            machines[machine_id]['status'] = "online"

        return {
            "machines": list(machines.values()),
            "total": len(machines),
            "online": sum(1 for m in machines.values() if m["status"] == "online"),
        }

    except Exception as e:
        logger.error(f"Error listing machines: {e}")
        return {
            "machines": [],
            "total": 0,
            "online": 0,
            "error": str(e),
        }


@router.get("/{machine_id}")
async def get_machine(
    machine_id: str,
    orchestrator: Orchestrator = Depends(get_orchestrator)
) -> Dict[str, Any]:
    """
    Get detailed information about a specific machine.

    Args:
        machine_id: ID of the machine

    Returns:
        Machine information with metrics
    """
    try:
        if machine_id == "local":
            # Local machine
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            return {
                "id": "local",
                "name": "Local Machine",
                "location": "localhost",
                "status": "online",
                "metrics": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_used_mb": round(memory.used / (1024 * 1024), 2),
                    "memory_total_mb": round(memory.total / (1024 * 1024), 2),
                    "disk_percent": disk.percent,
                    "disk_used_gb": round(disk.used / (1024 * 1024 * 1024), 2),
                    "disk_total_gb": round(disk.total / (1024 * 1024 * 1024), 2),
                },
            }
        else:
            # Remote machine - would need to implement remote metrics collection
            return {
                "id": machine_id,
                "error": "Remote machine metrics not yet implemented",
            }

    except Exception as e:
        logger.error(f"Error getting machine {machine_id}: {e}")
        return {
            "error": str(e),
        }
