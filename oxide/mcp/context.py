"""
Server context management for Oxide MCP server.

Replaces global variables with a proper context manager pattern.
"""
import sys
import os
import subprocess
from typing import Optional

from ..core.orchestrator import Orchestrator
from ..config.loader import load_config, Config
from ..utils.logging import logger, setup_logging
from .tools import OxideTools


class OxideServerContext:
    """
    Context manager for Oxide MCP server state.

    Manages orchestrator, tools, and web UI subprocess lifecycle
    without relying on global variables.
    """

    _instance: Optional['OxideServerContext'] = None

    def __init__(self, config: Optional[Config] = None):
        """
        Initialize server context.

        Args:
            config: Optional Config object (loads default if not provided)
        """
        self.config: Optional[Config] = config
        self.orchestrator: Optional[Orchestrator] = None
        self.tools: Optional[OxideTools] = None
        self.web_process: Optional[subprocess.Popen] = None
        self._initialized: bool = False

    @classmethod
    def get_instance(cls) -> 'OxideServerContext':
        """
        Get singleton instance of server context.

        Returns:
            Singleton OxideServerContext instance

        Raises:
            RuntimeError: If instance has not been initialized
        """
        if cls._instance is None:
            raise RuntimeError("OxideServerContext not initialized. Call initialize() first.")
        return cls._instance

    @classmethod
    def initialize(cls, config: Optional[Config] = None) -> 'OxideServerContext':
        """
        Initialize singleton instance.

        Args:
            config: Optional Config object

        Returns:
            Initialized OxideServerContext instance
        """
        if cls._instance is not None:
            logger.warning("OxideServerContext already initialized, returning existing instance")
            return cls._instance

        cls._instance = cls(config)
        cls._instance._setup()
        return cls._instance

    def _setup(self) -> None:
        """Internal setup method."""
        if self._initialized:
            return

        logger.info("Initializing Oxide MCP Server Context")

        try:
            # Load configuration
            if self.config is None:
                self.config = load_config()

            # Setup logging
            setup_logging(
                level=self.config.logging.level,
                log_file=self.config.logging.file,
                console=self.config.logging.console
            )

            # Initialize orchestrator
            self.orchestrator = Orchestrator(self.config)

            # Initialize tools
            self.tools = OxideTools(self.orchestrator)

            self._initialized = True
            logger.info("Oxide MCP Server Context initialized successfully")

            # Auto-start Web UI if enabled
            self.start_web_ui()

        except Exception as e:
            logger.error(f"Failed to initialize Oxide context: {e}")
            raise

    def start_web_ui(self) -> None:
        """Start Web UI backend if enabled via environment variable."""
        if self.web_process is not None and self.web_process.poll() is None:
            logger.debug("Web UI already running")
            return

        # Check if auto-start is enabled
        if os.environ.get("OXIDE_AUTO_START_WEB", "").lower() not in ("true", "1", "yes"):
            logger.debug("Auto-start Web UI disabled")
            return

        logger.info("Auto-starting Web UI backend...")

        try:
            # Start web backend as subprocess
            self.web_process = subprocess.Popen(
                [
                    sys.executable, "-m", "uvicorn",
                    "oxide.web.backend.main:app",
                    "--host", "0.0.0.0",
                    "--port", "8000",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            logger.info(f"Web UI backend started (PID: {self.web_process.pid})")
            print("🌐 Web UI started at http://localhost:8000", file=sys.stderr)

        except Exception as e:
            logger.error(f"Failed to start Web UI: {e}")

    def stop_web_ui(self) -> None:
        """Stop Web UI backend if running."""
        if self.web_process is None or self.web_process.poll() is not None:
            logger.debug("Web UI not running")
            return

        logger.info("Stopping Web UI backend...")
        self.web_process.terminate()

        try:
            self.web_process.wait(timeout=5)
            logger.info("Web UI backend stopped gracefully")
        except subprocess.TimeoutExpired:
            logger.warning("Web UI backend did not stop, force killing...")
            self.web_process.kill()
            self.web_process.wait()
            logger.warning("Web UI backend force killed")

    def cleanup(self) -> None:
        """Clean up resources."""
        logger.info("Cleaning up Oxide Server Context")
        self.stop_web_ui()
        self._initialized = False

    def __enter__(self) -> 'OxideServerContext':
        """Context manager entry."""
        if not self._initialized:
            self._setup()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.cleanup()

    @classmethod
    def reset(cls) -> None:
        """Reset singleton instance (useful for testing)."""
        if cls._instance is not None:
            cls._instance.cleanup()
            cls._instance = None
