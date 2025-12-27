#!/usr/bin/env python3
"""Test LM Studio provider integration."""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from oxide.core.orchestrator import Orchestrator
from oxide.config.loader import load_config
from oxide.utils.task_storage import get_task_storage


async def test_lmstudio():
    """Test LM Studio connectivity and task execution."""
    print("=" * 80)
    print("LM Studio Provider Integration Test")
    print("=" * 80)

    # Load config
    config_path = Path(__file__).parent / "config" / "default.yaml"
    cfg = load_config(config_path)

    # Initialize orchestrator
    print("\n[1/4] Initializing orchestrator...")
    orchestrator = Orchestrator(cfg)

    # Check LM Studio health
    print("\n[2/4] Checking LM Studio health...")
    if "lmstudio" in orchestrator.adapters:
        adapter = orchestrator.adapters["lmstudio"]
        try:
            # Get service info
            info = adapter.get_service_info()
            print(f"  ✓ Service Type: {info['type']}")
            print(f"  ✓ Base URL: {info['base_url']}")
            print(f"  ✓ API Type: {info.get('api_type', 'N/A')}")

            # Check health
            is_healthy = await orchestrator._check_service_health("lmstudio")
            print(f"  ✓ Health Status: {'Healthy' if is_healthy else 'Unhealthy'}")

            if not is_healthy:
                print("\n❌ LM Studio is not healthy. Cannot proceed with test.")
                return False

        except Exception as e:
            print(f"  ❌ Error checking health: {e}")
            return False
    else:
        print("  ❌ LM Studio adapter not found in orchestrator")
        return False

    # Execute test task
    print("\n[3/4] Executing test task through LM Studio...")
    task_id = "test_lmstudio_001"
    prompt = "What is the capital of Italy? Provide only the city name, no explanation."

    try:
        result_chunks = []
        async for chunk in orchestrator.execute_task(
            prompt=prompt,
            preferences={
                "task_id": task_id,
                "preferred_service": "lmstudio"
            }
        ):
            result_chunks.append(chunk)
            print(".", end="", flush=True)

        response = "".join(result_chunks)
        print()  # Newline after dots
        print(f"\n  ✓ Response: {response[:200]}")

    except Exception as e:
        print(f"\n  ❌ Error executing task: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Verify task tracking
    print("\n[4/4] Verifying task tracking...")
    try:
        storage = get_task_storage()
        task = storage.get_task(task_id)

        if task:
            print(f"  ✓ Task ID: {task.get('id', task_id)}")
            print(f"  ✓ Status: {task.get('status', 'unknown')}")
            print(f"  ✓ Service: {task.get('service', 'N/A')}")
            print(f"  ✓ Task Type: {task.get('task_type', 'N/A')}")
            print(f"  ✓ Prompt: {task.get('prompt', '')[:50]}...")
            print(f"  ✓ Duration: {task.get('duration', 'N/A')} seconds")
        else:
            print(f"  ❌ Task {task_id} not found in storage")
            return False

    except Exception as e:
        print(f"  ❌ Error checking task storage: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 80)
    print("✅ LM Studio Integration Test PASSED")
    print("=" * 80)
    return True


if __name__ == "__main__":
    success = asyncio.run(test_lmstudio())
    sys.exit(0 if success else 1)
