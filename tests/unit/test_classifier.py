"""
Unit tests for TaskClassifier.
"""
import pytest
from pathlib import Path

from oxide.core.classifier import TaskClassifier, TaskType, TaskInfo


class TestTaskClassifier:
    """Test suite for TaskClassifier."""

    @pytest.fixture
    def classifier(self):
        """Create a TaskClassifier instance."""
        return TaskClassifier()

    def test_classify_quick_query_no_files(self, classifier):
        """Test classification of quick queries without files."""
        result = classifier.classify("What is Python?")

        assert result.task_type == TaskType.QUICK_QUERY
        assert result.file_count == 0
        assert result.use_parallel is False
        assert result.estimated_latency == "low"

    def test_classify_code_review_with_keyword(self, classifier):
        """Test classification of code review tasks."""
        result = classifier.classify("Review this code for bugs", files=["test.py"])

        assert result.task_type == TaskType.CODE_REVIEW
        assert result.file_count == 1
        assert "qwen" in result.recommended_services

    def test_classify_code_generation(self, classifier):
        """Test classification of code generation tasks."""
        # Add files to avoid quick_query classification
        result = classifier.classify("Generate a REST API endpoint", files=["main.py"])

        assert result.task_type == TaskType.CODE_GENERATION
        assert "qwen" in result.recommended_services or "ollama_local" in result.recommended_services

    def test_classify_debugging(self, classifier):
        """Test classification of debugging tasks."""
        # Add files to avoid quick_query classification
        result = classifier.classify("Debug this error in the authentication module", files=["auth.py"])

        assert result.task_type == TaskType.DEBUGGING
        assert "qwen" in result.recommended_services

    def test_classify_refactoring(self, classifier):
        """Test classification of refactoring tasks."""
        result = classifier.classify("Refactor this code to improve performance", files=["main.py"])

        assert result.task_type == TaskType.REFACTORING

    def test_classify_documentation(self, classifier):
        """Test classification of documentation tasks."""
        # Add files to avoid quick_query classification
        result = classifier.classify("Document this API with docstrings", files=["api.py"])

        assert result.task_type == TaskType.DOCUMENTATION

    def test_classify_architecture_design(self, classifier):
        """Test classification of architecture design tasks."""
        # Add files to avoid quick_query classification
        result = classifier.classify("Design the system architecture for microservices", files=["system.py"])

        assert result.task_type == TaskType.ARCHITECTURE_DESIGN
        assert "gemini" in result.recommended_services

    def test_classify_large_codebase(self, classifier, tmp_path):
        """Test classification of large codebase analysis."""
        # Create multiple files
        files = []
        for i in range(25):
            file_path = tmp_path / f"file_{i}.py"
            file_path.write_text(f"# File {i}\n" + "x" * 1000)
            files.append(str(file_path))

        result = classifier.classify("Analyze this codebase", files=files)

        assert result.task_type == TaskType.CODEBASE_ANALYSIS
        assert result.file_count == 25
        assert result.use_parallel is True
        assert "gemini" in result.recommended_services
        assert result.estimated_latency == "high"

    def test_calculate_complexity_no_files(self, classifier):
        """Test complexity calculation with no files."""
        result = classifier.classify("Simple query")

        assert result.complexity_score == 0.0

    def test_calculate_complexity_many_files(self, classifier, tmp_path):
        """Test complexity calculation with many files."""
        files = []
        for i in range(50):
            file_path = tmp_path / f"file_{i}.py"
            file_path.write_text("x" * 10000)
            files.append(str(file_path))

        result = classifier.classify("Analyze", files=files)

        # Complexity is based on normalized values, adjust expectation
        assert result.complexity_score > 0.2
        assert result.complexity_score <= 1.0

    def test_calculate_total_size_nonexistent_file(self, classifier):
        """Test handling of nonexistent files."""
        result = classifier.classify("Test", files=["/nonexistent/file.py"])

        # Should not crash, just skip the file
        assert result.file_count == 1
        assert result.total_size_bytes == 0

    def test_parallel_execution_threshold(self, classifier, tmp_path):
        """Test that parallel execution is recommended for large codebases."""
        # Just above threshold
        files = []
        for i in range(21):
            file_path = tmp_path / f"file_{i}.py"
            file_path.write_text("content")
            files.append(str(file_path))

        result = classifier.classify("Analyze codebase", files=files)

        assert result.use_parallel is True

    def test_no_parallel_for_small_codebase(self, classifier):
        """Test that parallel execution is not used for small codebases."""
        result = classifier.classify("Review", files=["file1.py", "file2.py"])

        assert result.use_parallel is False

    def test_keyword_matching_case_insensitive(self, classifier):
        """Test that keyword matching is case-insensitive."""
        # Add files to avoid quick_query classification
        result1 = classifier.classify("REVIEW this code", files=["code.py"])
        result2 = classifier.classify("review this code", files=["code.py"])

        assert result1.task_type == result2.task_type == TaskType.CODE_REVIEW

    def test_multiple_keywords_priority(self, classifier):
        """Test that codebase size takes priority over keywords."""
        # Even with "review" keyword, large codebase should be classified as analysis
        files = [f"file_{i}.py" for i in range(25)]
        result = classifier.classify("Review this large codebase", files=files)

        assert result.task_type == TaskType.CODEBASE_ANALYSIS

    def test_estimated_latency_quick_query(self, classifier):
        """Test latency estimation for quick queries."""
        result = classifier.classify("What is Python?")

        assert result.estimated_latency == "low"

    def test_estimated_latency_large_codebase(self, classifier):
        """Test latency estimation for large codebases."""
        files = [f"file_{i}.py" for i in range(60)]
        result = classifier.classify("Analyze", files=files)

        assert result.estimated_latency == "high"

    def test_recommended_services_codebase_analysis(self, classifier):
        """Test service recommendations for codebase analysis."""
        files = [f"file_{i}.py" for i in range(25)]
        result = classifier.classify("Analyze architecture", files=files)

        assert "gemini" in result.recommended_services
