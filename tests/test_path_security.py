"""
Security tests for file system sandboxing and path validation.
"""
import pytest
from pathlib import Path
import tempfile
import os

from oxide.utils.path_validator import (
    PathValidator,
    SecurityError,
    init_path_validator,
    get_path_validator,
    validate_path,
    validate_paths
)


class TestPathValidator:
    """Test path validation and security features."""

    def test_whitelist_enforcement_allowed(self, tmp_path):
        """Test that paths within allowed directories are accepted."""
        # Create allowed directory
        allowed_dir = tmp_path / "allowed"
        allowed_dir.mkdir()
        test_file = allowed_dir / "test.txt"
        test_file.write_text("test")

        # Initialize validator with allowed directory
        validator = PathValidator(allowed_dirs=[str(allowed_dir)])

        # Should pass validation
        validated_path = validator.validate_path(str(test_file), require_exists=True)
        assert validated_path.exists()
        assert str(validated_path).startswith(str(allowed_dir))

    def test_whitelist_enforcement_denied(self, tmp_path):
        """Test that paths outside allowed directories are rejected."""
        # Create directories
        allowed_dir = tmp_path / "allowed"
        forbidden_dir = tmp_path / "forbidden"
        allowed_dir.mkdir()
        forbidden_dir.mkdir()

        forbidden_file = forbidden_dir / "secret.txt"
        forbidden_file.write_text("secret")

        # Initialize validator with only allowed_dir
        validator = PathValidator(allowed_dirs=[str(allowed_dir)])

        # Should fail validation
        with pytest.raises(SecurityError) as exc_info:
            validator.validate_path(str(forbidden_file))

        assert "outside allowed directories" in str(exc_info.value).lower()

    def test_path_traversal_prevention(self, tmp_path):
        """Test that path traversal attempts are blocked."""
        allowed_dir = tmp_path / "allowed"
        allowed_dir.mkdir()

        validator = PathValidator(allowed_dirs=[str(allowed_dir)])

        # Various path traversal attempts
        traversal_attempts = [
            str(allowed_dir / ".." / "etc" / "passwd"),
            str(allowed_dir / "subdir" / ".." / ".." / "forbidden"),
            "../../../etc/passwd",
            "subdir/../../forbidden/file.txt",
        ]

        for attempt in traversal_attempts:
            with pytest.raises(SecurityError) as exc_info:
                validator.validate_path(attempt)
            assert "path traversal" in str(exc_info.value).lower()

    def test_sensitive_file_protection(self):
        """Test that access to sensitive system files is blocked."""
        # Use a broad whitelist that includes system directories
        validator = PathValidator(allowed_dirs=["/", str(Path.home())])

        sensitive_files = [
            "/etc/passwd",
            "/etc/shadow",
            "/etc/sudoers",
            str(Path.home() / ".ssh" / "id_rsa"),
            str(Path.home() / ".aws" / "credentials"),
            "/root/.bash_history",
        ]

        for sensitive_file in sensitive_files:
            with pytest.raises(SecurityError) as exc_info:
                validator.validate_path(sensitive_file)
            assert "sensitive" in str(exc_info.value).lower()

    def test_symlink_resolution(self, tmp_path):
        """Test that symlinks are resolved and validated."""
        # Create directory structure
        allowed_dir = tmp_path / "allowed"
        forbidden_dir = tmp_path / "forbidden"
        allowed_dir.mkdir()
        forbidden_dir.mkdir()

        # Create file in forbidden directory
        forbidden_file = forbidden_dir / "secret.txt"
        forbidden_file.write_text("secret")

        # Create symlink in allowed directory pointing to forbidden file
        symlink = allowed_dir / "link_to_secret.txt"
        symlink.symlink_to(forbidden_file)

        validator = PathValidator(allowed_dirs=[str(allowed_dir)])

        # Should fail - symlink resolves to forbidden directory
        with pytest.raises(SecurityError):
            validator.validate_path(str(symlink))

    def test_empty_path_rejected(self):
        """Test that empty paths are rejected."""
        validator = PathValidator(allowed_dirs=["/tmp"])

        with pytest.raises(SecurityError) as exc_info:
            validator.validate_path("")
        assert "empty" in str(exc_info.value).lower()

    def test_require_exists_validation(self, tmp_path):
        """Test require_exists parameter."""
        allowed_dir = tmp_path / "allowed"
        allowed_dir.mkdir()

        validator = PathValidator(allowed_dirs=[str(allowed_dir)])

        # Non-existent file without require_exists - should pass
        non_existent = allowed_dir / "does_not_exist.txt"
        validated = validator.validate_path(str(non_existent), require_exists=False)
        assert validated == non_existent

        # Non-existent file with require_exists - should fail
        with pytest.raises(FileNotFoundError):
            validator.validate_path(str(non_existent), require_exists=True)

    def test_multiple_paths_validation(self, tmp_path):
        """Test validating multiple paths at once."""
        allowed_dir = tmp_path / "allowed"
        allowed_dir.mkdir()

        file1 = allowed_dir / "file1.txt"
        file2 = allowed_dir / "file2.txt"
        file1.write_text("test1")
        file2.write_text("test2")

        validator = PathValidator(allowed_dirs=[str(allowed_dir)])

        # Should validate both paths
        validated = validator.validate_paths([str(file1), str(file2)], require_exists=True)
        assert len(validated) == 2
        assert all(p.exists() for p in validated)

    def test_add_allowed_directory(self, tmp_path):
        """Test dynamically adding allowed directories."""
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()

        file1 = dir1 / "file1.txt"
        file2 = dir2 / "file2.txt"
        file1.write_text("test1")
        file2.write_text("test2")

        # Initialize with only dir1
        validator = PathValidator(allowed_dirs=[str(dir1)])

        # file1 should pass
        validator.validate_path(str(file1))

        # file2 should fail
        with pytest.raises(SecurityError):
            validator.validate_path(str(file2))

        # Add dir2 to whitelist
        validator.add_allowed_directory(str(dir2))

        # Now file2 should pass
        validator.validate_path(str(file2))

    def test_is_path_allowed_non_raising(self, tmp_path):
        """Test non-raising path check."""
        allowed_dir = tmp_path / "allowed"
        forbidden_dir = tmp_path / "forbidden"
        allowed_dir.mkdir()
        forbidden_dir.mkdir()

        allowed_file = allowed_dir / "allowed.txt"
        forbidden_file = forbidden_dir / "forbidden.txt"
        allowed_file.write_text("test")
        forbidden_file.write_text("test")

        validator = PathValidator(allowed_dirs=[str(allowed_dir)])

        # Should return True for allowed path
        assert validator.is_path_allowed(str(allowed_file)) is True

        # Should return False for forbidden path (no exception)
        assert validator.is_path_allowed(str(forbidden_file)) is False

    def test_home_directory_expansion(self):
        """Test that ~ is properly expanded and rejected."""
        validator = PathValidator(allowed_dirs=["/tmp"])

        # Tilde should be rejected (caught in traversal check)
        with pytest.raises(SecurityError):
            validator.validate_path("~/Documents/test.txt")

    def test_current_directory_included_by_default(self, tmp_path):
        """Test that current working directory is included in defaults."""
        # Change to tmp directory
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Create validator with defaults
            validator = PathValidator()

            # Current directory files should be allowed
            test_file = tmp_path / "test.txt"
            test_file.write_text("test")

            validated = validator.validate_path(str(test_file))
            assert validated.exists()
        finally:
            os.chdir(original_cwd)


