"""
Autonomous Machine Provider Server for OpenHarness.
Implements the 8-method JSON-RPC 2.0 + Server-Sent Events (SSE) streaming protocol
specified by autonomous-ai/openharness/provider/spec.
"""
import os
import sys
import json
import time
import uuid
import threading
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, List, Optional

from codepilot.openharness.protocol import (
    ProviderEvent,
    ProviderError,
    AgentDescriptor,
    current_iso_time,
)
from codepilot.openharness.dsh import DSHRegistry
from codepilot.agent.orchestrator import AgentOrchestrator
from codepilot.agent.security_agent import SecurityAuditorAgent
from codepilot.agent.quality_agent import CodeQualityAgent
from codepilot.agent.architecture_agent import ArchitectureAgent
from codepilot.agent.video_agent import DemoVideoAgent
from codepilot.agent.base_agent import AgentTask


class OpenHarnessStore:
    """Stores agent registry and event histories for OpenHarness."""

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = workspace_root
        self.dsh_registry = DSHRegistry(workspace_root)
        self.agents: Dict[str, AgentDescriptor] = {
            "central-orchestrator": AgentDescriptor(
                id="central-orchestrator",
                name="Central Swarm Orchestrator",
                description="LLM-driven orchestrator coordinating CodePilot multi-agent workflows.",
            ),
            "security-auditor": AgentDescriptor(
                id="security-auditor",
                name="Security Auditor",
                description="AST static scanner for secrets, SQL/command injection, and vulnerabilities.",
            ),
            "code-quality": AgentDescriptor(
                id="code-quality",
                name="Code Quality Agent",
                description="Duplication detector, dead code finder, and maintainability refactoring.",
            ),
            "architecture-agent": AgentDescriptor(
                id="architecture-agent",
                name="Architecture Documentation Agent",
                description="AST dependency mapper generating Mermaid diagrams and architecture docs.",
            ),
            "video-demo": AgentDescriptor(
                id="video-demo",
                name="Automated Demo Video Agent",
                description="Produces storyboards, dark-mode slides, audio, and compiles demo.mp4.",
            ),
            "dsh-polymath": AgentDescriptor(
                id="dsh-polymath",
                name="Domain-Specific Polymath (DSH)",
                description="OpenHarness multidisciplinary harness: 3D CAD, circuits, MuJoCo robotics & audio.",
            ),
        }
        provider_name = os.getenv("OPENHARNESS_LLM_PROVIDER") or os.getenv("DEFAULT_PROVIDER") or "mock"
        self.orchestrator = AgentOrchestrator(workspace_root=workspace_root, provider=provider_name, verbose=False)
        self.history: Dict[str, List[Dict[str, Any]]] = {}
        self.recaps: Dict[str, str] = {}
        self.active_turns: Dict[str, bool] = {}
        self.lock = threading.Lock()

    def list_agents(self) -> List[AgentDescriptor]:
        with self.lock:
            return list(self.agents.values())

    def get_agent(self, agent_id: str) -> Optional[AgentDescriptor]:
        with self.lock:
            return self.agents.get(agent_id)

    def create_agent(self, name: str, description: Optional[str] = None) -> AgentDescriptor:
        with self.lock:
            agent_id = str(uuid.uuid4())[:8]
            desc = AgentDescriptor(id=agent_id, name=name, description=description)
            self.agents[agent_id] = desc
            self.history[agent_id] = []
            return desc

    def rename_agent(self, agent_id: str, new_name: str) -> Optional[AgentDescriptor]:
        with self.lock:
            if agent_id in self.agents:
                self.agents[agent_id].name = new_name
                return self.agents[agent_id]
            return None

    def delete_agent(self, agent_id: str) -> bool:
        with self.lock:
            if agent_id in self.agents:
                del self.agents[agent_id]
                self.history.pop(agent_id, None)
                return True
            return False

    def append_event(self, agent_id: str, event: Dict[str, Any]):
        with self.lock:
            if agent_id not in self.history:
                self.history[agent_id] = []
            self.history[agent_id].append(event)

    def get_history(self, agent_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        with self.lock:
            events = self.history.get(agent_id, [])
            return events[-limit:]

    def set_recap(self, agent_id: str, recap: str):
        with self.lock:
            self.recaps[agent_id] = recap

    def get_recap(self, agent_id: str) -> Optional[str]:
        with self.lock:
            return self.recaps.get(agent_id)

    def mark_turn_active(self, turn_id: str):
        with self.lock:
            self.active_turns[turn_id] = True

    def cancel_turn(self, turn_id: str):
        with self.lock:
            self.active_turns[turn_id] = False

    def is_turn_active(self, turn_id: str) -> bool:
        with self.lock:
            return self.active_turns.get(turn_id, True)


class OpenHarnessProviderHandler(BaseHTTPRequestHandler):
    store: OpenHarnessStore
    auth_token: Optional[str] = None

    def log_message(self, format, *args):
        pass

    def do_POST(self):
        # Enforce server-to-server constraint per OpenHarness spec
        if self.headers.get("Origin") is not None or self.headers.get("Sec-Fetch-Site") is not None:
            self._send_raw_json(403, {"error": "forbidden"})
            return

        # Check authentication if token configured
        if self.auth_token:
            auth_header = self.headers.get("Authorization", "")
            expected = f"Bearer {self.auth_token}"
            if auth_header != expected:
                self._send_rpc_error(None, "unauthenticated", "Invalid or missing Bearer token")
                return

        content_length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_length)

        try:
            req_data = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except Exception:
            self._send_rpc_error(None, "invalid_request", "Could not parse JSON body")
            return

        method = req_data.get("method", "")
        req_id = req_data.get("id")
        params = req_data.get("params", {}) or {}

        if method == "agent.list":
            agents = [a.to_dict() for a in self.store.list_agents()]
            self._send_rpc_result(req_id, {"agents": agents})

        elif method == "agent.send":
            self._handle_agent_send(req_id, params)

        elif method == "agent.history":
            agent_id = params.get("agentId", "")
            limit = int(params.get("limit", 100))
            if not self.store.get_agent(agent_id):
                self._send_rpc_error(req_id, "not_found", f"Agent '{agent_id}' not found")
                return
            events = self.store.get_history(agent_id, limit)
            self._send_rpc_result(req_id, {"agentId": agent_id, "events": events})

        elif method == "turn.cancel":
            turn_id = params.get("turnId", "")
            self.store.cancel_turn(turn_id)
            self._send_rpc_result(req_id, {"cancelled": True})

        elif method == "agent.create":
            name = params.get("name", "New Agent")
            desc = params.get("description")
            created = self.store.create_agent(name, desc)
            self._send_rpc_result(req_id, created.to_dict())

        elif method == "agent.rename":
            agent_id = params.get("agentId", "")
            name = params.get("name", "")
            renamed = self.store.rename_agent(agent_id, name)
            if not renamed:
                self._send_rpc_error(req_id, "not_found", f"Agent '{agent_id}' not found")
                return
            self._send_rpc_result(req_id, renamed.to_dict())

        elif method == "agent.delete":
            agent_id = params.get("agentId", "")
            deleted = self.store.delete_agent(agent_id)
            if not deleted:
                self._send_rpc_error(req_id, "not_found", f"Agent '{agent_id}' not found")
                return
            self._send_rpc_result(req_id, {"deleted": True})

        elif method == "agent.recap":
            agent_id = params.get("agentId", "")
            recap = self.store.get_recap(agent_id) or "No turns recorded yet for this agent."
            self._send_rpc_result(req_id, {"agentId": agent_id, "recap": recap})

        else:
            self._send_rpc_error(req_id, "unsupported", f"Method '{method}' is not supported")

    def _handle_agent_send(self, req_id: Any, params: Dict[str, Any]):
        """Stream Server-Sent Events (SSE) for the agent turn."""
        agent_id = params.get("agentId", "central-orchestrator")
        turn_id = params.get("turnId") or f"t_{uuid.uuid4().hex[:12]}"
        msg_obj = params.get("message", {})
        prompt = msg_obj.get("text", "") if isinstance(msg_obj, dict) else str(msg_obj)

        if not self.store.get_agent(agent_id):
            self._send_rpc_error(req_id, "not_found", f"Agent '{agent_id}' not found")
            return

        self.store.mark_turn_active(turn_id)

        # Send SSE Headers
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True

        def emit(event: ProviderEvent):
            ed = event.to_dict()
            self.store.append_event(agent_id, ed)
            data_str = f"data: {json.dumps(ed)}\n\n"
            try:
                self.wfile.write(data_str.encode("utf-8"))
                self.wfile.flush()
            except Exception:
                pass

        # 1. Turn Started
        emit(ProviderEvent(kind="turn_started", turnId=turn_id, agentId=agent_id, at=current_iso_time()))
        emit(ProviderEvent(kind="user_message", turnId=turn_id, text=prompt, at=current_iso_time()))

        if not self.store.is_turn_active(turn_id):
            emit(ProviderEvent(kind="turn_cancelled", turnId=turn_id, at=current_iso_time()))
            return

        # 2. Execution Routing
        try:
            emit(ProviderEvent(kind="thinking_title", turnId=turn_id, title=f"Executing {agent_id}...", at=current_iso_time()))
            
            output_text = ""
            recap_text = ""

            if agent_id == "security-auditor":
                emit(ProviderEvent(kind="tool_start", turnId=turn_id, tool="security_audit", input={"workspace": self.store.workspace_root}))
                auditor = self.store.orchestrator.get_agent("security_auditor")
                res = auditor.execute(AgentTask(task_id=turn_id, agent_id="security_auditor", objective=prompt))
                emit(ProviderEvent(kind="tool_end", turnId=turn_id, tool="security_audit", ok=(res.status == "SUCCESS"), output=res.summary))
                output_text = f"Security Audit Result:\n{res.summary}\nArtifacts: {res.artifacts}"
                recap_text = f"Audited codebase for vulnerabilities. {res.summary}"

            elif agent_id == "code-quality":
                emit(ProviderEvent(kind="tool_start", turnId=turn_id, tool="code_quality_scan", input={"workspace": self.store.workspace_root}))
                quality = self.store.orchestrator.get_agent("code_quality")
                res = quality.execute(AgentTask(task_id=turn_id, agent_id="code_quality", objective=prompt))
                emit(ProviderEvent(kind="tool_end", turnId=turn_id, tool="code_quality_scan", ok=(res.status == "SUCCESS"), output=res.summary))
                output_text = f"Code Quality Scan Result:\n{res.summary}\nArtifacts: {res.artifacts}"
                recap_text = f"Analyzed code maintainability and duplication. {res.summary}"

            elif agent_id == "architecture-agent":
                emit(ProviderEvent(kind="tool_start", turnId=turn_id, tool="map_architecture", input={"workspace": self.store.workspace_root}))
                arch = self.store.orchestrator.get_agent("architecture_agent")
                res = arch.execute(AgentTask(task_id=turn_id, agent_id="architecture_agent", objective=prompt))
                emit(ProviderEvent(kind="tool_end", turnId=turn_id, tool="map_architecture", ok=(res.status == "SUCCESS"), output=res.summary))
                output_text = f"Architecture Documentation Result:\n{res.summary}\nArtifacts: {res.artifacts}"
                recap_text = f"Mapped system architecture and module dependencies. {res.summary}"

            elif agent_id == "video-demo":
                emit(ProviderEvent(kind="tool_start", turnId=turn_id, tool="generate_demo_video", input={"prompt": prompt}))
                video = self.store.orchestrator.get_agent("demo_video")
                res = video.execute(AgentTask(task_id=turn_id, agent_id="demo_video", objective=prompt))
                emit(ProviderEvent(kind="tool_end", turnId=turn_id, tool="generate_demo_video", ok=(res.status == "SUCCESS"), output=res.summary))
                output_text = f"Demo Video Result:\n{res.summary}\nArtifacts: {res.artifacts}"
                recap_text = f"Created demo storyboard, slides, and compiled video. {res.summary}"

            elif agent_id == "dsh-polymath":
                emit(ProviderEvent(kind="tool_start", turnId=turn_id, tool="dsh_execute", input={"prompt": prompt}))
                # Auto-detect domain
                domain = "blender"
                prompt_lower = prompt.lower()
                if "circuit" in prompt_lower or "resistor" in prompt_lower or "pcb" in prompt_lower:
                    domain = "circuitjs"
                elif "robot" in prompt_lower or "mujoco" in prompt_lower or "joint" in prompt_lower:
                    domain = "mujoco"
                elif "music" in prompt_lower or "audio" in prompt_lower or "sound" in prompt_lower:
                    domain = "music-studio"
                elif "data" in prompt_lower or "plot" in prompt_lower or "csv" in prompt_lower:
                    domain = "data-studio"
                
                dsh_res = self.store.dsh_registry.execute_harness(domain, prompt)
                emit(ProviderEvent(kind="tool_end", turnId=turn_id, tool="dsh_execute", ok=(dsh_res.get("status") == "SUCCESS"), output=dsh_res.get("summary", "")))
                output_text = f"OpenHarness DSH Result ({domain}):\n{dsh_res.get('summary', '')}\nArtifacts: {dsh_res.get('artifacts', {})}"
                recap_text = dsh_res.get("summary", "")

            else:
                # Default to Central Swarm Orchestrator
                emit(ProviderEvent(kind="thinking_delta", turnId=turn_id, text="Planning swarm execution and coordinating tools...", at=current_iso_time()))
                orch = AgentOrchestrator(workspace_root=self.store.workspace_root, provider="ollama")
                read_only_agents = ["security_auditor", "code_quality", "architecture_agent"]
                results = orch.run_concurrent_agents(read_only_agents, prompt)
                summary_lines = [f"• {aid.upper()}: {res.summary}" for aid, res in results.items()]
                output_text = "Multi-Agent Swarm Orchestration Findings:\n" + "\n".join(summary_lines)
                recap_text = f"Orchestrated parallel analysis across {len(results)} specialized agents."

            if not self.store.is_turn_active(turn_id):
                emit(ProviderEvent(kind="turn_cancelled", turnId=turn_id, at=current_iso_time()))
                return

            # Stream response in chunks
            emit(ProviderEvent(kind="text_delta", turnId=turn_id, text=output_text, at=current_iso_time()))
            
            # Recap & Terminal Completion
            emit(ProviderEvent(kind="recap_start", turnId=turn_id, at=current_iso_time()))
            emit(ProviderEvent(kind="recap_end", turnId=turn_id, recap=recap_text, at=current_iso_time()))
            self.store.set_recap(agent_id, recap_text)
            
            emit(ProviderEvent(kind="turn_completed", turnId=turn_id, at=current_iso_time()))

        except Exception as e:
            err = ProviderError(code="internal", message=str(e))
            emit(ProviderEvent(kind="turn_failed", turnId=turn_id, error=err, at=current_iso_time()))

    def _send_raw_json(self, status: int, data: Dict[str, Any]):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def _send_rpc_result(self, req_id: Any, result: Dict[str, Any]):
        payload = {"jsonrpc": "2.0", "id": req_id, "result": result}
        self._send_raw_json(200, payload)

    def _send_rpc_error(self, req_id: Any, code: str, message: str):
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": code, "message": message},
        }
        self._send_raw_json(200, payload)


def start_openharness_provider_server(
    workspace_root: str = ".",
    port: int = 4319,
    auth_token: Optional[str] = None,
    blocking: bool = True,
) -> HTTPServer:
    """Start an OpenHarness Machine Provider server."""
    store = OpenHarnessStore(workspace_root=workspace_root)
    OpenHarnessProviderHandler.store = store
    OpenHarnessProviderHandler.auth_token = auth_token

    server_address = ("", port)
    try:
        httpd = HTTPServer(server_address, OpenHarnessProviderHandler)
    except OSError:
        port = port + 1
        httpd = HTTPServer(("", port), OpenHarnessProviderHandler)

    print(f"\033[1;35m[🌐 OpenHarness Provider Server listening on http://localhost:{port}]\033[0m")
    if auth_token:
        print(f"\033[1;33m[🔑 Bearer Token Authentication required]\033[0m")

    if not blocking:
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        return httpd

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[Stopping OpenHarness Provider Server. Goodbye!]")
        httpd.server_close()
        return httpd
