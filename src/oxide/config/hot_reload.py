"""
Configuration Hot Reload System

Monitors configuration files and reloads changes without restarting the server.
"""
import asyncio
import time
from pathlib import Path
from typing import Optional, Dict, Any, Callable, List
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

from .loader import load_config, Config, ConfigError
from ..utils.logging import get_logger

logger = get_logger(__name__)


class ConfigChangeEvent:
    """Configuration change event."""

    def __init__(
        self,
        old_config: Config,
        new_config: Config,
        changes: Dict[str, Any]
    ):
        self.old_config = old_config
        self.new_config = new_config
        self.changes = changes
        self.timestamp = time.time()


class ConfigWatcher(FileSystemEventHandler):
    """File system watcher for configuration files."""

    def __init__(self, config_path: Path, callback: Callable[[Path], None]):
        self.config_path = config_path.resolve()
        self.callback = callback
        self.last_modified = 0
        self.debounce_seconds = 1.0  # Ignore changes within 1 second

    def on_modified(self, event: FileModifiedEvent):
        """Handle file modification events."""
        if event.is_directory:
            return

        # Check if modified file is our config file
        modified_path = Path(event.src_path).resolve()
        if modified_path != self.config_path:
            return

        # Debounce - ignore rapid successive changes
        now = time.time()
        if now - self.last_modified < self.debounce_seconds:
            return

        self.last_modified = now
        logger.info(f"Configuration file changed: {self.config_path}")

        # Trigger callback
        try:
            self.callback(self.config_path)
        except Exception as e:
            logger.error(f"Error in config change callback: {e}")


