"""
Test broadcast_all execution mode.

Verifies that the multi-LLM broadcast orchestration works correctly.
"""
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest


def test_router_decision_broadcast_all():
    """Test RouterDecision supports broadcast_all mode."""
    print("\n🧪 Test 1: RouterDecision with broadcast_all")

    from oxide.core.router import RouterDecision

    decision = RouterDecision(
        primary_service="gemini",
        fallback_services=[],
        execution_mode="broadcast_all",
        timeout_seconds=30,
        broadcast_services=["gemini", "qwen", "openrouter"]
    )

    assert decision.execution_mode == "broadcast_all"
    assert decision.broadcast_services == ["gemini", "qwen", "openrouter"]
    assert len(decision.broadcast_services) == 3

    print("   ✅ RouterDecision supports broadcast_all mode")
    print(f"   ✅ Broadcast services: {decision.broadcast_services}")


@pytest.mark.asyncio
async def test_router_broadcast_all_method():
    """Test TaskRouter.route_broadcast_all() method."""
    print("\n🧪 Test 2: TaskRouter.route_broadcast_all()")

    from oxide.core.router import TaskRouter
    from oxide.core.classifier import TaskInfo, TaskType
    from oxide.config.loader import Config, ServiceConfig, RoutingRuleConfig

    # Create mock config with multiple services
    config = Config(
        services={
            "gemini": ServiceConfig(enabled=True, type="cli", model="gemini"),
            "qwen": ServiceConfig(enabled=True, type="cli", model="qwen"),
            "ollama": ServiceConfig(enabled=True, type="http", base_url="http://localhost:11434"),
        },
        routing_rules={
            "code_generation": RoutingRuleConfig(
                primary="gemini",
                fallback=["qwen"],
                parallel_threshold_files=5,
                timeout_seconds=30
            )
        }
    )

    # Mock health checker that returns all services as healthy
    async def mock_health_checker(service_name):
        return True

    router = TaskRouter(config, service_health_checker=mock_health_checker)

    # Create task info
    task_info = TaskInfo(
        task_type=TaskType.CODE_GENERATION,
        recommended_services=["gemini", "qwen"],
        use_parallel=False,
        complexity_score=0.5,
        file_count=0,
        total_size_bytes=0
    )

    # Get broadcast routing decision
    decision = await router.route_broadcast_all(task_info)

    assert decision.execution_mode == "broadcast_all"
    assert decision.broadcast_services is not None
    assert len(decision.broadcast_services) == 3  # All 3 services
    assert "gemini" in decision.broadcast_services
    assert "qwen" in decision.broadcast_services
    assert "ollama" in decision.broadcast_services

    print("   ✅ route_broadcast_all() returns correct decision")
    print(f"   ✅ Broadcast to {len(decision.broadcast_services)} services")
    print(f"   ✅ Services: {', '.join(decision.broadcast_services)}")


def test_task_storage_broadcast_results():
    """Test TaskStorage supports broadcast_results field."""
    print("\n🧪 Test 3: TaskStorage broadcast_results")

    import tempfile
    from pathlib import Path
    from oxide.utils.task_storage import TaskStorage

    # Create temporary storage
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = TaskStorage(Path(tmpdir) / "test_tasks.json")

        # Add task with broadcast execution mode
        task = storage.add_task(
            task_id="test_broadcast_1",
            prompt="Test broadcast prompt",
            files=None,
            preferences={"broadcast_all": True},
            service="broadcast_all",
            task_type="code_generation",
            execution_mode="broadcast_all"
        )

        assert task["execution_mode"] == "broadcast_all"
        assert "broadcast_results" in task
        assert isinstance(task["broadcast_results"], list)
        assert len(task["broadcast_results"]) == 0  # Empty initially

        print("   ✅ Task created with broadcast_all mode")

        # Add results from multiple services
        storage.add_broadcast_result(
            task_id="test_broadcast_1",
            service="gemini",
            result="Gemini response here",
            error=None,
            chunks=15
        )

        storage.add_broadcast_result(
            task_id="test_broadcast_1",
            service="qwen",
            result="Qwen response here",
            error=None,
            chunks=23
        )

        storage.add_broadcast_result(
            task_id="test_broadcast_1",
            service="ollama",
            result=None,
            error="Connection timeout",
            chunks=0
        )

        # Retrieve and verify
        task = storage.get_task("test_broadcast_1")

        assert len(task["broadcast_results"]) == 3

        # Check gemini result
        gemini_result = next(r for r in task["broadcast_results"] if r["service"] == "gemini")
        assert gemini_result["result"] == "Gemini response here"
        assert gemini_result["chunks"] == 15
        assert gemini_result["error"] is None

        # Check qwen result
        qwen_result = next(r for r in task["broadcast_results"] if r["service"] == "qwen")
        assert qwen_result["result"] == "Qwen response here"
        assert qwen_result["chunks"] == 23

        # Check ollama error
        ollama_result = next(r for r in task["broadcast_results"] if r["service"] == "ollama")
        assert ollama_result["result"] is None
        assert ollama_result["error"] == "Connection timeout"

        print("   ✅ Broadcast results stored correctly")
        print(f"   ✅ Gemini: {gemini_result['chunks']} chunks")
        print(f"   ✅ Qwen: {qwen_result['chunks']} chunks")
        print(f"   ✅ Ollama: Error captured")


