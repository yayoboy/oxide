"""
Path validation and file system sandboxing for security.

Prevents access to sensitive system files and path traversal attacks.
"""
from pathlib import Path
from typing import List, Optional
import os
import logging

from .logging import logger


class SecurityError(Exception):
    """Raised when a path fails security validation."""
    pass


class PathValidator:
    """
    Validates file paths against security rules.

    Features:
    - Whitelist-based directory access control
    - Path traversal attack prevention
    - Symlink resolution and validation
    - Audit logging for blocked attempts
    """

    def __init__(self, allowed_dirs: Optional[List[str]] = None):
        """
        Initialize path validator.

        Args:
            allowed_dirs: List of allowed directory paths. If None, uses defaults.
        """
        if allowed_dirs is None:
            # Default safe directories
            allowed_dirs = [
                str(Path.home() / "Documents"),
                str(Path.home() / "Projects"),
                str(Path.home() / "Downloads"),
                str(Path.cwd()),  # Current working directory
                "/tmp",  # Temporary files
                "/workspace",  # Docker mount point
            ]

        # Resolve and normalize all allowed directories
        self.allowed_dirs = [str(Path(d).resolve()) for d in allowed_dirs if Path(d).exists()]

        if not self.allowed_dirs:
            logger.warning("No valid allowed directories found. Validation will deny all paths.")
        else:
            logger.info(f"Path validator initialized with {len(self.allowed_dirs)} allowed directories")

    def validate_path(self, file_path: str, require_exists: bool = False) -> Path:
        """
        Validate a file path against security rules.

        Args:
            file_path: Path to validate
            require_exists: If True, path must exist on filesystem

        Returns:
            Resolved Path object if validation passes

        Raises:
            SecurityError: If path fails validation
            FileNotFoundError: If require_exists=True and path doesn't exist
        """
        if not file_path:
            raise SecurityError("Empty file path provided")

        # Check for obvious path traversal patterns
        if ".." in file_path or file_path.startswith("~"):
            logger.warning(f"Path traversal attempt blocked: {file_path}")
            raise SecurityError(f"Path traversal detected in: {file_path}")

        try:
            # Resolve path (follows symlinks, makes absolute)
            resolved_path = Path(file_path).resolve()
        except (OSError, RuntimeError) as e:
            logger.warning(f"Failed to resolve path '{file_path}': {e}")
            raise SecurityError(f"Invalid path: {file_path}")

        # Check if path is within allowed directories
        path_str = str(resolved_path)
        is_allowed = any(path_str.startswith(allowed_dir) for allowed_dir in self.allowed_dirs)

        if not is_allowed:
            logger.warning(
                f"Access denied to path outside allowed directories: {path_str}\n"
                f"Allowed directories: {self.allowed_dirs}"
            )
            raise SecurityError(
                f"Path '{file_path}' is outside allowed directories. "
                f"Resolved to: {path_str}"
            )

        # Check for sensitive system files (additional security layer)
        sensitive_patterns = [
            "/etc/passwd",
            "/etc/shadow",
            "/etc/sudoers",
            "/.ssh/",
            "/root/",
            "/.aws/",
            "/.config/secrets",
        ]

        for pattern in sensitive_patterns:
            if pattern in path_str:
                logger.error(f"SECURITY ALERT: Attempt to access sensitive file blocked: {path_str}")
                raise SecurityError(f"Access to sensitive system file denied: {pattern}")

        # Check if path exists (if required)
        if require_exists and not resolved_path.exists():
            raise FileNotFoundError(f"Path does not exist: {resolved_path}")

        logger.debug(f"Path validation passed: {file_path} -> {resolved_path}")
        return resolved_path

    def validate_paths(self, file_paths: List[str], require_exists: bool = False) -> List[Path]:
        """
        Validate multiple file paths.

        Args:
            file_paths: List of paths to validate
            require_exists: If True, all paths must exist

        Returns:
            List of resolved Path objects

        Raises:
            SecurityError: If any path fails validation
        """
        validated_paths = []

        for file_path in file_paths:
            validated_path = self.validate_path(file_path, require_exists=require_exists)
            validated_paths.append(validated_path)

        return validated_paths

    def is_path_allowed(self, file_path: str) -> bool:
        """
        Check if a path would pass validation (non-raising).

        Args:
            file_path: Path to check

        Returns:
            True if path is allowed, False otherwise
        """
        try:
            self.validate_path(file_path, require_exists=False)
            return True
        except (SecurityError, FileNotFoundError):
            return False

    def add_allowed_directory(self, directory: str) -> None:
        """
        Add a directory to the allowed list.

        Args:
            directory: Directory path to allow
        """
        dir_path = Path(directory)

        if not dir_path.exists():
            logger.warning(f"Cannot add non-existent directory to whitelist: {directory}")
            return

        resolved_dir = str(dir_path.resolve())

        if resolved_dir not in self.allowed_dirs:
            self.allowed_dirs.append(resolved_dir)
            logger.info(f"Added directory to whitelist: {resolved_dir}")

    def get_allowed_directories(self) -> List[str]:
        """
        Get list of currently allowed directories.

        Returns:
            List of allowed directory paths
        """
        return self.allowed_dirs.copy()


# Global validator instance (can be reconfigured)
_global_validator: Optional[PathValidator] = None


def init_path_validator(allowed_dirs: Optional[List[str]] = None) -> PathValidator:
    """
    Initialize the global path validator.

    Args:
        allowed_dirs: List of allowed directory paths

    Returns:
        Configured PathValidator instance
    """
    global _global_validator
    _global_validator = PathValidator(allowed_dirs=allowed_dirs)
    return _global_validator


def get_path_validator() -> PathValidator:
    """
    Get the global path validator instance.

    Returns:
        PathValidator instance
    """
    global _global_validator

    if _global_validator is None:
        _global_validator = PathValidator()

    return _global_validator


def validate_path(file_path: str, require_exists: bool = False) -> Path:
    """
    Validate a file path using the global validator.

    Args:
        file_path: Path to validate
        require_exists: If True, path must exist

    Returns:
        Resolved Path object

    Raises:
        SecurityError: If path fails validation
    """
    validator = get_path_validator()
    return validator.validate_path(file_path, require_exists=require_exists)


def validate_paths(file_paths: List[str], require_exists: bool = False) -> List[Path]:
    """
    Validate multiple file paths using the global validator.

    Args:
        file_paths: List of paths to validate
        require_exists: If True, all paths must exist

    Returns:
        List of resolved Path objects

    Raises:
        SecurityError: If any path fails validation
    """
    validator = get_path_validator()
    return validator.validate_paths(file_paths, require_exists=require_exists)
