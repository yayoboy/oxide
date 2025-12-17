"""
Base CLI adapter for command-line LLM tools (Gemini, Qwen).
"""
import asyncio
import shlex
from pathlib import Path
from typing import AsyncIterator, List, Optional, Dict, Any

from .base import BaseAdapter
from ..utils.exceptions import CLIAdapterError, ServiceUnavailableError, TimeoutError, AdapterError
from ..utils.security import validate_prompt, validate_file_paths, sanitize_command_arg


class CLIAdapter(BaseAdapter):
    """
    Base adapter for CLI-based LLM services.

    Handles subprocess management, streaming output, and error handling for
    command-line tools like Gemini and Qwen.
    """

    def __init__(self, service_name: str, config: Dict[str, Any]):
        super().__init__(service_name, config)
        self.executable = config.get("executable")
        if not self.executable:
            raise CLIAdapterError(
                f"No executable specified for CLI service '{service_name}'"
            )

    async def execute(
        self,
        prompt: str,
        files: Optional[List[str]] = None,
        timeout: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Execute CLI command and stream output.

        Args:
            prompt: Task prompt
            files: Optional list of files to include with @ syntax
            timeout: Optional timeout in seconds
            **kwargs: Additional arguments

        Yields:
            Response chunks as they become available

        Raises:
            CLIAdapterError: If command execution fails
            TimeoutError: If execution times out
        """
        # Build command
        cmd = await self._build_command(prompt, files)

        self.logger.debug(f"Executing command: {' '.join(cmd[:3])}... (truncated)")

        try:
            # Create subprocess
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Stream output with timeout
            try:
                async for chunk in self._stream_output(process, timeout):
                    yield chunk

            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise TimeoutError(self.service_name, timeout or 0)

            # Wait for process to complete
            await process.wait()

            # Check exit code
            if process.returncode != 0:
                stderr = await process.stderr.read() if process.stderr else b""
                error_msg = stderr.decode().strip()
                raise CLIAdapterError(
                    f"Command failed with exit code {process.returncode}: {error_msg}"
                )

        except FileNotFoundError:
            raise ServiceUnavailableError(
                self.service_name,
                f"Executable '{self.executable}' not found in PATH"
            )
        except CLIAdapterError:
            raise
        except (asyncio.TimeoutError, OSError, PermissionError, ProcessLookupError) as e:
            # Expected process/system errors
            raise CLIAdapterError(f"Process execution error: {e}") from e
        except Exception as e:
            # Unexpected error
            raise CLIAdapterError(f"Unexpected error during execution: {e}") from e

    async def _build_command(
        self,
        prompt: str,
        files: Optional[List[str]] = None
    ) -> List[str]:
        """
        Build command-line arguments with security validation.

        Args:
            prompt: Task prompt
            files: Optional file paths

        Returns:
            List of command arguments

        Raises:
            AdapterError: If inputs contain dangerous patterns
        """
        # Validate prompt for security issues
        try:
            validated_prompt = validate_prompt(prompt)
        except AdapterError as e:
            self.logger.error(f"Prompt validation failed: {e}")
            raise

        cmd = [self.executable, "-p"]

        # Build prompt with file inclusions
        full_prompt = ""

        # Validate and add file references with @ syntax
        if files:
            try:
                # Validate all file paths for security
                validated_paths = validate_file_paths(files, must_exist=True)

                for path in validated_paths:
                    # Sanitize path string before adding to command
                    sanitized_path = sanitize_command_arg(str(path))
                    full_prompt += f"@{sanitized_path} "

            except AdapterError as e:
                self.logger.warning(f"File validation warning: {e}")
                # Continue without files rather than failing completely

        # Add main prompt (sanitize as defense-in-depth)
        sanitized_prompt = sanitize_command_arg(validated_prompt)
        full_prompt += sanitized_prompt

        cmd.append(full_prompt)

        return cmd

    async def _stream_output(
        self,
        process: asyncio.subprocess.Process,
        timeout: Optional[int] = None
    ) -> AsyncIterator[str]:
        """
        Stream output from subprocess.

        Args:
            process: Running subprocess
            timeout: Optional timeout in seconds

        Yields:
            Output chunks
        """
        if not process.stdout:
            return

        buffer = ""
        while True:
            try:
                # Read with timeout
                line_bytes = await asyncio.wait_for(
                    process.stdout.readline(),
                    timeout=timeout
                )

                if not line_bytes:
                    # EOF reached
                    if buffer:
                        yield buffer
                    break

                line = line_bytes.decode("utf-8", errors="replace")
                buffer += line

                # Yield complete lines
                if "\n" in buffer:
                    lines = buffer.split("\n")
                    for complete_line in lines[:-1]:
                        if complete_line.strip():
                            yield complete_line + "\n"
                    buffer = lines[-1]

            except asyncio.TimeoutError:
                raise

    async def health_check(self) -> bool:
        """
        Check if CLI tool is available.

        Returns:
            True if executable exists and responds
        """
        try:
            # Try to run with --version or --help
            process = await asyncio.create_subprocess_exec(
                self.executable,
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            await asyncio.wait_for(process.wait(), timeout=5)
            return process.returncode == 0

        except (FileNotFoundError, asyncio.TimeoutError):
            return False
        except (OSError, PermissionError, ProcessLookupError) as e:
            # Expected system/process errors
            self.logger.debug(f"Health check failed (expected): {e}")
            return False
        except Exception as e:
            # Unexpected error
            self.logger.warning(f"Health check failed unexpectedly: {e}")
            return False
