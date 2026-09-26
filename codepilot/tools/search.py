"""
Code search tool for pattern and keyword discovery across workspace.
"""
import os
import re
from pathlib import Path
from typing import Any, List
from codepilot.safety.policy import SafetyPolicy
from codepilot.tools.base import BaseTool, ToolResult


class SearchCodeTool(BaseTool):
    name = "search_code"
    description = "Search repository code files for a string or regex query."
    parameters_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "String or regex pattern to search for."},
            "path": {"type": "string", "description": "Subdirectory path to restrict search (defaults to '.')."},
            "is_regex": {"type": "boolean", "description": "If true, treat query as regex."}
        },
        "required": ["query"]
    }

    def __init__(self, safety: SafetyPolicy):
        self.safety = safety

    def execute(self, query: str, path: str = ".", is_regex: bool = False, **kwargs: Any) -> ToolResult:
        try:
            target_dir = self.safety.validate_path(path, allow_creation=False)
            if not target_dir.is_dir():
                target_dir = target_dir.parent

            if is_regex:
                pattern = re.compile(query)
            else:
                pattern = re.compile(re.escape(query))

            matches: List[str] = []

            for root, dirs, files in os.walk(target_dir):
                dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__" and d != "venv" and d != "node_modules"]
                for f in files:
                    if f.endswith((".py", ".json", ".md", ".txt", ".yml", ".yaml", ".sh", ".js", ".ts", ".c", ".cpp", ".h")):
                        file_path = Path(root, f)
                        try:
                            lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
                            for idx, line in enumerate(lines, 1):
                                if pattern.search(line):
                                    rel_file = file_path.relative_to(self.safety.workspace_root)
                                    matches.append(f"{rel_file}:{idx}: {line.strip()}")
                        except Exception:
                            continue

            out_text = "\n".join(matches[:200]) if matches else f"No matches found for query '{query}'."
            if len(matches) > 200:
                out_text += f"\n... [{len(matches) - 200} more matches omitted]"

            out_text = self.safety.sanitize_output(out_text)
            return ToolResult(
                success=True,
                output=out_text,
                metadata={"query": query, "matches_count": len(matches)}
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
