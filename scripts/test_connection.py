#!/usr/bin/env python3
"""
Test connectivity to all configured LLM services.

Usage:
    python scripts/test_connection.py              # Test all services
    python scripts/test_connection.py --service gemini  # Test specific service
    python scripts/test_connection.py --all        # Detailed test with sample prompts
"""
import asyncio
import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from oxide.core.orchestrator import Orchestrator
from oxide.utils.logging import logger


async def test_service(orchestrator: Orchestrator, service_name: str, detailed: bool = False):
    """Test a specific service."""
    print(f"\n{'='*60}")
    print(f"Testing: {service_name}")
    print(f"{'='*60}")

    # Check if service exists
    if service_name not in orchestrator.adapters:
        print(f"❌ Service '{service_name}' not found or not initialized")
        return False

    adapter = orchestrator.adapters[service_name]

    # 1. Health check
    print(f"\n1️⃣  Health Check...")
    try:
        is_healthy = await adapter.health_check()
        if is_healthy:
            print(f"   ✅ Service is healthy")
        else:
            print(f"   ❌ Service failed health check")
            return False
    except Exception as e:
        print(f"   ❌ Health check error: {e}")
        return False

    # 2. Get service info
    print(f"\n2️⃣  Service Info...")
    try:
        info = adapter.get_service_info()
        for key, value in info.items():
            print(f"   {key}: {value}")
    except Exception as e:
        print(f"   ⚠️  Could not get service info: {e}")

    # 3. Detailed test with sample prompt
    if detailed:
        print(f"\n3️⃣  Sample Execution Test...")
        test_prompt = "Say hello in one sentence"

        try:
            print(f"   Prompt: '{test_prompt}'")
            print(f"   Response: ", end="", flush=True)

            chunks = []
            async for chunk in adapter.execute(test_prompt, timeout=30):
                print(chunk, end="", flush=True)
                chunks.append(chunk)

            response = "".join(chunks)
            print(f"\n   ✅ Execution successful ({len(response)} chars)")

        except Exception as e:
            print(f"\n   ❌ Execution failed: {e}")
            return False

    print(f"\n{'='*60}")
    print(f"✅ {service_name}: PASSED")
    print(f"{'='*60}\n")

    return True


async def test_all_services(orchestrator: Orchestrator, detailed: bool = False):
    """Test all configured services."""
    print("\n" + "="*60)
    print("Testing All Configured Services")
    print("="*60)

    results = {}

    for service_name in orchestrator.adapters.keys():
        success = await test_service(orchestrator, service_name, detailed)
        results[service_name] = success

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    passed = sum(1 for success in results.values() if success)
    total = len(results)

    for service_name, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{service_name:20s} {status}")

    print(f"\nTotal: {passed}/{total} services passed")

    if passed == total:
        print("\n🎉 All services are working!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} service(s) failed")
        return 1


async def main():
    parser = argparse.ArgumentParser(description="Test Oxide LLM service connections")
    parser.add_argument(
        "--service",
        type=str,
        help="Test specific service (e.g., gemini, qwen, ollama_local)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run detailed tests with sample prompts"
    )

    args = parser.parse_args()

    print("🔬 Oxide Connection Tester")
    print("="*60)

    # Initialize orchestrator
    try:
        print("Initializing Oxide...")
        orchestrator = Orchestrator()
        print(f"✅ Loaded {len(orchestrator.adapters)} service(s)\n")

    except Exception as e:
        print(f"❌ Failed to initialize Oxide: {e}")
        return 1

    # Test services
    if args.service:
        success = await test_service(orchestrator, args.service, detailed=True)
        return 0 if success else 1
    else:
        return await test_all_services(orchestrator, detailed=args.all)


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        sys.exit(1)
