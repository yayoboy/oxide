"""
Integration test for task history.

Tests that tasks executed via MCP are properly stored and can be
retrieved via the Web backend API.
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from oxide.config.loader import load_config
from oxide.core.orchestrator import Orchestrator
from oxide.mcp.tools import OxideTools
from oxide.utils.task_storage import get_task_storage


async def test_task_storage_integration():
    """Test that MCP task execution populates task storage."""
    print("\n=== Task History Integration Test ===\n")

    # Initialize orchestrator and tools
    config = load_config()
    orchestrator = Orchestrator(config)
    tools = OxideTools(orchestrator)

    # Get task storage
    task_storage = get_task_storage()

    # Clear any existing tasks
    task_storage.clear_tasks()
    print("✓ Cleared task storage")

    # Test 1: Execute a simple task via MCP tools
    print("\n--- Test 1: Execute task via MCP ---")
    prompt = "What is 2 + 2?"

    print(f"Prompt: {prompt}")

    try:
        # Execute task (this should save to task_storage)
        response_parts = []
        async for content in tools.route_task(prompt=prompt):
            response_parts.append(content.text)

        response = "".join(response_parts)
        print(f"✓ Task executed successfully")
        print(f"  Response length: {len(response)} chars")

        # Give a moment for async operations to complete
        await asyncio.sleep(0.5)

        # Test 2: Verify task was saved
        print("\n--- Test 2: Verify task in storage ---")
        tasks = task_storage.list_tasks(limit=10)

        print(f"✓ Found {len(tasks)} task(s) in storage")

        if len(tasks) == 0:
            print("✗ FAILED: No tasks found in storage!")
            return False

        # Check the latest task
        latest_task = tasks[0]
        print(f"\nLatest task details:")
        print(f"  ID: {latest_task['id']}")
        print(f"  Status: {latest_task['status']}")
        print(f"  Prompt: {latest_task['prompt'][:50]}...")
        print(f"  Service: {latest_task.get('service', 'unknown')}")
        print(f"  Task Type: {latest_task.get('task_type', 'unknown')}")

        if latest_task.get('duration'):
            print(f"  Duration: {latest_task['duration']:.2f}s")

        # Verify task details
        assert latest_task["prompt"] == prompt, "Prompt mismatch!"
        assert latest_task["status"] in ("completed", "failed"), f"Unexpected status: {latest_task['status']}"

        if latest_task["status"] == "completed":
            assert latest_task.get("result"), "No result stored!"
            print(f"✓ Task completed successfully")
        else:
            print(f"⚠ Task failed: {latest_task.get('error')}")

        # Test 3: Check task statistics
        print("\n--- Test 3: Check statistics ---")
        stats = task_storage.get_stats()

        print(f"Total tasks: {stats['total']}")
        print(f"By status: {stats['by_status']}")
        print(f"By service: {stats['by_service']}")
        print(f"By type: {stats['by_task_type']}")

        print("\n✅ All tests passed!")
        return True

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run the integration test."""
    success = asyncio.run(test_task_storage_integration())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
