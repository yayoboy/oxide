"""
Parallel execution engine for distributing tasks across multiple LLMs.

MVP implementation supports "split" strategy (divide files among services).
"""
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..utils.logging import logger
from ..utils.exceptions import ExecutionError


@dataclass
class ParallelResult:
    """Result from parallel execution."""
    aggregated_text: str
    individual_results: List[Dict[str, Any]]
    services_used: List[str]
    total_duration_seconds: float
    successful_tasks: int
    failed_tasks: int


class ParallelExecutor:
    """
    Executes tasks in parallel across multiple LLM services.

    MVP version supports file splitting strategy for large codebase analysis.
    """

    def __init__(self, max_workers: int = 3):
        """
        Initialize parallel executor.

        Args:
            max_workers: Maximum number of parallel workers
        """
        self.max_workers = max_workers
        self.logger = logger.getChild("parallel")

    async def execute_parallel(
        self,
        prompt: str,
        files: List[str],
        services: List[str],
        adapters: Dict[str, Any],
        strategy: str = "split"
    ) -> ParallelResult:
        """
        Execute task in parallel across multiple services.

        Args:
            prompt: Task prompt
            files: List of files to analyze
            services: List of service names to use
            adapters: Dictionary of initialized adapters
            strategy: Execution strategy ("split" or "duplicate")

        Returns:
            ParallelResult with aggregated output

        Raises:
            ExecutionError: If parallel execution fails
        """
        import time
        start_time = time.time()

        self.logger.info(
            f"Starting parallel execution: {len(files)} files, "
            f"{len(services)} services, strategy={strategy}"
        )

        if strategy == "split":
            result = await self._execute_split_strategy(
                prompt,
                files,
                services,
                adapters
            )
        elif strategy == "duplicate":
            result = await self._execute_duplicate_strategy(
                prompt,
                files,
                services,
                adapters
            )
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

        duration = time.time() - start_time
        result.total_duration_seconds = duration

        self.logger.info(
            f"Parallel execution completed in {duration:.2f}s: "
            f"{result.successful_tasks} successful, {result.failed_tasks} failed"
        )

        return result

    async def _execute_split_strategy(
        self,
        prompt: str,
        files: List[str],
        services: List[str],
        adapters: Dict[str, Any]
    ) -> ParallelResult:
        """
        Split files among services and execute in parallel.

        Each service analyzes a subset of files.
        """
        # Limit services to available workers
        services_to_use = services[:min(len(services), self.max_workers)]

        # Split files into chunks
        chunks = self._split_files(files, len(services_to_use))

        # Create tasks for each service/chunk pair
        tasks = []
        for service_name, file_chunk in zip(services_to_use, chunks):
            adapter = adapters.get(service_name)
            if not adapter:
                self.logger.warning(f"Adapter not found for {service_name}, skipping")
                continue

            task = self._execute_on_service(
                service_name,
                adapter,
                prompt,
                file_chunk
            )
            tasks.append(task)

        # Execute all tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        individual_results = []
        successful = 0
        failed = 0

        for idx, result in enumerate(results):
            service_name = services_to_use[idx] if idx < len(services_to_use) else "unknown"

            if isinstance(result, Exception):
                self.logger.error(f"Service {service_name} failed: {result}")
                individual_results.append({
                    "service": service_name,
                    "success": False,
                    "error": str(result)
                })
                failed += 1
            else:
                individual_results.append({
                    "service": service_name,
                    "success": True,
                    "output": result
                })
                successful += 1

        # Aggregate successful results
        aggregated = self._aggregate_results(individual_results)

        return ParallelResult(
            aggregated_text=aggregated,
            individual_results=individual_results,
            services_used=services_to_use,
            total_duration_seconds=0.0,  # Will be set by caller
            successful_tasks=successful,
            failed_tasks=failed
        )

    async def _execute_duplicate_strategy(
        self,
        prompt: str,
        files: List[str],
        services: List[str],
        adapters: Dict[str, Any]
    ) -> ParallelResult:
        """
        Send same query to multiple services for comparison.

        All services analyze the same files.
        """
        services_to_use = services[:min(len(services), self.max_workers)]

        # Create tasks
        tasks = []
        for service_name in services_to_use:
            adapter = adapters.get(service_name)
            if not adapter:
                continue

            task = self._execute_on_service(
                service_name,
                adapter,
                prompt,
                files
            )
            tasks.append(task)

        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results (similar to split strategy)
        individual_results = []
        successful = 0
        failed = 0

        for idx, result in enumerate(results):
            service_name = services_to_use[idx]

            if isinstance(result, Exception):
                individual_results.append({
                    "service": service_name,
                    "success": False,
                    "error": str(result)
                })
                failed += 1
            else:
                individual_results.append({
                    "service": service_name,
                    "success": True,
                    "output": result
                })
                successful += 1

        # For duplicate strategy, show all results side-by-side
        aggregated = self._aggregate_duplicate_results(individual_results)

        return ParallelResult(
            aggregated_text=aggregated,
            individual_results=individual_results,
            services_used=services_to_use,
            total_duration_seconds=0.0,
            successful_tasks=successful,
            failed_tasks=failed
        )

    async def _execute_on_service(
        self,
        service_name: str,
        adapter: Any,
        prompt: str,
        files: List[str]
    ) -> str:
        """
        Execute task on a single service.

        Args:
            service_name: Service name
            adapter: Adapter instance
            prompt: Task prompt
            files: Files to include

        Returns:
            Complete response text

        Raises:
            Exception: If execution fails
        """
        self.logger.debug(f"Executing on {service_name} with {len(files)} files")

        chunks = []
        async for chunk in adapter.execute(prompt, files=files):
            chunks.append(chunk)

        response = "".join(chunks)
        self.logger.debug(
            f"{service_name} completed: {len(response)} chars"
        )

        return response

    def _split_files(self, files: List[str], num_chunks: int) -> List[List[str]]:
        """
        Split files into roughly equal chunks.

        Args:
            files: List of file paths
            num_chunks: Number of chunks to create

        Returns:
            List of file lists
        """
        if num_chunks <= 0:
            return []

        if num_chunks == 1:
            return [files]

        chunk_size = len(files) // num_chunks
        remainder = len(files) % num_chunks

        chunks = []
        start = 0

        for i in range(num_chunks):
            # Add one extra file to first 'remainder' chunks
            extra = 1 if i < remainder else 0
            end = start + chunk_size + extra

            chunks.append(files[start:end])
            start = end

        return chunks

    def _aggregate_results(self, individual_results: List[Dict[str, Any]]) -> str:
        """
        Aggregate results from parallel execution (split strategy).

        Simple concatenation with service labels for MVP.
        """
        output_parts = []

        for result in individual_results:
            if not result.get("success"):
                continue

            service = result.get("service", "unknown")
            output = result.get("output", "")

            output_parts.append(f"## Results from {service}\n\n{output}\n")

        if not output_parts:
            return "All parallel tasks failed."

        return "\n---\n\n".join(output_parts)

    def _aggregate_duplicate_results(self, individual_results: List[Dict[str, Any]]) -> str:
        """
        Aggregate results from duplicate strategy (comparison).

        Shows results side-by-side for comparison.
        """
        output_parts = ["# Comparison of Results from Multiple Models\n"]

        for result in individual_results:
            service = result.get("service", "unknown")

            if result.get("success"):
                output = result.get("output", "")
                output_parts.append(f"## {service}\n\n{output}\n")
            else:
                error = result.get("error", "Unknown error")
                output_parts.append(f"## {service}\n\n**Error:** {error}\n")

        return "\n---\n\n".join(output_parts)
