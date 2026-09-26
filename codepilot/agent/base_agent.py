"""
Base Agent Infrastructure for CodePilot Multi-Agent Architecture.
Defines AgentTask, AgentResult, and BaseSpecializedAgent interfaces.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import time
from codepilot.safety.policy import SafetyPolicy
from codepilot.llm.adapter import LLMAdapter


@dataclass
class AgentTask:
    task_id: str
    agent_id: str
    objective: str
    context: Dict[str, Any] = field(default_factory=dict)
    constraints: List[str] = field(default_factory=list)
    budget: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "objective": self.objective,
            "context": self.context,
            "constraints": self.constraints,
            "budget": self.budget
        }


@dataclass
class AgentResult:
    task_id: str
    agent_id: str
    status: str  # "SUCCESS", "FAILED", "PARTIAL"
    findings: List[Dict[str, Any]] = field(default_factory=list)
    artifacts: Dict[str, str] = field(default_factory=dict)  # artifact_name -> file_path
    evidence: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "status": self.status,
            "findings": self.findings,
            "artifacts": self.artifacts,
            "evidence": self.evidence,
            "metrics": self.metrics,
            "errors": self.errors,
            "summary": self.summary
        }


class BaseSpecializedAgent:
    """Abstract base class for all specialized domain agents in CodePilot."""
    agent_id: str = "base_agent"
    agent_role: str = "Specialized Agent"
    is_read_only: bool = True
    description: str = "Base specialized agent."

    def __init__(self, workspace_root: str, llm: LLMAdapter, safety: SafetyPolicy):
        self.workspace_root = workspace_root
        self.llm = llm
        self.safety = safety

    def execute(self, task: AgentTask) -> AgentResult:
        """Executes the specialized task and returns an AgentResult."""
        raise NotImplementedError("Subclasses must implement execute()")
