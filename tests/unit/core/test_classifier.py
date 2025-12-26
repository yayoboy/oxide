"""
Unit tests for TaskClassifier.

Tests task classification logic, complexity calculation, service recommendations,
and edge cases for all task types.
"""
import pytest
from pathlib import Path

from oxide.core.classifier import TaskClassifier, TaskType, TaskInfo


class TestTaskClassifier:
    """Test suite for TaskClassifier"""

    def test_init(self):
        """Test classifier initialization"""
        classifier = TaskClassifier()
        assert classifier is not None
        assert hasattr(classifier, 'logger')

    # Quick Query Tests

    def test_classify_quick_query_no_files(self, sample_prompts):
        """Test classification of quick queries without files"""
        classifier = TaskClassifier()
        task_info = classifier.classify(sample_prompts["quick_query"])

        assert task_info.task_type == TaskType.QUICK_QUERY
        assert task_info.file_count == 0
        assert task_info.total_size_bytes == 0
        assert task_info.complexity_score < 0.3
        assert "ollama_local" in task_info.recommended_services
        assert task_info.use_parallel is False
        assert task_info.estimated_latency == "low"

    def test_classify_quick_query_short_prompt(self):
        """Test quick query with very short prompt"""
        classifier = TaskClassifier()
        task_info = classifier.classify("hi")

        assert task_info.task_type == TaskType.QUICK_QUERY
        assert task_info.complexity_score < 0.1

    # Code Review Tests

    def test_classify_code_review_keyword(self, sample_prompts, sample_task_files):
        """Test code review detection by keyword"""
        classifier = TaskClassifier()
        task_info = classifier.classify(
            sample_prompts["code_review"],
            files=sample_task_files
        )

        assert task_info.task_type == TaskType.CODE_REVIEW
        assert "qwen" in task_info.recommended_services
        assert task_info.file_count == 3

    def test_classify_code_review_variations(self):
        """Test different code review keyword variations"""
        classifier = TaskClassifier()

        variations = [
            "review this code",
            "analyze the implementation",
            "check for bugs",
            "audit this function",
            "inspect the codebase",
            "examine this file"
        ]

        for prompt in variations:
            task_info = classifier.classify(prompt, files=["test.py"])
            assert task_info.task_type == TaskType.CODE_REVIEW, f"Failed for: {prompt}"

    # Code Generation Tests

    def test_classify_code_generation_keyword(self, sample_prompts):
        """Test code generation detection"""
        classifier = TaskClassifier()
        task_info = classifier.classify(sample_prompts["code_generation"])

        assert task_info.task_type == TaskType.CODE_GENERATION
        assert "qwen" in task_info.recommended_services

    def test_classify_code_generation_variations(self):
        """Test different generation keyword variations"""
        classifier = TaskClassifier()

        variations = [
            "write a function",
            "create a class",
            "generate a script",
            "implement sorting",
            "build an API",
            "add a feature",
            "make a utility"
        ]

        for prompt in variations:
            task_info = classifier.classify(prompt)
            assert task_info.task_type == TaskType.CODE_GENERATION, f"Failed for: {prompt}"

    # Debugging Tests

    def test_classify_debugging_keyword(self, sample_prompts):
        """Test debugging task detection"""
        classifier = TaskClassifier()
        task_info = classifier.classify(sample_prompts["debugging"])

        assert task_info.task_type == TaskType.DEBUGGING
        assert "qwen" in task_info.recommended_services

    def test_classify_debugging_variations(self):
        """Test debugging keyword variations"""
        classifier = TaskClassifier()

        variations = [
            "debug this function",
            "fix the bug",
            "solve this error",
            "find the issue",
            "resolve the problem",
            "repair broken code"
        ]

        for prompt in variations:
            task_info = classifier.classify(prompt)
            assert task_info.task_type == TaskType.DEBUGGING

    # Refactoring Tests

    def test_classify_refactoring_keyword(self, sample_prompts):
        """Test refactoring task detection"""
        classifier = TaskClassifier()
        task_info = classifier.classify(sample_prompts["refactoring"])

        assert task_info.task_type == TaskType.REFACTORING
        assert "qwen" in task_info.recommended_services

    def test_classify_refactoring_variations(self):
        """Test refactoring keyword variations"""
        classifier = TaskClassifier()

        variations = [
            "refactor this code",
            "improve the structure",
            "optimize performance",
            "clean up the mess",
            "restructure components"
        ]

        for prompt in variations:
            task_info = classifier.classify(prompt)
            assert task_info.task_type == TaskType.REFACTORING

    # Documentation Tests

    def test_classify_documentation_keyword(self, sample_prompts):
        """Test documentation task detection"""
        classifier = TaskClassifier()
        task_info = classifier.classify(sample_prompts["documentation"])

        assert task_info.task_type == TaskType.DOCUMENTATION
        assert "ollama_local" in task_info.recommended_services

    def test_classify_documentation_variations(self):
        """Test documentation keyword variations"""
        classifier = TaskClassifier()

        variations = [
            "document this API",
            "write docs for",
            "create README",
            "add comments to",
            "explain how this works",
            "describe the interface"
        ]

        for prompt in variations:
            task_info = classifier.classify(prompt)
            assert task_info.task_type == TaskType.DOCUMENTATION

    # Architecture Design Tests

    def test_classify_architecture_keyword(self, sample_prompts):
        """Test architecture design detection"""
        classifier = TaskClassifier()
        task_info = classifier.classify(sample_prompts["architecture"])

        assert task_info.task_type == TaskType.ARCHITECTURE_DESIGN
        assert "gemini" in task_info.recommended_services

    def test_classify_architecture_variations(self):
        """Test architecture keyword variations"""
        classifier = TaskClassifier()

        variations = [
            "design the architecture",
            "create system design",
            "define the structure",
            "architect a solution",
            "design patterns for"
        ]

        for prompt in variations:
            task_info = classifier.classify(prompt)
            assert task_info.task_type == TaskType.ARCHITECTURE_DESIGN

    # Codebase Analysis Tests

    def test_classify_codebase_analysis_many_files(self, large_file_set):
        """Test codebase analysis with 20+ files"""
        classifier = TaskClassifier()
        task_info = classifier.classify(
            "Analyze this project",
            files=large_file_set
        )

        assert task_info.task_type == TaskType.CODEBASE_ANALYSIS
        assert task_info.file_count > 20
        assert "gemini" in task_info.recommended_services
        assert task_info.use_parallel is True
        assert task_info.estimated_latency == "high"

    def test_classify_codebase_analysis_large_size(self, tmp_path):
        """Test codebase analysis with large total size"""
        classifier = TaskClassifier()

        # Create files totaling > 500KB
        large_file = tmp_path / "large.py"
        large_file.write_text("# " + "x" * 600000)  # >500KB

        task_info = classifier.classify(
            "Analyze this",
            files=[str(large_file)]
        )

        assert task_info.task_type == TaskType.CODEBASE_ANALYSIS
        assert task_info.total_size_bytes > 500000

    # Complexity Calculation Tests

    def test_complexity_score_minimal(self):
        """Test complexity score for minimal task"""
        classifier = TaskClassifier()
        task_info = classifier.classify("hi")

        # No files, short prompt
        assert 0.0 <= task_info.complexity_score < 0.1

    def test_complexity_score_moderate(self, sample_task_files):
        """Test complexity score for moderate task"""
        classifier = TaskClassifier()
        prompt = "a" * 500  # Medium length prompt
        task_info = classifier.classify(prompt, files=sample_task_files)

        assert 0.2 <= task_info.complexity_score <= 0.6

    def test_complexity_score_maximum(self, tmp_path):
        """Test complexity score for maximum complexity task"""
        classifier = TaskClassifier()

        # Create 100 large files
        files = []
        for i in range(100):
            f = tmp_path / f"file_{i}.py"
            f.write_text("x" * 100000)  # 100KB each = 10MB total
            files.append(str(f))

        prompt = "a" * 2000  # Very long prompt
        task_info = classifier.classify(prompt, files=files)

        # Should be close to 1.0
        assert task_info.complexity_score > 0.8

    def test_complexity_score_normalization(self):
        """Test that complexity score is normalized to 0.0-1.0"""
        classifier = TaskClassifier()

        # Try various inputs
        test_cases = [
            ("hi", []),
            ("medium prompt " * 50, []),
            ("long prompt " * 500, [])
        ]

        for prompt, files in test_cases:
            task_info = classifier.classify(prompt, files)
            assert 0.0 <= task_info.complexity_score <= 1.0

    # File Size Calculation Tests

    def test_calculate_total_size_no_files(self):
        """Test size calculation with no files"""
        classifier = TaskClassifier()
        size = classifier._calculate_total_size([])
        assert size == 0

    def test_calculate_total_size_valid_files(self, sample_task_files):
        """Test size calculation with valid files"""
        classifier = TaskClassifier()
        size = classifier._calculate_total_size(sample_task_files)
        assert size > 0

    def test_calculate_total_size_nonexistent_file(self):
        """Test size calculation with nonexistent file"""
        classifier = TaskClassifier()
        size = classifier._calculate_total_size(["/nonexistent/file.py"])
        # Should handle gracefully and return 0
        assert size == 0

    def test_calculate_total_size_mixed_files(self, sample_task_files):
        """Test size calculation with mix of valid and invalid files"""
        classifier = TaskClassifier()
        files = sample_task_files + ["/nonexistent.py"]
        size = classifier._calculate_total_size(files)
        # Should only count valid files
        assert size > 0

    # Service Recommendation Tests

    def test_recommend_services_codebase_analysis(self):
        """Test service recommendations for codebase analysis"""
        classifier = TaskClassifier()
        recommendations = classifier._recommend_services(
            TaskType.CODEBASE_ANALYSIS,
            file_count=25,
            total_size=1000000
        )

        assert "gemini" in recommendations
        assert len(recommendations) > 0

    def test_recommend_services_quick_query(self):
        """Test service recommendations for quick query"""
        classifier = TaskClassifier()
        recommendations = classifier._recommend_services(
            TaskType.QUICK_QUERY,
            file_count=0,
            total_size=0
        )

        assert "ollama_local" in recommendations

    def test_recommend_services_all_types(self):
        """Test that all task types have recommendations"""
        classifier = TaskClassifier()

        for task_type in TaskType:
            recommendations = classifier._recommend_services(
                task_type,
                file_count=1,
                total_size=1000
            )
            assert len(recommendations) > 0, f"No recommendations for {task_type}"

    # Parallel Execution Tests

    def test_should_use_parallel_large_codebase(self):
        """Test parallel recommendation for large codebase"""
        classifier = TaskClassifier()
        should_parallel = classifier._should_use_parallel(
            TaskType.CODEBASE_ANALYSIS,
            file_count=30
        )
        assert should_parallel is True

    def test_should_use_parallel_small_task(self):
        """Test parallel not recommended for small tasks"""
        classifier = TaskClassifier()
        should_parallel = classifier._should_use_parallel(
            TaskType.QUICK_QUERY,
            file_count=0
        )
        assert should_parallel is False

    def test_should_use_parallel_threshold(self):
        """Test parallel threshold boundary"""
        classifier = TaskClassifier()

        # Just below threshold
        should_parallel_19 = classifier._should_use_parallel(
            TaskType.CODEBASE_ANALYSIS,
            file_count=19
        )
        assert should_parallel_19 is False

        # At threshold
        should_parallel_20 = classifier._should_use_parallel(
            TaskType.CODEBASE_ANALYSIS,
            file_count=20
        )
        assert should_parallel_20 is False

        # Above threshold
        should_parallel_21 = classifier._should_use_parallel(
            TaskType.CODEBASE_ANALYSIS,
            file_count=21
        )
        assert should_parallel_21 is True

    # Latency Estimation Tests

    def test_estimate_latency_quick_query(self):
        """Test latency estimation for quick queries"""
        classifier = TaskClassifier()
        latency = classifier._estimate_latency(
            TaskType.QUICK_QUERY,
            file_count=0,
            total_size=0
        )
        assert latency == "low"

    def test_estimate_latency_codebase_analysis(self):
        """Test latency estimation for codebase analysis"""
        classifier = TaskClassifier()
        latency = classifier._estimate_latency(
            TaskType.CODEBASE_ANALYSIS,
            file_count=25,
            total_size=1000000
        )
        assert latency == "high"

    def test_estimate_latency_many_files(self):
        """Test latency estimation with many files"""
        classifier = TaskClassifier()
        latency = classifier._estimate_latency(
            TaskType.CODE_REVIEW,
            file_count=60,
            total_size=500000
        )
        assert latency == "high"

    def test_estimate_latency_medium_task(self):
        """Test latency estimation for medium complexity task"""
        classifier = TaskClassifier()
        latency = classifier._estimate_latency(
            TaskType.CODE_REVIEW,
            file_count=5,
            total_size=10000
        )
        assert latency == "medium"

    # Edge Cases and Error Handling

    def test_classify_empty_prompt(self):
        """Test classification with empty prompt"""
        classifier = TaskClassifier()
        task_info = classifier.classify("")

        # Should default to quick query
        assert task_info.task_type == TaskType.QUICK_QUERY

    def test_classify_only_whitespace_prompt(self):
        """Test classification with whitespace-only prompt"""
        classifier = TaskClassifier()
        task_info = classifier.classify("   \n\t  ")

        assert task_info.task_type == TaskType.QUICK_QUERY

    def test_classify_very_long_prompt(self):
        """Test classification with extremely long prompt"""
        classifier = TaskClassifier()
        long_prompt = "analyze " * 10000  # Very long prompt
        task_info = classifier.classify(long_prompt)

        # Should handle without crashing
        assert task_info is not None
        assert 0.0 <= task_info.complexity_score <= 1.0

    def test_classify_with_files_but_no_keywords(self, sample_task_files):
        """Test classification with files but no specific keywords"""
        classifier = TaskClassifier()
        task_info = classifier.classify(
            "Tell me about this",
            files=sample_task_files
        )

        # Should default to code review when files are present
        assert task_info.task_type == TaskType.CODE_REVIEW

    def test_classify_mixed_keywords(self):
        """Test classification with multiple conflicting keywords"""
        classifier = TaskClassifier()
        task_info = classifier.classify(
            "review and fix and refactor and document this code"
        )

        # Should pick first matching keyword (review)
        assert task_info.task_type in [
            TaskType.CODE_REVIEW,
            TaskType.DEBUGGING,
            TaskType.REFACTORING,
            TaskType.DOCUMENTATION
        ]

    def test_classify_case_insensitive(self):
        """Test that classification is case-insensitive"""
        classifier = TaskClassifier()

        prompts = [
            "REVIEW THIS CODE",
            "Review This Code",
            "review this code"
        ]

        results = [classifier.classify(p) for p in prompts]

        # All should be classified the same
        assert all(r.task_type == TaskType.CODE_REVIEW for r in results)

    # Integration Tests

    def test_classify_returns_complete_task_info(self, sample_prompts, sample_task_files):
        """Test that classify returns complete TaskInfo"""
        classifier = TaskClassifier()
        task_info = classifier.classify(
            sample_prompts["code_review"],
            files=sample_task_files
        )

        # Verify all fields are populated
        assert isinstance(task_info.task_type, TaskType)
        assert isinstance(task_info.file_count, int)
        assert isinstance(task_info.total_size_bytes, int)
        assert isinstance(task_info.complexity_score, float)
        assert isinstance(task_info.recommended_services, list)
        assert isinstance(task_info.use_parallel, bool)
        assert isinstance(task_info.estimated_latency, str)

    def test_classify_logging(self, mock_logger, monkeypatch, sample_prompts):
        """Test that classification logs appropriately"""
        classifier = TaskClassifier()
        monkeypatch.setattr(classifier, 'logger', mock_logger)

        classifier.classify(sample_prompts["quick_query"])

        # Verify logging occurred
        mock_logger.info.assert_called()
