"""
Process lifecycle management for Oxide.

Tracks and manages all spawned subprocesses to ensure proper cleanup
when the MCP server exits (gracefully or forcefully).
"""
import asyncio
import atexit
import signal
import subprocess
import sys
from typing import Set, Optional
from .logging import logger


class ProcessManager:
    """
    Central registry for all spawned processes.

    Ensures all child processes are properly terminated when Oxide exits,
    regardless of exit reason (SIGTERM, SIGINT, exception, etc.).
    """

    def __init__(self):
        self.sync_processes: Set[subprocess.Popen] = set()
        self.async_processes: Set[asyncio.subprocess.Process] = set()
        self._shutdown_initiated = False
        self.logger = logger.getChild("process_manager")

        # Register cleanup handlers
        self._register_handlers()

    def _register_handlers(self):
        """Register signal handlers and atexit cleanup."""
        # Handle SIGTERM (e.g., when Claude Code kills the MCP server)
        signal.signal(signal.SIGTERM, self._handle_signal)

        # Handle SIGINT (Ctrl+C)
        signal.signal(signal.SIGINT, self._handle_signal)

        # Atexit handler as final safety net
        atexit.register(self.cleanup_all)

        self.logger.debug("Registered signal handlers and atexit cleanup")

    def _handle_signal(self, signum, frame):
        """Handle termination signals."""
        sig_name = signal.Signals(signum).name
        self.logger.info(f"Received {sig_name}, initiating cleanup...")

        self.cleanup_all()
        sys.exit(0)

    def register_sync_process(self, process: subprocess.Popen):
        """Register a synchronous subprocess for tracking."""
        if process and process.poll() is None:
            self.sync_processes.add(process)
            self.logger.debug(f"Registered sync process: PID {process.pid}")

    def register_async_process(self, process: asyncio.subprocess.Process):
        """Register an async subprocess for tracking."""
        if process and process.returncode is None:
            self.async_processes.add(process)
            self.logger.debug(f"Registered async process: PID {process.pid}")

    def unregister_sync_process(self, process: subprocess.Popen):
        """Unregister a synchronous subprocess (called when it completes)."""
        self.sync_processes.discard(process)

    def unregister_async_process(self, process: asyncio.subprocess.Process):
        """Unregister an async subprocess (called when it completes)."""
        self.async_processes.discard(process)

    def cleanup_all(self):
        """
        Terminate all tracked processes.

        Attempts graceful termination first, then force kills if needed.
        """
        if self._shutdown_initiated:
            return  # Prevent multiple cleanup attempts

        self._shutdown_initiated = True
        self.logger.info("Cleaning up all spawned processes...")

        # Clean up synchronous processes
        for process in list(self.sync_processes):
            self._cleanup_sync_process(process)

        # Clean up async processes
        for process in list(self.async_processes):
            self._cleanup_async_process(process)

        self.logger.info("Process cleanup completed")

    def _cleanup_sync_process(self, process: subprocess.Popen):
        """Clean up a single synchronous process."""
        if process.poll() is not None:
            # Already terminated
            self.sync_processes.discard(process)
            return

        try:
            pid = process.pid
            self.logger.debug(f"Terminating sync process: PID {pid}")

            # Try graceful termination
            process.terminate()

            try:
                process.wait(timeout=5)
                self.logger.debug(f"Process {pid} terminated gracefully")
            except subprocess.TimeoutExpired:
                # Force kill if timeout
                self.logger.warning(f"Process {pid} didn't terminate, force killing...")
                process.kill()
                process.wait(timeout=2)
                self.logger.debug(f"Process {pid} force killed")

        except Exception as e:
            self.logger.error(f"Error cleaning up sync process: {e}")

        finally:
            self.sync_processes.discard(process)

    def _cleanup_async_process(self, process: asyncio.subprocess.Process):
        """Clean up a single async process."""
        if process.returncode is not None:
            # Already terminated
            self.async_processes.discard(process)
            return

        try:
            pid = process.pid
            self.logger.debug(f"Terminating async process: PID {pid}")

            # Terminate the process
            process.terminate()

            # Note: Can't await here in sync context, but terminate() is effective
            self.logger.debug(f"Sent SIGTERM to process {pid}")

        except Exception as e:
            self.logger.error(f"Error cleaning up async process: {e}")

        finally:
            self.async_processes.discard(process)

    def get_status(self) -> dict:
        """Get current status of tracked processes."""
        return {
            "sync_processes": len(self.sync_processes),
            "async_processes": len(self.async_processes),
            "total": len(self.sync_processes) + len(self.async_processes)
        }


# Global singleton instance
_process_manager: Optional[ProcessManager] = None


def get_process_manager() -> ProcessManager:
    """Get the global ProcessManager instance."""
    global _process_manager
    if _process_manager is None:
        _process_manager = ProcessManager()
    return _process_manager
