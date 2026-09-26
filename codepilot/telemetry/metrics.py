"""
Metrics tracker for token usage, API calls, tool counts, runtime, and retries.
"""
import time
from typing import Dict, Any


class MetricsTracker:
    def __init__(self):
        self.start_time = time.time()
        self.model_calls = 0
        self.tool_calls = 0
        self.retry_count = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.files_inspected = set()
        self.files_modified = set()

    def record_model_call(self, prompt_tok: int = 0, comp_tok: int = 0) -> None:
        self.model_calls += 1
        self.prompt_tokens += prompt_tok
        self.completion_tokens += comp_tok

    def record_tool_call(self, tool_name: str) -> None:
        self.tool_calls += 1

    def record_retry(self) -> None:
        self.retry_count += 1

    def record_file_inspected(self, path: str) -> None:
        self.files_inspected.add(path)

    def record_file_modified(self, path: str) -> None:
        self.files_modified.add(path)

    def summary(self) -> Dict[str, Any]:
        return {
            "runtime_seconds": round(time.time() - self.start_time, 2),
            "model_calls": self.model_calls,
            "tool_calls": self.tool_calls,
            "retry_count": self.retry_count,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.prompt_tokens + self.completion_tokens,
            "files_inspected_count": len(self.files_inspected),
            "files_modified_count": len(self.files_modified),
            "files_modified": list(self.files_modified)
        }
