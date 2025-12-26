"""
Cluster Management Module

Enables multi-machine cooperation and task distribution.
"""
from .coordinator import (
    ClusterCoordinator,
    NodeInfo,
    get_cluster_coordinator,
    init_cluster_coordinator
)

__all__ = [
    "ClusterCoordinator",
    "NodeInfo",
    "get_cluster_coordinator",
    "init_cluster_coordinator"
]
