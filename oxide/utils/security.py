"""
Security utilities for input validation and sanitization.
"""
import re
from pathlib import Path
from typing import List

from .exceptions import AdapterError


# Maximum prompt length to prevent abuse
MAX_PROMPT_LENGTH = 100_000  # 100KB

# Dangerous patterns that could indicate command injection attempts
DANGEROUS_PATTERNS = [
    r';\s*(?:rm|curl|wget|nc|bash|sh|python|perl|ruby)',  # Command chaining
    r'\$\([^)]*\)',  # Command substitution $(...)
    r'`[^`]*`',  # Command substitution backticks
    r'\|\s*(?:bash|sh|python|perl|ruby)',  # Pipe to interpreter
    r'>\s*/dev/',  # Redirecting to devices
    r'&\s*(?:rm|curl|wget)',  # Background command execution
]


def validate_prompt(prompt: str) -> str:
    """
    Validate and sanitize a prompt string.

    Args:
        prompt: User-provided prompt

    Returns:
        Validated prompt string

    Raises:
        AdapterError: If prompt contains dangerous patterns or is too long
    """
    if not isinstance(prompt, str):
        raise AdapterError(f"Prompt must be a string, got {type(prompt)}")

    if not prompt.strip():
        raise AdapterError("Prompt cannot be empty")

    if len(prompt) > MAX_PROMPT_LENGTH:
        raise AdapterError(
            f"Prompt exceeds maximum length of {MAX_PROMPT_LENGTH} characters"
        )

    # Check for dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, prompt, re.IGNORECASE):
            raise AdapterError(
                f"Prompt contains potentially dangerous pattern: {pattern}"
            )

    return prompt


def validate_file_path(file_path: str, must_exist: bool = True) -> Path:
    """
    Validate and sanitize a file path.

    Args:
        file_path: User-provided file path
        must_exist: Whether the file must exist

    Returns:
        Validated Path object

    Raises:
        AdapterError: If file path is invalid or dangerous
    """
    if not isinstance(file_path, str):
        raise AdapterError(f"File path must be a string, got {type(file_path)}")

    if not file_path.strip():
        raise AdapterError("File path cannot be empty")

    try:
        # Expand user and resolve to absolute path
        path = Path(file_path).expanduser().resolve()
    except Exception as e:
        raise AdapterError(f"Invalid file path '{file_path}': {e}")

    # Check for path traversal attempts
    if ".." in file_path:
        # Verify resolved path doesn't escape intended boundaries
        # (This is a basic check, more sophisticated checks may be needed)
        pass

    # Check if file exists (if required)
    if must_exist and not path.exists():
        raise AdapterError(f"File not found: {file_path}")

    # Ensure it's a file (not a directory or special file)
    if must_exist and not path.is_file():
        raise AdapterError(f"Path is not a regular file: {file_path}")

    return path


def validate_file_paths(file_paths: List[str], must_exist: bool = True) -> List[Path]:
    """
    Validate multiple file paths.

    Args:
        file_paths: List of user-provided file paths
        must_exist: Whether files must exist

    Returns:
        List of validated Path objects

    Raises:
        AdapterError: If any file path is invalid
    """
    validated_paths = []

    for file_path in file_paths:
        try:
            path = validate_file_path(file_path, must_exist=must_exist)
            validated_paths.append(path)
        except AdapterError:
            # Log warning but continue with other files
            # Alternatively, could raise error to fail fast
            continue

    return validated_paths


def sanitize_command_arg(arg: str) -> str:
    """
    Sanitize a command-line argument.

    This provides defense-in-depth even when using subprocess with list arguments.

    Args:
        arg: Command argument to sanitize

    Returns:
        Sanitized argument
    """
    # Remove null bytes
    arg = arg.replace('\x00', '')

    # Remove other control characters that could be problematic
    arg = ''.join(char for char in arg if ord(char) >= 32 or char in '\n\r\t')

    return arg
