"""
Base data models and abstractions for CodePilot tools.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ToolResult:
    success: bool
    output: str
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "metadata": self.metadata,
        }


class BaseTool:
    name: str = ""
    description: str = ""
    parameters_schema: Dict[str, Any] = {}

    def execute(self, **kwargs: Any) -> ToolResult:
        raise NotImplementedError("Tool execution must be implemented by subclasses.")

