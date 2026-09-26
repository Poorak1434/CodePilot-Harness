"""
ContextManager maintains task state, token budget, active repository context, and history formatting.
"""
from typing import List, Dict, Any, Optional
from codepilot.safety.policy import SafetyPolicy
from codepilot.context.retriever import RepositoryRetriever
from codepilot.context.compressor import ContextCompressor


class ContextManager:
    def __init__(
        self,
        safety: SafetyPolicy,
        max_context_bytes: int = 40_000,
        keep_recent_history: int = 6
    ):
        self.safety = safety
        self.max_context_bytes = max_context_bytes
        self.retriever = RepositoryRetriever(safety)
        self.compressor = ContextCompressor(max_turn_bytes=4000)
        self.keep_recent_history = keep_recent_history

        self.task_description: str = ""
        self.retrieved_files: List[Dict[str, Any]] = []
        self.history: List[Dict[str, Any]] = []
        self.current_plan: List[str] = []
        self.failure_history: List[Dict[str, Any]] = []

    def initialize_task(self, task_description: str) -> None:
        self.task_description = task_description
        self.history.clear()
        self.failure_history.clear()
        self.current_plan.clear()

        # Perform initial repository exploration
        self.retrieved_files = self.retriever.retrieve_relevant_files(task_description)

    def add_history(self, role: str, content: str, tool_calls: Optional[List[Dict[str, Any]]] = None) -> None:
        compressed_content = self.compressor.compress_tool_output(content)
        entry: Dict[str, Any] = {"role": role, "content": compressed_content}
        if tool_calls:
            entry["tool_calls"] = tool_calls
        self.history.append(entry)

        # Apply history compression if context limit exceeded
        self.history = self.compressor.compress_history(self.history, keep_recent=self.keep_recent_history)

    def record_failure(self, failure_info: Dict[str, Any]) -> None:
        self.failure_history.append(failure_info)

    def get_formatted_context(self) -> str:
        """Returns structured prompt context package for LLM orchestration."""
        context_parts = []
        context_parts.append(f"### ISSUE / TASK DESCRIPTION:\n{self.task_description}\n")

        if self.current_plan:
            context_parts.append("### CURRENT PLAN:")
            for idx, step in enumerate(self.current_plan, 1):
                context_parts.append(f"{idx}. {step}")
            context_parts.append("")

        if self.retrieved_files:
            context_parts.append("### RELEVANT REPOSITORY FILES IDENTIFIED BY HARNESS:")
            for rf in self.retrieved_files:
                context_parts.append(f"- File: `{rf['path']}` (Relevance Score: {rf['score']})")
            context_parts.append("")

        if self.failure_history:
            context_parts.append("### PRIOR FAILURE / ERROR EVIDENCE:")
            for idx, fail in enumerate(self.failure_history[-3:], 1):  # last 3 failures
                context_parts.append(f"Attempt #{fail.get('attempt', idx)} Failed:")
                context_parts.append(f"- Failure Type: {fail.get('type', 'Unknown')}")
                context_parts.append(f"- Execution Output / Stderr:\n{fail.get('output', '')}\n")

        full_context = "\n".join(context_parts)
        if len(full_context) > self.max_context_bytes:
            full_context = full_context[: self.max_context_bytes] + "\n... [Context truncated to fit budget]"
        return full_context
