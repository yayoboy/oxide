#!/usr/bin/env python3
"""
Oxide Unified Launcher

Launches both MCP server and Web UI backend simultaneously.
Useful for starting everything with a single command.

Usage:
    oxide-all                    # Start both services
    oxide-all --mcp-only         # MCP server only
    oxide-all --web-only         # Web backend only
    oxide-all --open-browser     # Auto-open browser
"""
import sys
import signal
import subprocess
import time
import webbrowser
from pathlib import Path
import argparse

from .utils.logging import logger


class OxideLauncher:
    """Launches and manages Oxide services."""

    def __init__(self):
        self.processes = []
        self.logger = logger.getChild("launcher")

    def launch_mcp(self):
        """Launch MCP server."""
        print("🔬 Starting Oxide MCP Server...")

        try:
            # Import and run MCP server in subprocess
            from .mcp.server import main as mcp_main

            # Run in subprocess to keep it separate
            proc = subprocess.Popen(
                [sys.executable, "-m", "oxide.mcp.server"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            self.processes.append(("MCP Server", proc))
            print("✅ MCP Server started (stdio mode)")
            return proc

        except Exception as e:
            print(f"❌ Failed to start MCP server: {e}")
            return None

    def launch_web(self):
        """Launch Web UI backend."""
        print("🌐 Starting Oxide Web Backend...")

        try:
            proc = subprocess.Popen(
                [
                    sys.executable, "-m", "uvicorn",
                    "oxide.web.backend.main:app",
                    "--host", "0.0.0.0",
                    "--port", "8000",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            self.processes.append(("Web Backend", proc))

            # Wait a moment for server to start
            time.sleep(2)

            print("✅ Web Backend started")
            print("   API: http://localhost:8000")
            print("   Docs: http://localhost:8000/docs")

            return proc

        except Exception as e:
            print(f"❌ Failed to start Web backend: {e}")
            return None

    def open_browser(self):
        """Open browser to dashboard."""
        print("\n🌐 Opening browser...")
        time.sleep(1)  # Wait for servers to be ready
        try:
            webbrowser.open("http://localhost:8000/docs")
            print("✅ Browser opened to API docs")
        except Exception as e:
            print(f"⚠️  Could not open browser: {e}")

    def monitor_processes(self):
        """Monitor running processes and display logs."""
        print("\n" + "="*60)
        print("📊 Oxide Services Running")
        print("="*60)
        print("\nPress Ctrl+C to stop all services\n")

        try:
            # Monitor and display logs
            while True:
                for name, proc in self.processes:
                    if proc.poll() is not None:
                        print(f"\n⚠️  {name} stopped unexpectedly (exit code: {proc.returncode})")
                        self.cleanup()
                        return

                time.sleep(1)

        except KeyboardInterrupt:
            print("\n\n⚠️  Shutdown requested...")
            self.cleanup()

    def cleanup(self):
        """Stop all processes."""
        print("\n🛑 Stopping services...")

        for name, proc in self.processes:
            if proc.poll() is None:  # Still running
                print(f"   Stopping {name}...")
                proc.terminate()

                try:
                    proc.wait(timeout=5)
                    print(f"   ✅ {name} stopped")
                except subprocess.TimeoutExpired:
                    print(f"   ⚠️  Force killing {name}...")
                    proc.kill()
                    proc.wait()

        print("✅ All services stopped")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Oxide Unified Launcher - Start MCP and Web UI together"
    )
    parser.add_argument(
        "--mcp-only",
        action="store_true",
        help="Launch only MCP server"
    )
    parser.add_argument(
        "--web-only",
        action="store_true",
        help="Launch only Web backend"
    )
    parser.add_argument(
        "--open-browser",
        action="store_true",
        help="Auto-open browser to API docs"
    )

    args = parser.parse_args()

    print("🚀 Oxide Unified Launcher")
    print("="*60)

    launcher = OxideLauncher()

    # Setup signal handlers
    def signal_handler(sig, frame):
        launcher.cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Launch services
    if args.mcp_only:
        launcher.launch_mcp()
    elif args.web_only:
        launcher.launch_web()
    else:
        # Launch both
        launcher.launch_mcp()
        time.sleep(1)  # Small delay between launches
        launcher.launch_web()

    # Open browser if requested
    if args.open_browser:
        launcher.open_browser()

    # Monitor processes
    launcher.monitor_processes()


if __name__ == "__main__":
    main()
