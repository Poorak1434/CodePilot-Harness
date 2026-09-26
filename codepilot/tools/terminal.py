"""
Terminal tool for executing subprocess commands safely.
"""
import subprocess
import os
from typing import Any, Optional
from codepilot.safety.policy import SafetyPolicy
from codepilot.tools.base import BaseTool, ToolResult


class RunCommandTool(BaseTool):
    name = "run_command"
    description = "Run a shell command inside the workspace directory safely."
    parameters_schema = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Shell command line to execute."},
            "timeout": {"type": "number", "description": "Execution timeout in seconds (default 30)."}
        },
        "required": ["command"]
    }

    def __init__(self, safety: SafetyPolicy):
        self.safety = safety

    def execute(self, command: str, timeout: Optional[float] = None, **kwargs: Any) -> ToolResult:
        is_valid, reason = self.safety.validate_command(command)
        if not is_valid:
            return ToolResult(
                success=False,
                output="",
                error=f"Safety Policy Violation: {reason}",
                metadata={"command": command}
            )

        eff_timeout = timeout if (timeout and timeout > 0) else self.safety.default_timeout_seconds

        try:
            res = subprocess.run(
                command,
                shell=True,
                cwd=str(self.safety.workspace_root),
                capture_output=True,
                text=True,
                timeout=eff_timeout
            )

            stdout = res.stdout or ""
            stderr = res.stderr or ""
            combined_output = f"STDOUT:\n{stdout}\nSTDERR:\n{stderr}".strip()
            combined_output = self.safety.sanitize_output(combined_output)

            success = (res.returncode == 0)
            return ToolResult(
                success=success,
                output=combined_output,
                error=None if success else f"Command exited with return code {res.returncode}",
                metadata={
                    "command": command,
                    "returncode": res.returncode,
                    "stdout_bytes": len(stdout),
                    "stderr_bytes": len(stderr)
                }
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                output=f"Command timed out after {eff_timeout} seconds.",
                error=f"TimeoutExpired ({eff_timeout}s)",
                metadata={"command": command, "timeout": eff_timeout}
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e), metadata={"command": command})
