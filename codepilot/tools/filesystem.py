"""
Filesystem tools with safety policy validation.
"""
import os
import fnmatch
from pathlib import Path
from typing import Any, Optional, List
from codepilot.safety.policy import SafetyPolicy, SafetyViolationError
from codepilot.tools.base import BaseTool, ToolResult


class ListDirTool(BaseTool):
    name = "list_dir"
    description = "List files and directories within a given directory path."
    parameters_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative or absolute directory path (defaults to root '.' )"}
        },
        "required": []
    }

    def __init__(self, safety: SafetyPolicy):
        self.safety = safety

    def execute(self, path: str = ".", **kwargs: Any) -> ToolResult:
        try:
            target_path = self.safety.validate_path(path, allow_creation=False)
            if not target_path.is_dir():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Path '{path}' is not a directory.",
                    metadata={"path": str(target_path)}
                )

            items = []
            for entry in sorted(os.listdir(target_path)):
                if entry.startswith(".git") or entry.startswith("__pycache__") or entry == ".venv":
                    continue
                entry_path = target_path / entry
                kind = "dir" if entry_path.is_dir() else "file"
                items.append(f"{entry} ({kind})")

            output_text = "\n".join(items) if items else "(empty directory)"
            return ToolResult(
                success=True,
                output=output_text,
                metadata={"item_count": len(items), "path": str(target_path)}
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class ReadFileTool(BaseTool):
    name = "read_file"
    description = "Read lines from a text file, optionally specifying start_line and end_line (1-indexed)."
    parameters_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the file to read."},
            "start_line": {"type": "integer", "description": "Start line (1-indexed)."},
            "end_line": {"type": "integer", "description": "End line (1-indexed, inclusive)."}
        },
        "required": ["path"]
    }

    def __init__(self, safety: SafetyPolicy):
        self.safety = safety

    def execute(self, path: str, start_line: Optional[int] = None, end_line: Optional[int] = None, **kwargs: Any) -> ToolResult:
        try:
            target_path = self.safety.validate_path(path, allow_creation=False)
            if not target_path.is_file():
                return ToolResult(success=False, output="", error=f"File not found: '{path}'")

            lines = target_path.read_text(encoding="utf-8", errors="replace").splitlines()

            total_lines = len(lines)
            s_idx = (start_line - 1) if (start_line and start_line > 0) else 0
            e_idx = end_line if (end_line and end_line > 0) else total_lines

            s_idx = max(0, min(s_idx, total_lines))
            e_idx = max(s_idx, min(e_idx, total_lines))

            selected_lines = lines[s_idx:e_idx]
            formatted_lines = [
                f"{i + s_idx + 1:4d} | {line}" for i, line in enumerate(selected_lines)
            ]

            out = "\n".join(formatted_lines)
            out = self.safety.sanitize_output(out)
            return ToolResult(
                success=True,
                output=out,
                metadata={"total_lines": total_lines, "returned_lines": len(selected_lines), "path": str(target_path)}
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class CreateFileTool(BaseTool):
    name = "create_file"
    description = "Create a new file or overwrite an existing file with given content."
    parameters_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the file to create."},
            "content": {"type": "string", "description": "File text content."}
        },
        "required": ["path", "content"]
    }

    def __init__(self, safety: SafetyPolicy):
        self.safety = safety

    def execute(self, path: str, content: str = "", **kwargs: Any) -> ToolResult:
        try:
            target_path = self.safety.validate_path(path, allow_creation=True)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(content, encoding="utf-8")
            return ToolResult(
                success=True,
                output=f"Successfully created file '{path}' ({len(content)} bytes).",
                metadata={"path": str(target_path), "bytes": len(content)}
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class EditFileTool(BaseTool):
    name = "edit_file"
    description = "Replace old_str with new_str in a file."
    parameters_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the file to edit."},
            "old_str": {"type": "string", "description": "Target string snippet to replace."},
            "new_str": {"type": "string", "description": "Replacement string snippet."}
        },
        "required": ["path", "old_str", "new_str"]
    }

    def __init__(self, safety: SafetyPolicy):
        self.safety = safety

    def execute(self, path: str, old_str: str, new_str: str, **kwargs: Any) -> ToolResult:
        try:
            target_path = self.safety.validate_path(path, allow_creation=False)
            if not target_path.is_file():
                return ToolResult(success=False, output="", error=f"File not found: '{path}'")

            content = target_path.read_text(encoding="utf-8", errors="replace")
            count = content.count(old_str)

            if count == 0:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Target text old_str not found in file '{path}'."
                )

            new_content = content.replace(old_str, new_str)
            target_path.write_text(new_content, encoding="utf-8")

            return ToolResult(
                success=True,
                output=f"Replaced {count} occurrence(s) of target text in '{path}'.",
                metadata={"path": str(target_path), "replacements": count}
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class FindFileTool(BaseTool):
    name = "find_file"
    description = "Find files matching a glob pattern (e.g. '*.py' or '*test*')."
    parameters_schema = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Glob pattern to match file names."},
            "directory": {"type": "string", "description": "Directory to search from (defaults to '.')."}
        },
        "required": ["pattern"]
    }

    def __init__(self, safety: SafetyPolicy):
        self.safety = safety

    def execute(self, pattern: str, directory: str = ".", **kwargs: Any) -> ToolResult:
        try:
            target_dir = self.safety.validate_path(directory, allow_creation=False)
            matched_files: List[str] = []

            for root, dirs, files in os.walk(target_dir):
                # Filter hidden / venv directories
                dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__" and d != "venv"]
                for f in files:
                    if fnmatch.fnmatch(f, pattern):
                        rel_path = Path(root, f).relative_to(self.safety.workspace_root)
                        matched_files.append(str(rel_path))

            matched_files.sort()
            out = "\n".join(matched_files) if matched_files else "No matching files found."
            return ToolResult(
                success=True,
                output=out,
                metadata={"count": len(matched_files), "pattern": pattern}
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
