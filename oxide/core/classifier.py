"""
Task classification system for intelligent routing.

Analyzes tasks to determine type, complexity, and recommended services.
"""
from enum import Enum
from pathlib import Path
from typing import List, Optional, Set
from dataclasses import dataclass

from ..utils.logging import logger


class TaskType(str, Enum):
    """Types of tasks that can be classified."""
    CODEBASE_ANALYSIS = "codebase_analysis"
    CODE_REVIEW = "code_review"
    CODE_GENERATION = "code_generation"
    QUICK_QUERY = "quick_query"
    ARCHITECTURE_DESIGN = "architecture_design"
    DEBUGGING = "debugging"
    DOCUMENTATION = "documentation"
    REFACTORING = "refactoring"


@dataclass
class TaskInfo:
    """Information about a classified task."""
    task_type: TaskType
    file_count: int
    total_size_bytes: int
    complexity_score: float  # 0.0 to 1.0
    recommended_services: List[str]
    use_parallel: bool = False
    estimated_latency: str = "medium"  # low, medium, high


class TaskClassifier:
    """
    Classifies tasks based on prompt analysis and file characteristics.

    Uses rule-based heuristics to determine optimal task routing.
    """

    # Keywords for different task types
    REVIEW_KEYWORDS = {"review", "analyze", "check", "audit", "inspect", "examine"}
    GENERATION_KEYWORDS = {"write", "create", "generate", "implement", "build", "add", "make"}
    DEBUG_KEYWORDS = {"debug", "fix", "bug", "error", "issue", "problem", "broken"}
    REFACTOR_KEYWORDS = {"refactor", "improve", "optimize", "clean", "restructure"}
    DOCUMENTATION_KEYWORDS = {"document", "docs", "readme", "comment", "explain", "describe"}
    ARCHITECTURE_KEYWORDS = {"architecture", "design", "structure", "pattern", "system"}

    # Thresholds
    LARGE_CODEBASE_FILES = 20
    LARGE_CODEBASE_SIZE = 500_000  # 500KB
    QUICK_QUERY_MAX_FILES = 0
    QUICK_QUERY_MAX_PROMPT_LENGTH = 200

    def __init__(self):
        self.logger = logger.getChild("classifier")

    def classify(self, prompt: str, files: Optional[List[str]] = None) -> TaskInfo:
        """
        Classify a task based on prompt and files.

        Args:
            prompt: The task prompt/query
            files: Optional list of file paths

        Returns:
            TaskInfo with classification results
        """
        files = files or []
        file_count = len(files)

        # Calculate total file size
        total_size = self._calculate_total_size(files)

        # Analyze prompt
        prompt_lower = prompt.lower()
        prompt_words = set(prompt_lower.split())

        # Determine task type
        task_type = self._determine_task_type(
            prompt_lower,
            prompt_words,
            file_count,
            total_size
        )

        # Calculate complexity
        complexity = self._calculate_complexity(
            file_count,
            total_size,
            len(prompt)
        )

        # Determine recommended services
        recommended_services = self._recommend_services(task_type, file_count, total_size)

        # Determine if parallel execution is beneficial
        use_parallel = self._should_use_parallel(task_type, file_count)

        # Estimate latency
        estimated_latency = self._estimate_latency(task_type, file_count, total_size)

        task_info = TaskInfo(
            task_type=task_type,
            file_count=file_count,
            total_size_bytes=total_size,
            complexity_score=complexity,
            recommended_services=recommended_services,
            use_parallel=use_parallel,
            estimated_latency=estimated_latency
        )

        self.logger.info(
            f"Classified task: type={task_type.value}, files={file_count}, "
            f"size={total_size}, complexity={complexity:.2f}, parallel={use_parallel}"
        )

        return task_info

    def _determine_task_type(
        self,
        prompt_lower: str,
        prompt_words: Set[str],
        file_count: int,
        total_size: int
    ) -> TaskType:
        """
        Determine task type based on heuristics.
        """
        # Large codebase analysis
        if file_count > self.LARGE_CODEBASE_FILES or total_size > self.LARGE_CODEBASE_SIZE:
            return TaskType.CODEBASE_ANALYSIS

        # Quick query (no files, short prompt)
        if file_count == self.QUICK_QUERY_MAX_FILES and len(prompt_lower) < self.QUICK_QUERY_MAX_PROMPT_LENGTH:
            return TaskType.QUICK_QUERY

        # Check for specific keywords
        if prompt_words & self.REVIEW_KEYWORDS:
            return TaskType.CODE_REVIEW

        if prompt_words & self.GENERATION_KEYWORDS:
            return TaskType.CODE_GENERATION

        if prompt_words & self.DEBUG_KEYWORDS:
            return TaskType.DEBUGGING

        if prompt_words & self.REFACTOR_KEYWORDS:
            return TaskType.REFACTORING

        if prompt_words & self.DOCUMENTATION_KEYWORDS:
            return TaskType.DOCUMENTATION

        if prompt_words & self.ARCHITECTURE_KEYWORDS:
            return TaskType.ARCHITECTURE_DESIGN

        # Default to code review if files are present
        if file_count > 0:
            return TaskType.CODE_REVIEW

        # Default to quick query
        return TaskType.QUICK_QUERY

    def _calculate_complexity(
        self,
        file_count: int,
        total_size: int,
        prompt_length: int
    ) -> float:
        """
        Calculate complexity score (0.0 to 1.0).

        Considers file count, size, and prompt length.
        """
        # File count factor (0-1, normalized to 100 files)
        file_factor = min(file_count / 100, 1.0)

        # Size factor (0-1, normalized to 5MB)
        size_factor = min(total_size / (5 * 1024 * 1024), 1.0)

        # Prompt factor (0-1, normalized to 1000 chars)
        prompt_factor = min(prompt_length / 1000, 1.0)

        # Weighted average
        complexity = (
            0.4 * file_factor +
            0.4 * size_factor +
            0.2 * prompt_factor
        )

        return round(complexity, 2)

    def _recommend_services(
        self,
        task_type: TaskType,
        file_count: int,
        total_size: int
    ) -> List[str]:
        """
        Recommend services based on task type.
        """
        recommendations = {
            TaskType.CODEBASE_ANALYSIS: ["gemini", "qwen"],
            TaskType.CODE_REVIEW: ["qwen", "ollama_local"],
            TaskType.CODE_GENERATION: ["qwen", "ollama_local"],
            TaskType.QUICK_QUERY: ["ollama_local", "ollama_remote"],
            TaskType.ARCHITECTURE_DESIGN: ["gemini", "qwen"],
            TaskType.DEBUGGING: ["qwen", "ollama_local"],
            TaskType.DOCUMENTATION: ["ollama_local", "qwen"],
            TaskType.REFACTORING: ["qwen", "ollama_local"],
        }

        return recommendations.get(task_type, ["qwen"])

    def _should_use_parallel(self, task_type: TaskType, file_count: int) -> bool:
        """
        Determine if parallel execution is beneficial.
        """
        # Parallel is beneficial for large codebase analysis
        if task_type == TaskType.CODEBASE_ANALYSIS and file_count > self.LARGE_CODEBASE_FILES:
            return True

        return False

    def _estimate_latency(
        self,
        task_type: TaskType,
        file_count: int,
        total_size: int
    ) -> str:
        """
        Estimate expected latency (low, medium, high).
        """
        if task_type == TaskType.QUICK_QUERY:
            return "low"

        if task_type == TaskType.CODEBASE_ANALYSIS or file_count > 50:
            return "high"

        return "medium"

    def _calculate_total_size(self, files: List[str]) -> int:
        """
        Calculate total size of all files in bytes.
        """
        total = 0
        for file_path in files:
            try:
                path = Path(file_path).expanduser().resolve()
                if path.exists() and path.is_file():
                    total += path.stat().st_size
            except (OSError, PermissionError, FileNotFoundError) as e:
                # Expected file system errors
                self.logger.debug(f"Cannot get size of {file_path}: {e}")
            except Exception as e:
                # Unexpected error
                self.logger.warning(f"Unexpected error getting size of {file_path}: {e}")

        return total
