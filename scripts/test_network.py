#!/usr/bin/env python3
"""
Network Services Test Script

Test connectivity and functionality of network-based LLM services
(Ollama Remote, LM Studio) for Oxide.

Usage:
    python scripts/test_network.py --service ollama_remote
    python scripts/test_network.py --service lmstudio
    python scripts/test_network.py --all
    python scripts/test_network.py --scan 192.168.1.0/24
"""
import asyncio
import argparse
import socket
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from oxide.adapters.ollama_http import OllamaHTTPAdapter
from oxide.config.loader import load_config
from oxide.utils.logging import logger


class NetworkTester:
    """Test network services for Oxide."""

    def __init__(self):
        self.config = load_config()

    async def test_ollama_remote(self, detailed=False):
        """Test Ollama remote service."""
        print("\n" + "="*60)
        print("Testing Ollama Remote")
        print("="*60)

        service_config = self.config.services.get("ollama_remote")
        if not service_config:
            print("❌ ollama_remote not found in configuration")
            return False

        if not service_config.enabled:
            print("⚠️  ollama_remote is disabled in configuration")
            print("   Enable it in config/default.yaml or run:")
            print("   ./scripts/setup_ollama_remote.sh --ip YOUR_IP")
            return False

        print(f"\nBase URL: {service_config.base_url}")
        print(f"Model: {service_config.default_model}")
        print(f"API Type: {service_config.api_type}")

        # Create adapter
        adapter = OllamaHTTPAdapter("ollama_remote", service_config.model_dump())

        # Health check
        print("\n1️⃣  Health Check...")
        try:
            is_healthy = await adapter.health_check()
            if is_healthy:
                print("   ✅ Service is healthy")
            else:
                print("   ❌ Service failed health check")
                return False
        except Exception as e:
            print(f"   ❌ Health check error: {e}")
            return False

        # Get models
        print("\n2️⃣  Available Models...")
        try:
            models = await adapter.get_models()
            if models:
                print(f"   ✅ Found {len(models)} model(s):")
                for model in models[:5]:  # Show first 5
                    print(f"      - {model}")
                if len(models) > 5:
                    print(f"      ... and {len(models) - 5} more")
            else:
                print("   ⚠️  No models found")
        except Exception as e:
            print(f"   ⚠️  Could not retrieve models: {e}")

        # Detailed test
        if detailed:
            print("\n3️⃣  Execution Test...")
            test_prompt = "Say hello in one sentence"
            print(f"   Prompt: '{test_prompt}'")
            print(f"   Response: ", end="", flush=True)

            try:
                chunks = []
                async for chunk in adapter.execute(test_prompt, timeout=30):
                    print(chunk, end="", flush=True)
                    chunks.append(chunk)

                response = "".join(chunks)
                print(f"\n   ✅ Execution successful ({len(response)} chars)")
            except Exception as e:
                print(f"\n   ❌ Execution failed: {e}")
                return False

        print("\n" + "="*60)
        print("✅ Ollama Remote: PASSED")
        print("="*60)
        return True

    async def test_lmstudio(self, detailed=False):
        """Test LM Studio service."""
        print("\n" + "="*60)
        print("Testing LM Studio")
        print("="*60)

        service_config = self.config.services.get("lmstudio")
        if not service_config:
            print("❌ lmstudio not found in configuration")
            return False

        if not service_config.enabled:
            print("⚠️  lmstudio is disabled in configuration")
            print("   Enable it in config/default.yaml or run:")
            print("   ./scripts/setup_lmstudio.sh --ip YOUR_IP")
            return False

        print(f"\nBase URL: {service_config.base_url}")
        print(f"API Type: {service_config.api_type}")

        # Create adapter
        adapter = OllamaHTTPAdapter("lmstudio", service_config.model_dump())

        # Health check
        print("\n1️⃣  Health Check...")
        try:
            is_healthy = await adapter.health_check()
            if is_healthy:
                print("   ✅ Service is healthy")
            else:
                print("   ❌ Service failed health check")
                return False
        except Exception as e:
            print(f"   ❌ Health check error: {e}")
            return False

        # Get models
        print("\n2️⃣  Loaded Models...")
        try:
            models = await adapter.get_models()
            if models:
                print(f"   ✅ Found {len(models)} loaded model(s):")
                for model in models:
                    print(f"      - {model}")
            else:
                print("   ⚠️  No models loaded in LM Studio")
                print("      Please load a model in LM Studio")
        except Exception as e:
            print(f"   ⚠️  Could not retrieve models: {e}")

        # Detailed test
        if detailed and models:
            print("\n3️⃣  Execution Test...")
            test_prompt = "Say hello in one sentence"
            print(f"   Prompt: '{test_prompt}'")
            print(f"   Response: ", end="", flush=True)

            try:
                chunks = []
                async for chunk in adapter.execute(test_prompt, timeout=30):
                    print(chunk, end="", flush=True)
                    chunks.append(chunk)

                response = "".join(chunks)
                print(f"\n   ✅ Execution successful ({len(response)} chars)")
            except Exception as e:
                print(f"\n   ❌ Execution failed: {e}")
                return False

        print("\n" + "="*60)
        print("✅ LM Studio: PASSED")
        print("="*60)
        return True

    def scan_network(self, network_range="192.168.1.0/24"):
        """Scan network for Ollama and LM Studio services."""
        print("\n" + "="*60)
        print(f"Scanning network: {network_range}")
        print("="*60)
        print("\nLooking for Ollama (port 11434) and LM Studio (port 1234)...")
        print("This may take a minute...\n")

        import ipaddress

        network = ipaddress.IPv4Network(network_range, strict=False)
        found_services = []

        # Common ports
        ports = {
            11434: "Ollama",
            1234: "LM Studio"
        }

        for ip in network.hosts():
            ip_str = str(ip)

            for port, service_name in ports.items():
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.5)

                try:
                    result = sock.connect_ex((ip_str, port))
                    if result == 0:
                        print(f"✅ Found {service_name} at {ip_str}:{port}")
                        found_services.append({
                            "ip": ip_str,
                            "port": port,
                            "service": service_name
                        })
                except:
                    pass
                finally:
                    sock.close()

        print("\n" + "="*60)
        if found_services:
            print(f"✅ Scan complete: Found {len(found_services)} service(s)")
            print("="*60)
            print("\nTo configure these services, run:")
            for service in found_services:
                if service["service"] == "Ollama":
                    print(f"  ./scripts/setup_ollama_remote.sh --ip {service['ip']}")
                elif service["service"] == "LM Studio":
                    print(f"  ./scripts/setup_lmstudio.sh --ip {service['ip']}")
        else:
            print("⚠️  No services found")
            print("="*60)
            print("\nMake sure:")
            print("  1. Services are running")
            print("  2. Network access is enabled")
            print("  3. Firewall allows the ports")