@pytest.mark.asyncio
async def test_websocket_broadcast_chunk_method():
    """Test WebSocketManager.broadcast_task_broadcast_chunk() method."""
    print("\n🧪 Test 4: WebSocket broadcast_task_broadcast_chunk()")

    from oxide.web.backend.websocket import WebSocketManager
    from unittest.mock import AsyncMock

    ws_manager = WebSocketManager(max_connections=10)

    # Mock WebSocket connections
    mock_ws1 = AsyncMock()
    mock_ws2 = AsyncMock()

    # Add mock connections
    ws_manager.active_connections.add(mock_ws1)
    ws_manager.active_connections.add(mock_ws2)

    # Broadcast chunk
    await ws_manager.broadcast_task_broadcast_chunk(
        task_id="test_task_1",
        service="gemini",
        chunk="Hello from Gemini",
        done=False,
        timestamp=1234567890.123,
        error=None,
        total_chunks=None
    )

    # Verify both connections received the message
    assert mock_ws1.send_json.called
    assert mock_ws2.send_json.called

    # Check message format
    sent_message = mock_ws1.send_json.call_args[0][0]

    assert sent_message["type"] == "task_broadcast_chunk"
    assert sent_message["task_id"] == "test_task_1"
    assert sent_message["service"] == "gemini"
    assert sent_message["chunk"] == "Hello from Gemini"
    assert sent_message["done"] is False
    assert sent_message["timestamp"] == 1234567890.123

    print("   ✅ broadcast_task_broadcast_chunk() sends correct message")
    print(f"   ✅ Message type: {sent_message['type']}")
    print(f"   ✅ Sent to {len(ws_manager.active_connections)} connections")


@pytest.mark.asyncio
async def test_orchestrator_execute_broadcast_all_integration():
    """Test Orchestrator._execute_broadcast_all() method integration."""
    print("\n🧪 Test 5: Orchestrator broadcast_all integration")

    from oxide.core.orchestrator import Orchestrator
    from oxide.config.loader import Config, ServiceConfig

    # Create minimal config
    config = Config(
        services={
            "mock_service_1": ServiceConfig(enabled=True, type="cli", model="test"),
            "mock_service_2": ServiceConfig(enabled=True, type="cli", model="test"),
        },
        routing_rules={}
    )

    orchestrator = Orchestrator(config)

    # Mock adapters that yield test chunks
    async def mock_execute_1(prompt, files=None, timeout=30):
        yield "Response from service 1 - chunk 1"
        await asyncio.sleep(0.01)
        yield "Response from service 1 - chunk 2"

    async def mock_execute_2(prompt, files=None, timeout=30):
        yield "Response from service 2 - chunk 1"
        await asyncio.sleep(0.01)
        yield "Response from service 2 - chunk 2"

    mock_adapter_1 = AsyncMock()
    mock_adapter_1.execute = mock_execute_1

    mock_adapter_2 = AsyncMock()
    mock_adapter_2.execute = mock_execute_2

    orchestrator.adapters = {
        "mock_service_1": mock_adapter_1,
        "mock_service_2": mock_adapter_2,
    }

    # Execute broadcast
    services = ["mock_service_1", "mock_service_2"]
    chunks_received = []

    async for chunk_json in orchestrator._execute_broadcast_all(
        services=services,
        prompt="Test prompt",
        files=None,
        timeout_seconds=30,
        task_id="test_broadcast_task"
    ):
        chunks_received.append(chunk_json)
        chunk_obj = json.loads(chunk_json)
        print(f"   📦 Chunk from {chunk_obj['service']}: {chunk_obj['chunk'][:30]}...")

    # Verify we got chunks from both services
    service_1_chunks = [c for c in chunks_received if '"service": "mock_service_1"' in c]
    service_2_chunks = [c for c in chunks_received if '"service": "mock_service_2"' in c]

    assert len(service_1_chunks) > 0, "Should have chunks from service 1"
    assert len(service_2_chunks) > 0, "Should have chunks from service 2"

    # Verify done markers
    done_chunks = [c for c in chunks_received if '"done": true' in c]
    assert len(done_chunks) == 2, "Should have 2 done markers (one per service)"

    print("   ✅ Broadcast execution completed")
    print(f"   ✅ Total chunks received: {len(chunks_received)}")
    print(f"   ✅ Service 1 chunks: {len(service_1_chunks)}")
    print(f"   ✅ Service 2 chunks: {len(service_2_chunks)}")
    print(f"   ✅ Completion markers: {len(done_chunks)}")


def run_all_tests():
    """Run all broadcast mode tests."""
    print("=" * 60)
    print("🧪 Broadcast Mode Tests")
    print("=" * 60)

    try:
        # Sync tests
        test_router_decision_broadcast_all()
        test_task_storage_broadcast_results()

        # Async tests
        asyncio.run(test_router_broadcast_all_method())
        asyncio.run(test_websocket_broadcast_chunk_method())
        asyncio.run(test_orchestrator_execute_broadcast_all_integration())

        print("\n" + "=" * 60)
        print("✅ All broadcast mode tests passed!")
        print("=" * 60)

        print("\n📋 Summary:")
        print("   ✅ RouterDecision supports broadcast_all mode")
        print("   ✅ TaskRouter.route_broadcast_all() works correctly")
        print("   ✅ TaskStorage handles broadcast_results")
        print("   ✅ WebSocket broadcasts chunks with service ID")
        print("   ✅ Orchestrator executes on multiple services in parallel")
        print("\n   The broadcast mode implementation is working correctly!")

        return 0

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(run_all_tests())
