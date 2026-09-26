"""
Git repository tools for status and diff inspection.
"""
from typing import Any
from codepilot.safety.policy import SafetyPolicy
from codepilot.tools.base import BaseTool, ToolResult
from codepilot.tools.terminal import RunCommandTool


class GitStatusTool(BaseTool):
    name = "git_status"
    description = "Check git repository status for modified, untracked, or staged files."
    parameters_schema = {
        "type": "object",
        "properties": {},
        "required": []
    }

    def __init__(self, safety: SafetyPolicy):
        self.safety = safety
        self.cmd_tool = RunCommandTool(safety)

    def execute(self, **kwargs: Any) -> ToolResult:
        res = self.cmd_tool.execute(command="git status --short")
        return ToolResult(
            success=res.success,
            output=res.output if res.output.strip() else "(Clean working tree, no modifications)",
            error=res.error,
            metadata={"command": "git status --short"}
        )


class GitDiffTool(BaseTool):
    name = "git_diff"
    description = "Get uncommitted git diff patch across the repository."
    parameters_schema = {
        "type": "object",
        "properties": {},
        "required": []
    }

    def __init__(self, safety: SafetyPolicy):
        self.safety = safety
        self.cmd_tool = RunCommandTool(safety)

    def execute(self, **kwargs: Any) -> ToolResult:
        res = self.cmd_tool.execute(command="git diff")
        diff_text = res.output if res.output.strip() else "(No diff)"
        return ToolResult(
            success=res.success,
            output=diff_text,
            error=res.error,
            metadata={"diff_length": len(diff_text)}
        )
