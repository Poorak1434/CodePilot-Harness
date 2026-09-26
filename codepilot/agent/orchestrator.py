"""
Central LLM-Driven Orchestrator for CodePilot Multi-Agent Architecture.
Coordinates specialized domain agents, manages shared context, schedules concurrent
read-only analysis tasks, serializes repository modifications, and verifies completion.
"""
from typing import Dict, Any, List, Optional
import uuid
import time
import concurrent.futures
from pathlib import Path

from codepilot.safety.policy import SafetyPolicy
from codepilot.tools.router import ToolRouter
from codepilot.tools.base import ToolResult
from codepilot.context.manager import ContextManager
from codepilot.llm.adapter import LLMAdapter
from codepilot.recovery import FailureDetector, FailureClassifier, RecoveryStrategy
from codepilot.verification import VerificationRunner, EvidenceReporter
from codepilot.telemetry import TraceLogger, MetricsTracker

from codepilot.agent.base_agent import BaseSpecializedAgent, AgentTask, AgentResult
from codepilot.agent.security_agent import SecurityAuditorAgent
from codepilot.agent.quality_agent import CodeQualityAgent
from codepilot.agent.architecture_agent import ArchitectureAgent
from codepilot.agent.video_agent import DemoVideoAgent
from codepilot.tools.agent_tools import (
    DelegateToAgentTool,
    RunSecurityAuditTool,
    RunCodeQualityTool,
    GenerateArchitectureDocsTool,
    GenerateDemoVideoTool,
    RunMultiAgentWorkflowTool
)


class AgentOrchestrator:
    def __init__(
        self,
        workspace_root: str,
        provider: str = "mock",
        model_name: Optional[str] = None,
        test_command: Optional[str] = None,
        verbose: bool = True
    ):
        self.workspace_root = workspace_root
        self.safety = SafetyPolicy(workspace_root=workspace_root)
        self.tools = ToolRouter(self.safety, default_test_command=test_command)
        self.context = ContextManager(self.safety)
        self.llm = LLMAdapter(provider=provider, model_name=model_name)
        self.verification = VerificationRunner(self.safety)
        self.logger = TraceLogger(verbose=verbose)
        self.metrics = MetricsTracker()

        # Initialize specialized domain agents
        self._specialized_agents: Dict[str, BaseSpecializedAgent] = {
            "security_auditor": SecurityAuditorAgent(workspace_root, self.llm, self.safety),
            "code_quality": CodeQualityAgent(workspace_root, self.llm, self.safety),
            "architecture_agent": ArchitectureAgent(workspace_root, self.llm, self.safety),
            "demo_video": DemoVideoAgent(workspace_root, self.llm, self.safety)
        }

        # Register agent delegation tools into router
        self._register_agent_tools()

    def _register_agent_tools(self) -> None:
        """Registers specialized agent tools into ToolRouter for LLM invocation."""
        agent_tools = [
            DelegateToAgentTool(self),
            RunSecurityAuditTool(self),
            RunCodeQualityTool(self),
            GenerateArchitectureDocsTool(self),
            GenerateDemoVideoTool(self),
            RunMultiAgentWorkflowTool(self)
        ]
        for t in agent_tools:
            self.tools.register_tool(t)

    def get_agent(self, agent_id: str) -> Optional[BaseSpecializedAgent]:
        return self._specialized_agents.get(agent_id)

    def list_agents(self) -> List[Dict[str, Any]]:
        return [
            {
                "agent_id": aid,
                "role": agent.agent_role,
                "is_read_only": agent.is_read_only,
                "description": agent.description
            }
            for aid, agent in self._specialized_agents.items()
        ]

    def execute_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        self.metrics.record_tool_call(tool_name)
        if "path" in arguments:
            self.metrics.record_file_inspected(arguments["path"])
        if tool_name in {"edit_file", "create_file"}:
            if "path" in arguments:
                self.metrics.record_file_modified(arguments["path"])

        result = self.tools.dispatch(tool_name, arguments)
        return result

    def run_concurrent_agents(self, agent_ids: List[str], objective: str) -> Dict[str, AgentResult]:
        """
        Executes independent read-only agents concurrently in parallel.
        Ensures thread safety and aggregates structured results.
        """
        results: Dict[str, AgentResult] = {}
        tasks = []

        for aid in agent_ids:
            agent = self.get_agent(aid)
            if agent:
                if not agent.is_read_only:
                    self.logger.log(f"Warning: Non-read-only agent '{aid}' cannot run in parallel batch.")
                    continue
                task = AgentTask(
                    task_id=f"concurrent-{uuid.uuid4().hex[:6]}",
                    agent_id=aid,
                    objective=objective,
                    context={"workspace": str(self.safety.workspace_root)}
                )
                tasks.append((agent, task))

        if not tasks:
            return results

        # Execute concurrent tasks with ThreadPoolExecutor
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(tasks))) as executor:
            future_to_agent = {
                executor.submit(agent.execute, task): (agent.agent_id, agent.agent_role)
                for agent, task in tasks
            }
            for future in concurrent.futures.as_completed(future_to_agent):
                aid, role = future_to_agent[future]
                try:
                    res = future.result()
                    results[aid] = res
                    self.logger.log(f"[{role}] Completed successfully.")
                except Exception as e:
                    self.logger.log(f"[{role}] Encountered error: {str(e)}")
                    results[aid] = AgentResult(
                        task_id="err",
                        agent_id=aid,
                        status="FAILED",
                        errors=[str(e)]
                    )

        return results

    def resolve_conflicts(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Resolves conflicting recommendations between agents (e.g. security fix vs quality simplification).
        Prioritizes Security > Correctness > Maintainability.
        """
        # Sort findings by priority: Critical Security > High Security > Quality
        priority_map = {
            "CRITICAL": 100,
            "HIGH": 80,
            "MEDIUM": 60,
            "LOW": 40,
            "INFO": 20
        }

        def get_score(f: Dict[str, Any]) -> int:
            if "severity" in f:
                return priority_map.get(f.get("severity", "LOW"), 30)
            return 10

        return sorted(findings, key=get_score, reverse=True)
