"""
ToolRouter manages tool registration, input validation, execution, and telemetry logging.
"""
from typing import Dict, Any, List, Optional
from codepilot.safety.policy import SafetyPolicy
from codepilot.tools.base import BaseTool, ToolResult
from codepilot.tools.filesystem import ListDirTool, ReadFileTool, CreateFileTool, EditFileTool, FindFileTool
from codepilot.tools.search import SearchCodeTool
from codepilot.tools.terminal import RunCommandTool
from codepilot.tools.tests import RunTestsTool
from codepilot.tools.git import GitStatusTool, GitDiffTool


class ToolRouter:
    def __init__(self, safety: SafetyPolicy, default_test_command: Optional[str] = None):
        self.safety = safety
        self.default_test_command = default_test_command
        self._tools: Dict[str, BaseTool] = {}
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        default_tools = [
            ListDirTool(self.safety),
            ReadFileTool(self.safety),
            CreateFileTool(self.safety),
            EditFileTool(self.safety),
            FindFileTool(self.safety),
            SearchCodeTool(self.safety),
            RunCommandTool(self.safety),
            RunTestsTool(self.safety, default_test_command=self.default_test_command),
            GitStatusTool(self.safety),
            GitDiffTool(self.safety),
        ]
        for t in default_tools:
            self.register_tool(t)

    def register_tool(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """Returns JSON schema definitions of all registered tools for LLM tool calling."""
        declarations = []
        for name, tool in self._tools.items():
            declarations.append({
                "name": name,
                "description": tool.description,
                "parameters": tool.parameters_schema
            })
        return declarations

    def dispatch(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        tool = self.get_tool(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                output="",
                error=f"Tool '{tool_name}' is not registered."
            )

        try:
            return tool.execute(**arguments)
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Unhandled exception during tool execution '{tool_name}': {str(e)}"
            )