class HotReloadManager:
    """
    Manages configuration hot reload.

    Features:
    - File system watching
    - Automatic reload on change
    - Manual reload API
    - Change detection and diff
    - Callback system for reload events
    """

    def __init__(
        self,
        config_path: Path,
        auto_reload: bool = True,
        watch_interval: float = 1.0
    ):
        """
        Initialize hot reload manager.

        Args:
            config_path: Path to configuration file
            auto_reload: Enable automatic reload on file change
            watch_interval: Debounce interval in seconds
        """
        self.config_path = config_path
        self.auto_reload = auto_reload
        self.watch_interval = watch_interval

        # Current configuration
        self.current_config: Optional[Config] = None

        # File watcher
        self.observer: Optional[Observer] = None
        self.watcher: Optional[ConfigWatcher] = None

        # Reload callbacks
        self.reload_callbacks: List[Callable[[ConfigChangeEvent], None]] = []

        # Statistics
        self.reload_count = 0
        self.last_reload_time: Optional[float] = None
        self.last_reload_success = True

        logger.info(f"Hot reload manager initialized (auto_reload={auto_reload})")

    def start(self):
        """Start watching configuration file."""
        if not self.auto_reload:
            logger.info("Auto-reload disabled, skipping file watcher")
            return

        # Load initial configuration
        try:
            self.current_config = load_config(self.config_path)
            logger.info(f"Initial configuration loaded from {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to load initial configuration: {e}")
            raise

        # Setup file watcher
        self.watcher = ConfigWatcher(
            config_path=self.config_path,
            callback=self._on_file_changed
        )

        self.observer = Observer()
        self.observer.schedule(
            self.watcher,
            path=str(self.config_path.parent),
            recursive=False
        )
        self.observer.start()

        logger.info(f"Watching configuration file: {self.config_path}")

    def stop(self):
        """Stop watching configuration file."""
        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=5.0)
            logger.info("Configuration watcher stopped")

    def _on_file_changed(self, config_path: Path):
        """Handle configuration file change."""
        logger.info("Configuration file changed, reloading...")

        try:
            # Reload configuration
            new_config = self.reload()

            # Notify success
            self.last_reload_success = True
            logger.info("✅ Configuration reloaded successfully")

        except Exception as e:
            self.last_reload_success = False
            logger.error(f"❌ Configuration reload failed: {e}")

    def reload(self) -> Config:
        """
        Reload configuration from file.

        Returns:
            New Config object

        Raises:
            ConfigError: If configuration is invalid
        """
        # Load new configuration
        try:
            new_config = load_config(self.config_path)
        except Exception as e:
            self.last_reload_success = False
            raise ConfigError(f"Failed to load configuration: {e}")

        # Detect changes
        changes = self._detect_changes(self.current_config, new_config)

        # Create change event
        event = ConfigChangeEvent(
            old_config=self.current_config,
            new_config=new_config,
            changes=changes
        )

        # Update current config
        old_config = self.current_config
        self.current_config = new_config

        # Update stats
        self.reload_count += 1
        self.last_reload_time = time.time()
        self.last_reload_success = True

        # Trigger callbacks
        self._trigger_callbacks(event)

        logger.info(
            f"Configuration reloaded (reload #{self.reload_count}): "
            f"{len(changes)} changes detected"
        )

        return new_config

    def _detect_changes(
        self,
        old_config: Optional[Config],
        new_config: Config
    ) -> Dict[str, Any]:
        """
        Detect changes between configurations.

        Args:
            old_config: Previous configuration (None if first load)
            new_config: New configuration

        Returns:
            Dictionary of changes
        """
        if old_config is None:
            return {"initial_load": True}

        changes = {}

        # Check service changes
        old_services = set(old_config.services.keys())
        new_services = set(new_config.services.keys())

        added_services = new_services - old_services
        removed_services = old_services - new_services

        if added_services:
            changes["services_added"] = list(added_services)

        if removed_services:
            changes["services_removed"] = list(removed_services)

        # Check service modifications
        modified_services = []
        for service_name in old_services & new_services:
            old_svc = old_config.services[service_name]
            new_svc = new_config.services[service_name]

            if old_svc.model_dump() != new_svc.model_dump():
                modified_services.append(service_name)

        if modified_services:
            changes["services_modified"] = modified_services

        # Check routing rule changes
        old_rules = set(old_config.routing_rules.keys())
        new_rules = set(new_config.routing_rules.keys())

        added_rules = new_rules - old_rules
        removed_rules = old_rules - new_rules

        if added_rules:
            changes["routing_rules_added"] = list(added_rules)

        if removed_rules:
            changes["routing_rules_removed"] = list(removed_rules)

        # Check routing rule modifications
        modified_rules = []
        for rule_name in old_rules & new_rules:
            old_rule = old_config.routing_rules[rule_name]
            new_rule = new_config.routing_rules[rule_name]

            if old_rule.model_dump() != new_rule.model_dump():
                modified_rules.append(rule_name)

        if modified_rules:
            changes["routing_rules_modified"] = modified_rules

        # Check execution settings
        if old_config.execution.model_dump() != new_config.execution.model_dump():
            changes["execution_modified"] = True

        # Check logging settings
        if old_config.logging.model_dump() != new_config.logging.model_dump():
            changes["logging_modified"] = True

        return changes

    def add_reload_callback(
        self,
        callback: Callable[[ConfigChangeEvent], None]
    ):
        """
        Add callback to be called on configuration reload.

        Args:
            callback: Function to call with ConfigChangeEvent
        """
        self.reload_callbacks.append(callback)
        logger.debug(f"Added reload callback: {callback.__name__}")

    def remove_reload_callback(
        self,
        callback: Callable[[ConfigChangeEvent], None]
    ):
        """Remove reload callback."""
        if callback in self.reload_callbacks:
            self.reload_callbacks.remove(callback)
            logger.debug(f"Removed reload callback: {callback.__name__}")

    def _trigger_callbacks(self, event: ConfigChangeEvent):
        """Trigger all reload callbacks."""
        for callback in self.reload_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(
                    f"Error in reload callback {callback.__name__}: {e}"
                )

    def get_stats(self) -> Dict[str, Any]:
        """Get reload statistics."""
        return {
            "auto_reload_enabled": self.auto_reload,
            "reload_count": self.reload_count,
            "last_reload_time": self.last_reload_time,
            "last_reload_success": self.last_reload_success,
            "watching": self.observer is not None and self.observer.is_alive(),
            "config_path": str(self.config_path)
        }


# Global hot reload manager instance
_hot_reload_manager: Optional[HotReloadManager] = None


def init_hot_reload(
    config_path: Path,
    auto_reload: bool = True
) -> HotReloadManager:
    """
    Initialize global hot reload manager.

    Args:
        config_path: Path to configuration file
        auto_reload: Enable automatic reload

    Returns:
        HotReloadManager instance
    """
    global _hot_reload_manager

    if _hot_reload_manager is not None:
        logger.warning("Hot reload manager already initialized")
        return _hot_reload_manager

    _hot_reload_manager = HotReloadManager(
        config_path=config_path,
        auto_reload=auto_reload
    )

    return _hot_reload_manager


def get_hot_reload_manager() -> Optional[HotReloadManager]:
    """Get global hot reload manager instance."""
    return _hot_reload_manager
