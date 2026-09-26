"""
Repository retriever for discovering relevant files, code snippets, and tests based on task description.
"""
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Set
from codepilot.safety.policy import SafetyPolicy


class RepositoryRetriever:
    def __init__(self, safety: SafetyPolicy):
        self.safety = safety

    def extract_keywords(self, task_description: str) -> List[str]:
        """Extract meaningful identifiers and keywords from issue text."""
        # Find snake_case, camelCase, file names, or function names
        tokens = re.findall(r"[a-zA-Z0-9_\-\.]+", task_description)
        stopwords = {
            "the", "a", "an", "in", "on", "at", "to", "for", "of", "with", "and", "or",
            "is", "are", "was", "were", "fix", "bug", "issue", "error", "failed", "test",
            "this", "that", "it", "not", "should", "does", "code", "file", "repo"
        }
        keywords = [t for t in tokens if t.lower() not in stopwords and len(t) > 2]
        return list(dict.fromkeys(keywords))  # unique preserving order

    def retrieve_relevant_files(self, task_description: str, max_files: int = 5) -> List[Dict[str, Any]]:
        """
        Scans workspace files and ranks them by relevance to task_description keywords.
        Returns list of dicts with file path, relevance score, and preview snippet.
        """
        keywords = self.extract_keywords(task_description)
        scored_files = []

        workspace_root = self.safety.workspace_root
        for root, dirs, files in os.walk(workspace_root):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in {"__pycache__", "venv", "node_modules", "dist", "build"}]
            for file_name in files:
                if not file_name.endswith((".py", ".js", ".ts", ".c", ".h", ".md", ".json")):
                    continue

                full_path = Path(root, file_name)
                rel_path = str(full_path.relative_to(workspace_root))

                score = 0
                # File name match
                for kw in keywords:
                    if kw.lower() in file_name.lower():
                        score += 5
                    if "test" in file_name.lower() and "test" in task_description.lower():
                        score += 2

                try:
                    content = full_path.read_text(encoding="utf-8", errors="ignore")
                    for kw in keywords:
                        occurrences = len(re.findall(re.escape(kw), content, re.IGNORECASE))
                        score += min(occurrences, 10)  # cap match count per keyword
                except Exception:
                    continue

                if score > 0:
                    scored_files.append({
                        "path": rel_path,
                        "score": score,
                        "lines_count": len(content.splitlines()),
                        "preview": "\n".join(content.splitlines()[:20])
                    })

        scored_files.sort(key=lambda x: x["score"], reverse=True)
        return scored_files[:max_files]
