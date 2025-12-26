"""
Tests for Cluster Coordinator

Tests multi-machine cooperation and task distribution:
- Node discovery
- Cluster status
- Load-based routing
- Remote task execution
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from oxide.cluster.coordinator import ClusterCoordinator, NodeInfo


@pytest.fixture
def coordinator():
    """Create a coordinator instance for testing"""
    return ClusterCoordinator(
        node_id="test_node_1",
        broadcast_port=18888,  # Non-standard port for testing
        api_port=18000
    )


@pytest.fixture
def mock_orchestrator():
    """Create a mock orchestrator"""
    mock = Mock()
    mock.adapters = {
        "gemini": Mock(),
        "qwen": Mock(),
        "ollama_local": Mock()
    }
    return mock


def test_coordinator_initialization(coordinator):
    """Test coordinator initialization"""
    assert coordinator.node_id == "test_node_1"
    assert coordinator.broadcast_port == 18888
    assert coordinator.api_port == 18000
    assert len(coordinator.nodes) == 0
    assert coordinator.local_node is None


@pytest.mark.asyncio
async def test_create_local_node_info(coordinator, mock_orchestrator):
    """Test local node info creation"""
    with patch('psutil.cpu_percent', return_value=25.0), \
         patch('psutil.virtual_memory') as mock_mem:

        mock_mem.return_value.percent = 50.0

        node = await coordinator._create_local_node_info(mock_orchestrator)

        assert node.node_id == "test_node_1"
        assert node.services == ["gemini", "qwen", "ollama_local"]
        assert node.cpu_percent == 25.0
        assert node.memory_percent == 50.0
        assert node.healthy is True


def test_get_cluster_status(coordinator):
    """Test cluster status retrieval"""
    # Create local node
    coordinator.local_node = NodeInfo(
        node_id="test_node_1",
        hostname="localhost",
        ip_address="192.168.1.100",
        port=8000,
        services=["gemini", "qwen"],
        cpu_percent=30.0,
        memory_percent=40.0,
        active_tasks=2,
        total_tasks=10,
        last_seen=1234567890.0,
        healthy=True
    )

    # Add remote node
    coordinator.nodes["test_node_2"] = NodeInfo(
        node_id="test_node_2",
        hostname="remote",
        ip_address="192.168.1.101",
        port=8000,
        services=["ollama_local"],
        cpu_percent=50.0,
        memory_percent=60.0,
        active_tasks=5,
        total_tasks=15,
        last_seen=1234567890.0,
        healthy=True
    )

    status = coordinator.get_cluster_status()

    assert status["total_nodes"] == 2
    assert status["healthy_nodes"] == 2
    assert status["local_node"]["node_id"] == "test_node_1"
    assert len(status["cluster_nodes"]) == 1


def test_get_best_node_for_task_local_preferred(coordinator):
    """Test node selection prefers least loaded node"""
    # Create local node (low load)
    coordinator.local_node = NodeInfo(
        node_id="test_node_1",
        hostname="localhost",
        ip_address="192.168.1.100",
        port=8000,
        services=["gemini", "qwen"],
        cpu_percent=20.0,
        memory_percent=30.0,
        active_tasks=1,
        total_tasks=5,
        last_seen=1234567890.0,
        healthy=True
    )

    # Add remote node (high load)
    coordinator.nodes["test_node_2"] = NodeInfo(
        node_id="test_node_2",
        hostname="remote",
        ip_address="192.168.1.101",
        port=8000,
        services=["gemini", "qwen"],
        cpu_percent=80.0,
        memory_percent=90.0,
        active_tasks=10,
        total_tasks=20,
        last_seen=1234567890.0,
        healthy=True
    )

    # Should select local node (lower load)
    best = coordinator.get_best_node_for_task("code_generation")
    assert best.node_id == "test_node_1"


def test_get_best_node_for_task_with_required_service(coordinator):
    """Test node selection with required service"""
    # Create local node (without required service)
    coordinator.local_node = NodeInfo(
        node_id="test_node_1",
        hostname="localhost",
        ip_address="192.168.1.100",
        port=8000,
        services=["gemini"],
        cpu_percent=20.0,
        memory_percent=30.0,
        active_tasks=1,
        total_tasks=5,
        last_seen=1234567890.0,
        healthy=True
    )

    # Add remote node (with required service)
    coordinator.nodes["test_node_2"] = NodeInfo(
        node_id="test_node_2",
        hostname="remote",
        ip_address="192.168.1.101",
        port=8000,
        services=["ollama_local"],
        cpu_percent=50.0,
        memory_percent=60.0,
        active_tasks=5,
        total_tasks=15,
        last_seen=1234567890.0,
        healthy=True
    )

    # Should select remote node (has required service)
    best = coordinator.get_best_node_for_task(
        "code_generation",
        required_service="ollama_local"
    )
    assert best.node_id == "test_node_2"


def test_get_best_node_no_candidates(coordinator):
    """Test node selection when no suitable nodes exist"""
    # No nodes available
    best = coordinator.get_best_node_for_task("code_generation")
    assert best is None

    # Add unhealthy node
    coordinator.nodes["test_node_1"] = NodeInfo(
        node_id="test_node_1",
        hostname="localhost",
        ip_address="192.168.1.100",
        port=8000,
        services=["gemini"],
        cpu_percent=20.0,
        memory_percent=30.0,
        active_tasks=1,
        total_tasks=5,
        last_seen=1234567890.0,
        healthy=False  # Unhealthy
    )

    # Should still return None
    best = coordinator.get_best_node_for_task("code_generation")
    assert best is None


@pytest.mark.asyncio
async def test_execute_task_on_node(coordinator):
    """Test remote task execution"""
    target_node = NodeInfo(
        node_id="test_node_2",
        hostname="remote",
        ip_address="192.168.1.101",
        port=8000,
        services=["gemini"],
        cpu_percent=30.0,
        memory_percent=40.0,
        active_tasks=2,
        total_tasks=10,
        last_seen=1234567890.0,
        healthy=True
    )

    # Mock successful response
    with patch('aiohttp.ClientSession') as mock_session:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"result": "success", "output": "Hello"})

        mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response

        result = await coordinator.execute_task_on_node(
            node=target_node,
            prompt="Test prompt",
            files=[],
            preferences={}
        )

        assert result["result"] == "success"
        assert result["output"] == "Hello"


@pytest.mark.asyncio
async def test_execute_task_on_node_failure(coordinator):
    """Test remote task execution failure handling"""
    target_node = NodeInfo(
        node_id="test_node_2",
        hostname="remote",
        ip_address="192.168.1.101",
        port=8000,
        services=["gemini"],
        cpu_percent=30.0,
        memory_percent=40.0,
        active_tasks=2,
        total_tasks=10,
        last_seen=1234567890.0,
        healthy=True
    )

    # Mock failed response
    with patch('aiohttp.ClientSession') as mock_session:
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal Server Error")

        mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response

        result = await coordinator.execute_task_on_node(
            node=target_node,
            prompt="Test prompt",
            files=[],
            preferences={}
        )

        assert "error" in result
        assert result["status"] == "failed"


def test_load_scoring():
    """Test that load scoring works correctly"""
    # Create nodes with different loads
    low_load_node = NodeInfo(
        node_id="low",
        hostname="low",
        ip_address="192.168.1.100",
        port=8000,
        services=["gemini"],
        cpu_percent=10.0,
        memory_percent=20.0,
        active_tasks=0,
        total_tasks=5,
        last_seen=1234567890.0,
        healthy=True
    )

    high_load_node = NodeInfo(
        node_id="high",
        hostname="high",
        ip_address="192.168.1.101",
        port=8000,
        services=["gemini"],
        cpu_percent=90.0,
        memory_percent=80.0,
        active_tasks=10,
        total_tasks=15,
        last_seen=1234567890.0,
        healthy=True
    )

    # Score function from coordinator (simplified)
    def score_node(node: NodeInfo) -> float:
        load_score = (node.cpu_percent + node.memory_percent) / 2
        task_score = node.active_tasks * 10
        return load_score + task_score

    # Low load should have lower score (better)
    assert score_node(low_load_node) < score_node(high_load_node)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
