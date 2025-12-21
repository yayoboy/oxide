"""
Custom routing rules management for Oxide.

Allows users to define custom task-to-service assignments via Web UI.
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import threading

from .logging import logger


class RoutingRulesManager:
    """
    Manages custom routing rules defined by users.

    Rules are stored as: task_type -> service_name mapping.
    Example: {"coding": "qwen", "review": "gemini", "bug_search": "ollama_local"}
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize routing rules manager.

        Args:
            storage_path: Path to rules JSON file (defaults to ~/.oxide/routing_rules.json)
        """
        if storage_path is None:
            storage_path = Path.home() / ".oxide" / "routing_rules.json"

        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Thread lock for file operations
        self._lock = threading.Lock()

        self.logger = logger.getChild("routing_rules")

        # Ensure file exists
        if not self.storage_path.exists():
            self._write_rules({})

        self.logger.info(f"Routing rules storage initialized: {self.storage_path}")

    def _read_rules(self) -> Dict[str, str]:
        """Read rules from JSON file."""
        try:
            with self._lock:
                with open(self.storage_path, 'r') as f:
                    return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            self.logger.warning(f"Failed to read rules: {e}, returning empty dict")
            return {}

    def _write_rules(self, rules: Dict[str, str]):
        """Write rules to JSON file."""
        try:
            with self._lock:
                with open(self.storage_path, 'w') as f:
                    json.dump(rules, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to write rules: {e}")

    def get_all_rules(self) -> Dict[str, str]:
        """
        Get all routing rules.

        Returns:
            Dictionary of task_type -> service_name mappings
        """
        return self._read_rules()

    def get_rule(self, task_type: str) -> Optional[str]:
        """
        Get assigned service for a specific task type.

        Args:
            task_type: Type of task (e.g., "coding", "review")

        Returns:
            Service name if rule exists, None otherwise
        """
        rules = self._read_rules()
        return rules.get(task_type)

    def add_rule(self, task_type: str, service_name: str) -> Dict[str, Any]:
        """
        Add or update a routing rule.

        Args:
            task_type: Type of task (e.g., "coding", "review", "bug_search")
            service_name: Service to assign (e.g., "qwen", "gemini", "ollama_local")

        Returns:
            Created/updated rule
        """
        rules = self._read_rules()

        # Store the rule
        rules[task_type] = service_name
        self._write_rules(rules)

        self.logger.info(f"Added routing rule: {task_type} -> {service_name}")

        return {
            "task_type": task_type,
            "service": service_name,
            "action": "updated" if task_type in rules else "created"
        }

    def delete_rule(self, task_type: str) -> bool:
        """
        Delete a routing rule.

        Args:
            task_type: Type of task

        Returns:
            True if deleted, False if not found
        """
        rules = self._read_rules()

        if task_type not in rules:
            return False

        del rules[task_type]
        self._write_rules(rules)

        self.logger.info(f"Deleted routing rule: {task_type}")
        return True

    def clear_all_rules(self) -> int:
        """
        Clear all routing rules.

        Returns:
            Number of rules cleared
        """
        rules = self._read_rules()
        count = len(rules)

        self._write_rules({})
        self.logger.info(f"Cleared all routing rules ({count} rules)")

        return count

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about routing rules."""
        rules = self._read_rules()

        # Count rules per service
        service_counts = {}
        for service in rules.values():
            service_counts[service] = service_counts.get(service, 0) + 1

        return {
            "total_rules": len(rules),
            "rules_by_service": service_counts,
            "task_types": list(rules.keys())
        }

    def export_rules(self) -> List[Dict[str, str]]:
        """
        Export rules in a format suitable for API responses.

        Returns:
            List of rule objects with task_type and service fields
        """
        rules = self._read_rules()
        return [
            {"task_type": task_type, "service": service}
            for task_type, service in rules.items()
        ]


# Global singleton instance
_routing_rules_manager: Optional[RoutingRulesManager] = None


def get_routing_rules_manager() -> RoutingRulesManager:
    """Get the global RoutingRulesManager instance."""
    global _routing_rules_manager
    if _routing_rules_manager is None:
        _routing_rules_manager = RoutingRulesManager()
    return _routing_rules_manager
