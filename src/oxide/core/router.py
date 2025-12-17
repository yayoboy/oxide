"""
Task routing system for service selection.

Determines which LLM service should handle a task based on
classification results and routing rules.
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from ..config.loader import Config, RoutingRuleConfig
from ..utils.exceptions import NoServiceAvailableError, RoutingError
from ..utils.logging import logger
from .classifier import TaskInfo


@dataclass
class RouterDecision:
    """Result of routing decision."""
    primary_service: str
    fallback_services: List[str]
    execution_mode: str  # "single" or "parallel"
    timeout_seconds: Optional[int] = None


class TaskRouter:
    """
    Routes tasks to appropriate LLM services.

    Uses configuration rules and service health checks to make
    intelligent routing decisions with fallback support.
    """

    def __init__(self, config: Config, service_health_checker=None):
        """
        Initialize router.

        Args:
            config: Oxide configuration
            service_health_checker: Optional function to check service health
                                  Signature: async def(service_name: str) -> bool
        """
        self.config = config
        self.routing_rules = config.routing_rules
        self.service_health_checker = service_health_checker
        self.logger = logger.getChild("router")

    async def route(self, task_info: TaskInfo) -> RouterDecision:
        """
        Make routing decision for a task.

        Args:
            task_info: Classified task information

        Returns:
            RouterDecision with service selection

        Raises:
            NoServiceAvailableError: If no service can handle the task
            RoutingError: If routing fails
        """
        task_type_key = task_info.task_type.value

        # Get routing rule for this task type
        rule = self.routing_rules.get(task_type_key)

        if not rule:
            # No specific rule, use recommendations from classifier
            self.logger.warning(
                f"No routing rule for {task_type_key}, using classifier recommendations"
            )
            return await self._route_from_recommendations(task_info)

        # Check if primary service is available
        primary_service = await self._select_available_service(
            rule.primary,
            rule.fallback
        )

        if not primary_service:
            raise NoServiceAvailableError(task_type_key)

        # Determine execution mode
        execution_mode = "parallel" if task_info.use_parallel else "single"

        # Get timeout
        timeout = rule.timeout_seconds or self.config.execution.timeout_seconds

        decision = RouterDecision(
            primary_service=primary_service,
            fallback_services=rule.fallback,
            execution_mode=execution_mode,
            timeout_seconds=timeout
        )

        self.logger.info(
            f"Routed {task_type_key} to {primary_service} "
            f"(mode={execution_mode}, timeout={timeout}s)"
        )

        return decision

    async def _route_from_recommendations(self, task_info: TaskInfo) -> RouterDecision:
        """
        Route based on classifier recommendations when no rule exists.
        """
        recommended = task_info.recommended_services

        if not recommended:
            raise NoServiceAvailableError(task_info.task_type.value)

        # Try to find an available service from recommendations
        primary = await self._select_available_service(
            recommended[0],
            recommended[1:]
        )

        if not primary:
            raise NoServiceAvailableError(task_info.task_type.value)

        return RouterDecision(
            primary_service=primary,
            fallback_services=recommended[1:],
            execution_mode="single",
            timeout_seconds=self.config.execution.timeout_seconds
        )

    async def _select_available_service(
        self,
        primary: str,
        fallbacks: List[str]
    ) -> Optional[str]:
        """
        Select first available service from primary and fallbacks.

        Args:
            primary: Primary service name
            fallbacks: List of fallback service names

        Returns:
            First available service name, or None if none available
        """
        # Try primary first
        if await self._is_service_available(primary):
            return primary

        # Try fallbacks in order
        for fallback in fallbacks:
            if await self._is_service_available(fallback):
                self.logger.info(f"Primary '{primary}' unavailable, using fallback '{fallback}'")
                return fallback

        return None

    async def _is_service_available(self, service_name: str) -> bool:
        """
        Check if a service is available.

        Args:
            service_name: Name of service to check

        Returns:
            True if service is available and enabled
        """
        # Check if service is in config
        if service_name not in self.config.services:
            self.logger.warning(f"Unknown service: {service_name}")
            return False

        service_config = self.config.services[service_name]

        # Check if enabled
        if not service_config.enabled:
            self.logger.debug(f"Service '{service_name}' is disabled")
            return False

        # Perform health check if checker is provided
        if self.service_health_checker:
            try:
                is_healthy = await self.service_health_checker(service_name)
                if not is_healthy:
                    self.logger.debug(f"Service '{service_name}' failed health check")
                return is_healthy
            except Exception as e:
                self.logger.warning(f"Health check error for '{service_name}': {e}")
                return False

        # If no health checker, assume available if enabled
        return True

    def get_routing_rules_summary(self) -> Dict[str, Dict[str, Any]]:
        """
        Get summary of all routing rules.

        Returns:
            Dictionary mapping task types to their routing configuration
        """
        summary = {}
        for task_type, rule in self.routing_rules.items():
            summary[task_type] = {
                "primary": rule.primary,
                "fallback": rule.fallback,
                "parallel_threshold": rule.parallel_threshold_files,
                "timeout": rule.timeout_seconds
            }
        return summary
