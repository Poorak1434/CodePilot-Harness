"""
Agent Coordination Tools enabling the Central Orchestrator LLM to delegate
specialized tasks to domain agents (Security, Quality, Architecture, Video)
and execute concurrent multi-agent inspection workflows.
"""
from typing import Dict, Any, List, Optional
import uuid
import concurrent.futures
from codepilot.tools.base import BaseTool, ToolResult
from codepilot.safety.policy import SafetyPolicy
from codepilot.agent.base_agent import AgentTask, AgentResult
from codepilot.agent.security_agent import SecurityAuditorAgent
from codepilot.agent.quality_agent import CodeQualityAgent
from codepilot.agent.architecture_agent import ArchitectureAgent
from codepilot.agent.video_agent import DemoVideoAgent


class DelegateToAgentTool(BaseTool):
    name = "delegate_to_agent"
    description = (
        "Delegates a specialized subtask to a domain agent. "
        "Available agents: 'security_auditor' (scans vulnerabilities, secrets, injections), "
        "'code_quality' (detects duplicates, dead code, simplification opportunities), "
        "'architecture_agent' (maps dependencies and Mermaid diagrams), "
        "'demo_video' (generates storyboard, narration, and renders playable demo.mp4 video)."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "agent_id": {
                "type": "string",
                "enum": ["security_auditor", "code_quality", "architecture_agent", "demo_video"],
                "description": "Identifier of the specialized agent to execute."
            },
            "objective": {
                "type": "string",
                "description": "Specific objective or focus for the agent."
            }
        },
        "required": ["agent_id", "objective"]
    }

    def __init__(self, orchestrator: Any):
        self.orchestrator = orchestrator

    def execute(self, agent_id: str, objective: str, **kwargs: Any) -> ToolResult:
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        task = AgentTask(
            task_id=task_id,
            agent_id=agent_id,
            objective=objective,
            context={"workspace": str(self.orchestrator.safety.workspace_root)}
        )

        agent = self.orchestrator.get_agent(agent_id)
        if not agent:
            return ToolResult(
                success=False,
                output="",
                error=f"Specialized agent '{agent_id}' is not registered."
            )

        try:
            self.orchestrator.logger.log(f"[{agent.agent_role}] Starting execution: '{objective}'")
            res: AgentResult = agent.execute(task)
            self.orchestrator.logger.log(f"[{agent.agent_role}] Finished: {res.summary}")

            return ToolResult(
                success=(res.status in ("SUCCESS", "PARTIAL")),
                output=res.summary,
                error="\n".join(res.errors) if res.errors else None,
                metadata={
                    "task_id": res.task_id,
                    "agent_id": res.agent_id,
                    "status": res.status,
                    "findings_count": len(res.findings),
                    "artifacts": res.artifacts
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Exception executing agent '{agent_id}': {str(e)}"
            )


class RunSecurityAuditTool(BaseTool):
    name = "run_security_audit"
    description = "Runs comprehensive security audit (vulnerabilities, exposed secrets, injection risks, auth checks)."
    parameters_schema = {
        "type": "object",
        "properties": {
            "objective": {
                "type": "string",
                "description": "Optional focus area for the security audit."
            }
        }
    }

    def __init__(self, orchestrator: Any):
        self.orchestrator = orchestrator

    def execute(self, objective: str = "Perform full repository security audit", **kwargs: Any) -> ToolResult:
        return self.orchestrator.tools.dispatch("delegate_to_agent", {
            "agent_id": "security_auditor",
            "objective": objective
        })


class RunCodeQualityTool(BaseTool):
    name = "run_code_quality_check"
    description = "Runs code quality and duplication analysis to find duplicate blocks, dead code, and simplification opportunities."
    parameters_schema = {
        "type": "object",
        "properties": {
            "objective": {
                "type": "string",
                "description": "Optional focus area for quality check."
            }
        }
    }

    def __init__(self, orchestrator: Any):
        self.orchestrator = orchestrator

    def execute(self, objective: str = "Scan for code duplication and maintainability issues", **kwargs: Any) -> ToolResult:
        return self.orchestrator.tools.dispatch("delegate_to_agent", {
            "agent_id": "code_quality",
            "objective": objective
        })


class GenerateArchitectureDocsTool(BaseTool):
    name = "generate_architecture_docs"
    description = "Inspects codebase and produces technical architecture documentation, module dependency graph, and Mermaid diagrams."
    parameters_schema = {
        "type": "object",
        "properties": {
            "objective": {
                "type": "string",
                "description": "Optional focus for architecture documentation."
            }
        }
    }

    def __init__(self, orchestrator: Any):
        self.orchestrator = orchestrator

    def execute(self, objective: str = "Generate system architecture and dependency documentation", **kwargs: Any) -> ToolResult:
        return self.orchestrator.tools.dispatch("delegate_to_agent", {
            "agent_id": "architecture_agent",
            "objective": objective
        })


class GenerateDemoVideoTool(BaseTool):
    name = "generate_demo_video"
    description = "Generates a project showcase video (storyboard, narration, slide frames, and real playable MP4) for hackathon judges."
    parameters_schema = {
        "type": "object",
        "properties": {
            "objective": {
                "type": "string",
                "description": "Optional custom angle or focus for the demo video."
            }
        }
    }

    def __init__(self, orchestrator: Any):
        self.orchestrator = orchestrator

    def execute(self, objective: str = "Generate complete showcase video for judges", **kwargs: Any) -> ToolResult:
        return self.orchestrator.tools.dispatch("delegate_to_agent", {
            "agent_id": "demo_video",
            "objective": objective
        })


class RunMultiAgentWorkflowTool(BaseTool):
    name = "run_multi_agent_workflow"
    description = (
        "Executes a multi-agent workflow: runs independent read-only agents (Security Auditor, "
        "Code Quality, Architecture) concurrently in parallel, consolidates findings, and prepares demo materials."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "include_video": {
                "type": "boolean",
                "description": "Whether to also generate showcase demo video after architecture analysis."
            }
        }
    }

    def __init__(self, orchestrator: Any):
        self.orchestrator = orchestrator

    def execute(self, include_video: bool = False, **kwargs: Any) -> ToolResult:
        read_only_agents = ["security_auditor", "code_quality", "architecture_agent"]
        self.orchestrator.logger.log("[Central Orchestrator] Launching parallel read-only analysis (Security + Quality + Architecture)...")

        results = self.orchestrator.run_concurrent_agents(read_only_agents, "Repository comprehensive audit and architectural inspection")

        output_lines = [
            "=== Multi-Agent Parallel Analysis Complete ==="
        ]
        for aid, res in results.items():
            output_lines.append(f"• {aid.upper()}: {res.summary}")

        if include_video:
            self.orchestrator.logger.log("[Central Orchestrator] Launching Demo Video Agent with verified architecture artifacts...")
            video_res = self.orchestrator.tools.dispatch("delegate_to_agent", {
                "agent_id": "demo_video",
                "objective": "Generate showcase demo video based on verified architecture"
            })
            output_lines.append(f"• DEMO_VIDEO: {video_res.output}")

        return ToolResult(
            success=True,
            output="\n".join(output_lines),
            metadata={"agent_results": {k: v.to_dict() for k, v in results.items()}}
        )
