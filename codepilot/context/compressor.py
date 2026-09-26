"""
Context compressor for summarizing past tool outputs and trimming old history.
"""
from typing import List, Dict, Any


class ContextCompressor:
    def __init__(self, max_turn_bytes: int = 4000):
        self.max_turn_bytes = max_turn_bytes

    def compress_tool_output(self, output: str, max_bytes: int = 1500) -> str:
        """Compresses long tool execution output (e.g. stdout/stderr)."""
        if len(output) <= max_bytes:
            return output

        half = max_bytes // 2
        prefix = output[:half]
        suffix = output[-half:]
        omitted = len(output) - max_bytes
        return f"{prefix}\n... [{omitted} bytes omitted for efficiency] ...\n{suffix}"

    def compress_history(self, history: List[Dict[str, Any]], keep_recent: int = 6) -> List[Dict[str, Any]]:
        """
        Compresses conversation history. Keeps system prompt + initial task + recent tool iterations.
        Older intermediate steps are summarized.
        """
        if len(history) <= keep_recent + 1:
            return history

        preserved_start = history[:2]  # Initial task / prompt
        recent_tail = history[-keep_recent:]
        middle_steps = history[2:-keep_recent]

        summarized_text = f"[Harness Context Compressor: Summarized {len(middle_steps)} earlier exploration/action steps to save tokens.]"
        summary_node = {
            "role": "system",
            "content": summarized_text
        }

        return preserved_start + [summary_node] + recent_tail
