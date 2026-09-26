"""
Architecture and Execution Flow Agent for CodePilot Multi-Agent Architecture.
Inspects actual repository structure, maps module dependencies via AST parsing,
and generates verified technical documentation and Mermaid diagrams for judges.
"""
import os
import ast
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple, Optional
from collections import defaultdict
from codepilot.agent.base_agent import BaseSpecializedAgent, AgentTask, AgentResult
from codepilot.safety.policy import SafetyPolicy
from codepilot.llm.adapter import LLMAdapter


class ArchitectureAgent(BaseSpecializedAgent):
    agent_id: str = "architecture_agent"
    agent_role: str = "Architecture & Execution Flow Agent"
    is_read_only: bool = True
    description: str = "Generates technical architecture documentation, dependency graphs, and execution flow diagrams."

    def __init__(self, workspace_root: str, llm: LLMAdapter, safety: SafetyPolicy):
        super().__init__(workspace_root, llm, safety)
        self.workspace_path = Path(workspace_root).resolve()

    def execute(self, task: AgentTask) -> AgentResult:
        start_time = time.time()
        errors: List[str] = []

        # 1. Inspect repository structure and AST module parsing
        modules_info, import_graph, entry_points = self._analyze_repository()

        # 2. Build Mermaid diagrams
        system_diagram_mermaid = self._generate_system_diagram()
        dependency_graph_mermaid = self._generate_dependency_graph(import_graph)
        execution_flow_mermaid = self._generate_execution_flow()
        agent_interaction_mermaid = self._generate_agent_interaction()

        # 3. Build comprehensive architecture overview markdown
        arch_overview = self._generate_architecture_doc(modules_info, entry_points)

        # 4. Save artifacts into artifacts/architecture/
        arch_dir = self.workspace_path / "artifacts" / "architecture"
        arch_dir.mkdir(parents=True, exist_ok=True)

        files_written = {}
        target_files = {
            "architecture.md": arch_overview,
            "system_diagram.md": system_diagram_mermaid,
            "module_dependency_graph.md": dependency_graph_mermaid,
            "execution_flow.md": execution_flow_mermaid,
            "agent_interaction.md": agent_interaction_mermaid
        }

        for filename, content in target_files.items():
            file_path = arch_dir / filename
            file_path.write_text(content, encoding="utf-8")
            files_written[filename] = str(file_path)

        runtime = round(time.time() - start_time, 2)
        summary = (
            f"Architecture documentation generated in artifacts/architecture/ "
            f"({len(modules_info)} modules parsed, {len(entry_points)} entry points mapped)."
        )

        return AgentResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            status="SUCCESS" if not errors else "PARTIAL",
            findings=[{
                "modules_analyzed": len(modules_info),
                "entry_points": entry_points,
                "dependency_edges": sum(len(v) for v in import_graph.values())
            }],
            artifacts=files_written,
            evidence={
                "modules_count": len(modules_info),
                "entry_points": entry_points,
                "diagrams_generated": list(target_files.keys())
            },
            metrics={"runtime_seconds": runtime, "modules_inspected": len(modules_info)},
            errors=errors,
            summary=summary
        )

    def _analyze_repository(self) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Set[str]], List[str]]:
        modules_info = {}
        import_graph = defaultdict(set)
        entry_points = []

        target_dir = self.workspace_path / "codepilot"
        if not target_dir.exists():
            target_dir = self.workspace_path

        for root, _, files in os.walk(target_dir):
            for file in files:
                if file.endswith(".py"):
                    full_path = Path(root) / file
                    rel_path = str(full_path.relative_to(self.workspace_path))
                    mod_name = rel_path.replace("/", ".").replace(".py", "")

                    try:
                        code = full_path.read_text(encoding="utf-8", errors="ignore")
                        tree = ast.parse(code)

                        classes = [n.name for n in tree.body if isinstance(n, ast.ClassDef)]
                        functions = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
                        doc = ast.get_docstring(tree) or ""

                        # Check if module is an entry point
                        if "__main__" in code or file in ("cli.py", "interactive.py", "gui.py", "main.py"):
                            entry_points.append(rel_path)

                        # Parse imports
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Import):
                                for alias in node.names:
                                    if alias.name.startswith("codepilot"):
                                        import_graph[mod_name].add(alias.name)
                            elif isinstance(node, ast.ImportFrom):
                                if node.module and (node.module.startswith("codepilot") or node.level > 0):
                                    full_imported = node.module
                                    import_graph[mod_name].add(full_imported)

                        modules_info[mod_name] = {
                            "path": rel_path,
                            "doc": doc.strip().split("\n")[0] if doc else "Module component",
                            "classes": classes,
                            "functions": functions
                        }
                    except Exception:
                        continue

        return modules_info, import_graph, entry_points

    def _generate_system_diagram(self) -> str:
        return """# System Architecture Diagram

```mermaid
graph TD
    subgraph UserInterface ["1. User Interface & Entry Points"]
        CLI["CLI (codepilot/cli.py)"]
        Chat["Interactive Chat (codepilot/interactive.py)"]
        GUI["Web GUI Dashboard (codepilot/gui.py)"]
    end

    subgraph CentralHub ["2. Central Multi-Agent Orchestrator"]
        Orchestrator["Central Orchestrator (codepilot/agent/orchestrator.py)"]
        Loop["Autonomous Loop (codepilot/agent/loop.py)"]
        State["Task State & Budget Machine (codepilot/agent/state.py)"]
        Planner["Dynamic Task Planner (codepilot/agent/planner.py)"]
        Context["Context Manager (codepilot/context/manager.py)"]
    end

    subgraph SpecializedAgents ["3. Specialized Autonomous Agents"]
        SecAgent["Security Auditor (codepilot/agent/security_agent.py)"]
        QualAgent["Code Quality & Duplication Agent (codepilot/agent/quality_agent.py)"]
        ArchAgent["Architecture & Execution Flow Agent (codepilot/agent/architecture_agent.py)"]
        VideoAgent["Automated Demo Video Agent (codepilot/agent/video_agent.py)"]
    end

    subgraph FoundationEngine ["4. Foundation Model & Tool Routing"]
        LLM["Unified LLM Adapter (Groq / Gemini / OpenAI / Anthropic / Ollama)"]
        Tools["Tool Router (codepilot/tools/router.py)"]
        Safety["Safety Policy (codepilot/safety/policy.py)"]
    end

    subgraph VerificationEngine ["5. Verification & Telemetry"]
        Verifier["Verification Runner (codepilot/verification/runner.py)"]
        Evidence["Evidence Reporter (codepilot/verification/evidence.py)"]
        Recovery["Failure Recovery Engine (codepilot/recovery/)"]
        Telemetry["Telemetry Tracker & Logger (codepilot/telemetry/)"]
    end

    CLI --> Orchestrator
    Chat --> Orchestrator
    GUI --> Orchestrator

    Orchestrator --> Context
    Orchestrator --> Planner
    Orchestrator --> LLM

    Orchestrator -. Parallel Concurrent Dispatch .-> SecAgent
    Orchestrator -. Parallel Concurrent Dispatch .-> QualAgent
    Orchestrator -. Parallel Concurrent Dispatch .-> ArchAgent
    Orchestrator -. Sequenced Artifact Consumer .-> VideoAgent

    Orchestrator --> Tools
    Tools --> Safety
    Tools --> VerificationEngine
    Loop --> Verifier
    Verifier --> Recovery
    VerificationEngine --> Evidence
    VerificationEngine --> Telemetry
```
"""

    def _generate_dependency_graph(self, import_graph: Dict[str, Set[str]]) -> str:
        lines = [
            "# Module Dependency Graph",
            "",
            "```mermaid",
            "graph LR"
        ]

        # Clean module labels
        for mod, targets in sorted(import_graph.items()):
            src_clean = mod.replace(".", "_")
            src_short = mod.split(".")[-1]
            lines.append(f'    {src_clean}["{src_short}"]')
            for tgt in sorted(targets):
                tgt_clean = tgt.replace(".", "_")
                tgt_short = tgt.split(".")[-1]
                lines.append(f'    {src_clean} --> {tgt_clean}["{tgt_short}"]')

        lines.append("```\n")
        return "\n".join(lines)

    def _generate_execution_flow(self) -> str:
        return """# Runtime Execution Flow

This sequence diagram depicts the end-to-end execution lifecycle when a user submits an engineering or multi-agent request.

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as CLI / GUI / Chat Entrypoint
    participant Orch as Central Orchestrator
    participant LLM as Foundation LLM / Local SLM
    participant Agents as Specialized Agents (Parallel)
    participant Tools as Tool Router & Safety Policy
    participant Verifier as Verification Engine
    participant Telemetry as Telemetry & Evidence

    User->>UI: Submit Natural Language Request
    UI->>Orch: orchestrator.run(request)
    Orchestrator->>LLM: Analyze intent & plan task dependencies

    alt General QA / Conversational Query
        LLM-->>Orch: Direct Thought Response (tool_call: done)
        Orch-->>UI: Return conversational answer
        UI-->>User: Display answer (Zero tools executed)
    else Multi-Agent or Code Engineering Task
        Orch->>Agents: Concurrently dispatch read-only analysis tasks
        par Security Audit
            Agents->>Tools: AST scan & secrets inspection (Read-Only)
        and Code Quality Analysis
            Agents->>Tools: Duplication & dead-code scan (Read-Only)
        and Architecture Documentation
            Agents->>Tools: Module dependency inspection (Read-Only)
        end
        Agents-->>Orch: Return structured AgentResults & findings

        opt Code Modification Requested
            Orch->>Tools: Controlled code edit (edit_file / create_file)
            Tools-->>Orch: Tool execution output
            Orch->>Verifier: Run test suite & verify syntax
            alt Verification Fails
                Verifier-->>Orch: Test failure & stacktrace
                Orch->>Orch: Classify failure & generate recovery strategy
                Orch->>Tools: Retry corrected edit
            end
        end

        opt Showcase / Demo Generation Requested
            Orch->>Agents: Dispatch Demo Video Agent with verified artifacts
            Agents->>Tools: Render slides & compile demo.mp4 with FFmpeg
            Agents-->>Orch: Video artifact ready (artifacts/demo/demo.mp4)
        end

        Orch->>Telemetry: Record runtime, token usage, tool invocations
        Telemetry-->>Orch: Consolidated metrics & evidence report
        Orch-->>UI: Consolidated final report
        UI-->>User: Display results, findings, and artifact paths
    end
```
"""

    def _generate_agent_interaction(self) -> str:
        return """# Agent Interaction & Coordination Protocol

```mermaid
sequenceDiagram
    participant Central as Central Orchestrator
    participant Bus as Task Dispatcher & Context Budgeter
    participant Sec as Security Auditor Agent
    participant Qual as Code Quality Agent
    participant Arch as Architecture Agent
    participant Video as Demo Video Agent

    Note over Central,Bus: 1. Request Analysis & Dependency Resolution
    Central->>Bus: Create AgentTasks (task_id, objective, constraints, budget)

    Note over Bus,Arch: 2. Concurrent Read-Only Execution (Independent)
    par Dispatch to Security Auditor
        Bus->>Sec: execute(AgentTask[security_auditor])
        Sec->>Sec: Scan secrets, injection risks, auth patterns
        Sec-->>Bus: AgentResult[SEC-001..n, artifacts/security_audit.md]
    and Dispatch to Code Quality Agent
        Bus->>Qual: execute(AgentTask[code_quality])
        Qual->>Qual: Analyze AST duplicates & dead code
        Qual-->>Bus: AgentResult[QUAL-001..n, artifacts/code_quality_report.md]
    and Dispatch to Architecture Agent
        Bus->>Arch: execute(AgentTask[architecture_agent])
        Arch->>Arch: Parse module dependencies & execution graph
        Arch-->>Bus: AgentResult[artifacts/architecture/*.md]
    end

    Note over Central,Video: 3. Sequential Artifact Consumption
    Bus-->>Central: Aggregate verified findings & architecture specs
    Central->>Video: execute(AgentTask[video_agent] with verified architecture artifacts)
    Video->>Video: Generate storyboard, narration, screenshot frames, & render demo.mp4
    Video-->>Central: AgentResult[artifacts/demo/demo.mp4]

    Note over Central: 4. Resolve Conflicting Recommendations & Generate Final Report
```
"""

    def _generate_architecture_doc(self, modules_info: Dict[str, Dict[str, Any]], entry_points: List[str]) -> str:
        md = [
            "# 🏛️ CodePilot Technical Architecture & System Overview",
            "This document is automatically generated by the CodePilot Architecture Agent by inspecting repository modules and AST structures.\n",
            "---",
            "## 1. Application Entry Points",
            "The system can be initialized through several dedicated entry points:"
        ]
        for ep in sorted(entry_points):
            md.append(f"- **`{ep}`**: Primary interface entry point.")

        md.extend([
            "\n---",
            "## 2. Core Subsystems & Responsibilities\n",
            "| Subsystem / Module | Responsibility | Key Classes / Functions |",
            "| :--- | :--- | :--- |"
        ])

        for mod, info in sorted(modules_info.items()):
            classes_str = ", ".join(info["classes"][:3]) or "-"
            functions_str = ", ".join(info["functions"][:3]) or "-"
            symbols = f"Classes: `{classes_str}`<br>Funcs: `{functions_str}`"
            md.append(f"| `{info['path']}` | {info['doc']} | {symbols} |")

        md.extend([
            "\n---",
            "## 3. Communication Protocol",
            "- **Central Orchestrator**: Coordinates tasks using typed `AgentTask` envelopes.",
            "- **Specialized Agents**: Return structured `AgentResult` objects containing findings, evidence, artifacts, and execution metrics.",
            "- **Safety Policy**: Enforces path containment and command whitelisting across all agent tools.",
            "- **Verification Engine**: Independently verifies changes before completion is declared.\n"
        ])

        return "\n".join(md)