class TestGlobalValidator:
    """Test global validator functions."""

    def test_init_and_get_global_validator(self, tmp_path):
        """Test global validator initialization and retrieval."""
        allowed_dir = tmp_path / "allowed"
        allowed_dir.mkdir()

        # Initialize global validator
        validator = init_path_validator(allowed_dirs=[str(allowed_dir)])
        assert validator is not None

        # Retrieve global validator
        retrieved = get_path_validator()
        assert retrieved is validator

    def test_global_validate_path(self, tmp_path):
        """Test global validate_path function."""
        allowed_dir = tmp_path / "allowed"
        allowed_dir.mkdir()
        test_file = allowed_dir / "test.txt"
        test_file.write_text("test")

        # Initialize global validator
        init_path_validator(allowed_dirs=[str(allowed_dir)])

        # Use global function
        validated = validate_path(str(test_file), require_exists=True)
        assert validated.exists()

    def test_global_validate_paths(self, tmp_path):
        """Test global validate_paths function."""
        allowed_dir = tmp_path / "allowed"
        allowed_dir.mkdir()

        file1 = allowed_dir / "file1.txt"
        file2 = allowed_dir / "file2.txt"
        file1.write_text("test1")
        file2.write_text("test2")

        # Initialize global validator
        init_path_validator(allowed_dirs=[str(allowed_dir)])

        # Use global function
        validated = validate_paths([str(file1), str(file2)], require_exists=True)
        assert len(validated) == 2


class TestSecurityScenarios:
    """Test real-world security scenarios."""

    def test_docker_workspace_access(self, tmp_path):
        """Test typical Docker workspace scenario."""
        # Simulate Docker /workspace mount
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        (workspace / "src").mkdir()
        (workspace / "tests").mkdir()

        source_file = workspace / "src" / "main.py"
        source_file.write_text("print('hello')")

        validator = PathValidator(allowed_dirs=[str(workspace)])

        # Workspace files should be accessible
        validated = validator.validate_path(str(source_file))
        assert validated.exists()

        # System files should be blocked
        with pytest.raises(SecurityError):
            validator.validate_path("/etc/passwd")

    def test_user_documents_access(self, tmp_path):
        """Test typical user Documents scenario."""
        docs_dir = tmp_path / "Documents"
        docs_dir.mkdir()
        (docs_dir / "Projects").mkdir()

        project_file = docs_dir / "Projects" / "my_project" / "code.py"
        project_file.parent.mkdir(parents=True)
        project_file.write_text("# Python code")

        validator = PathValidator(allowed_dirs=[str(docs_dir)])

        # Project files should be accessible
        validated = validator.validate_path(str(project_file))
        assert validated.parent.name == "my_project"

        # Files outside Documents should be blocked
        external_file = tmp_path / "external" / "file.txt"
        external_file.parent.mkdir()
        external_file.write_text("external")

        with pytest.raises(SecurityError):
            validator.validate_path(str(external_file))

    def test_path_traversal_attack_scenarios(self, tmp_path):
        """Test various path traversal attack vectors."""
        allowed_dir = tmp_path / "allowed"
        allowed_dir.mkdir()

        validator = PathValidator(allowed_dirs=[str(allowed_dir)])

        # Common attack patterns
        attack_vectors = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",  # Windows-style
            "....//....//....//etc/passwd",  # Double dot
            "./../.../../etc/passwd",
            "subdir/../../forbidden/file.txt",
        ]

        for attack in attack_vectors:
            with pytest.raises(SecurityError):
                validator.validate_path(attack)
