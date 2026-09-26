"""
AgentOrchestrator manages component routing, tool execution, and telemetry logging.
"""
from typing import Dict, Any, Tuple, Optional
from codepilot.safety.policy import SafetyPolicy
from codepilot.tools.router import ToolRouter
from codepilot.tools.base import ToolResult
from codepilot.context.manager import ContextManager
from codepilot.llm.adapter import LLMAdapter
from codepilot.llm.prompts import SYSTEM_PROMPT
from codepilot.recovery import FailureDetector, FailureClassifier, RecoveryStrategy
from codepilot.verification import VerificationRunner, EvidenceReporter
from codepilot.telemetry import TraceLogger, MetricsTracker


class AgentOrchestrator:
    def __init__(
        self,
        workspace_root: str,
        provider: str = "mock",
        model_name: Optional[str] = None,
        test_command: Optional[str] = None,
        verbose: bool = True
    ):
        self.safety = SafetyPolicy(workspace_root=workspace_root)
        self.tools = ToolRouter(self.safety, default_test_command=test_command)
        self.context = ContextManager(self.safety)
        self.llm = LLMAdapter(provider=provider, model_name=model_name)
        self.verification = VerificationRunner(self.safety)
        self.logger = TraceLogger(verbose=verbose)
        self.metrics = MetricsTracker()

    def execute_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        self.metrics.record_tool_call(tool_name)
        if "path" in arguments:
            self.metrics.record_file_inspected(arguments["path"])
        if tool_name in {"edit_file", "create_file"}:
            if "path" in arguments:
                self.metrics.record_file_modified(arguments["path"])

        result = self.tools.dispatch(tool_name, arguments)
        return result