async def main():
    parser = argparse.ArgumentParser(description="Test Oxide network services")
    parser.add_argument(
        "--service",
        type=str,
        choices=["ollama_remote", "lmstudio"],
        help="Test specific service"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Test all network services with detailed execution"
    )
    parser.add_argument(
        "--scan",
        type=str,
        metavar="NETWORK",
        help="Scan network for services (e.g., 192.168.1.0/24)"
    )

    args = parser.parse_args()

    print("🌐 Oxide Network Services Tester")

    tester = NetworkTester()

    # Scan network
    if args.scan:
        tester.scan_network(args.scan)
        return 0

    # Test specific service
    if args.service:
        if args.service == "ollama_remote":
            success = await tester.test_ollama_remote(detailed=True)
        elif args.service == "lmstudio":
            success = await tester.test_lmstudio(detailed=True)

        return 0 if success else 1

    # Test all services
    if args.all:
        results = {}
        results["ollama_remote"] = await tester.test_ollama_remote(detailed=True)
        results["lmstudio"] = await tester.test_lmstudio(detailed=True)

        # Summary
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)

        for service, success in results.items():
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"{service:20s} {status}")

        passed = sum(1 for s in results.values() if s)
        total = len(results)
        print(f"\nTotal: {passed}/{total} services passed")

        return 0 if passed == total else 1

    # No arguments - show help
    parser.print_help()
    return 0


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
