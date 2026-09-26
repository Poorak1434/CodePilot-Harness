"""
Test execution tool with failure output capture.
"""
from typing import Any, Optional
from codepilot.safety.policy import SafetyPolicy
from codepilot.tools.base import BaseTool, ToolResult
from codepilot.tools.terminal import RunCommandTool


class RunTestsTool(BaseTool):
    name = "run_tests"
    description = "Run test suite (e.g. pytest or python unittest) and capture structured test results."
    parameters_schema = {
        "type": "object",
        "properties": {
            "test_command": {"type": "string", "description": "Custom test command (defaults to pytest or python -m unittest discover)."}
        },
        "required": []
    }

    def __init__(self, safety: SafetyPolicy, default_test_command: Optional[str] = None):
        self.safety = safety
        self.default_test_command = default_test_command
        self.cmd_tool = RunCommandTool(safety)

    def execute(self, test_command: Optional[str] = None, **kwargs: Any) -> ToolResult:
        eff_command = test_command or self.default_test_command
        if not eff_command:
            ws = self.safety.workspace_root
            if (ws / "tests").exists() or (ws / "pyproject.toml").exists():
                eff_command = "pytest"
            else:
                eff_command = "python3 -m unittest discover"

        res = self.cmd_tool.execute(command=eff_command, timeout=60.0)

        failed = not res.success
        summary = {
            "test_command": eff_command,
            "passed": not failed,
            "raw_output": res.output
        }

        return ToolResult(
            success=res.success,
            output=res.output,
            error=res.error if failed else None,
            metadata=summary
        )
