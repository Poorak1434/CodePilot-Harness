"""
Safety policy enforcement for workspace boundary checks and command filtering.
"""
import os
import re
from pathlib import Path
from typing import Tuple, List, Optional

BLOCKED_COMMAND_PATTERNS = [
    r"\brm\s+-rf\b",
    r"\brm\s+-fr\b",
    r"\bsudo\b",
    r"\bchmod\b",
    r"\bchown\b",
    r"\bmkfs\b",
    r"\bdd\b",
    r"\bshutdown\b",
    r"\breboot\b",
    r":\(\)\{\s*:\|:&\s*\};:",  # fork bomb
    r"\bgit\s+reset\s+--hard\s+HEAD~[5-9][0-9]*\b",
    r"\bcurl\s+.*\|\s*sh\b",
    r"\bwget\s+.*\|\s*sh\b",
]


class SafetyViolationError(PermissionError):
    """Raised when an operation violates harness safety policy."""
    pass


class SafetyPolicy:
    def __init__(self, workspace_root: str, default_timeout_seconds: float = 30.0, max_output_bytes: int = 100_000):
        self.workspace_root = Path(workspace_root).resolve()
        self.default_timeout_seconds = default_timeout_seconds
        self.max_output_bytes = max_output_bytes

        if not self.workspace_root.exists():
            raise ValueError(f"Workspace root does not exist: {self.workspace_root}")

    def validate_path(self, target_path: str, allow_creation: bool = True) -> Path:
        """
        Validates that target_path resides within self.workspace_root.
        Prevents path traversal attacks (e.g. '../../etc/passwd').
        """
        path_obj = Path(target_path)
        if not path_obj.is_absolute():
            path_obj = (self.workspace_root / path_obj)
        
        resolved_path = path_obj.resolve()
        
        # Check workspace boundary
        try:
            resolved_path.relative_to(self.workspace_root)
        except ValueError:
            raise SafetyViolationError(
                f"Path '{target_path}' resolves to '{resolved_path}' outside workspace root '{self.workspace_root}'"
            )

        if not allow_creation and not resolved_path.exists():
            raise FileNotFoundError(f"Path '{resolved_path}' does not exist.")

        return resolved_path

    def validate_command(self, command: str) -> Tuple[bool, Optional[str]]:
        """
        Validates shell command against dangerous patterns.
        Returns (is_valid, reason_if_invalid).
        """
        cmd_stripped = command.strip()
        if not cmd_stripped:
            return False, "Command cannot be empty."

        for pattern in BLOCKED_COMMAND_PATTERNS:
            if re.search(pattern, cmd_stripped, re.IGNORECASE):
                return False, f"Command contains blocked pattern matching '{pattern}'"

        return True, None

    def sanitize_output(self, output: str) -> str:
        """
        Truncates output to max_output_bytes to prevent token/memory exhaustion.
        """
        if len(output) > self.max_output_bytes:
            truncated = output[: self.max_output_bytes]
            return truncated + f"\n... [Output truncated. Total size exceeded {self.max_output_bytes} bytes]"
        return output
