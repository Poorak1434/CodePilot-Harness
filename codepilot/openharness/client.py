"""
OpenHarness Python Client for interacting with Autonomous Machine Provider endpoints.
Decodes JSON-RPC responses and parses Server-Sent Events (SSE) streams into ProviderEvents.
"""
import json
import uuid
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional, Iterator

from codepilot.openharness.protocol import ProviderEvent, ProviderError


class OpenHarnessClient:
    """Client for testing and executing OpenHarness Provider endpoints."""

    def __init__(self, endpoint_url: str = "http://localhost:4319", token: Optional[str] = None):
        self.endpoint_url = endpoint_url.rstrip("/")
        self.token = token

    def _make_headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _call_rpc(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        req_id = str(uuid.uuid4())[:8]
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params or {},
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.endpoint_url, data=data, headers=self._make_headers())

        try:
            with urllib.request.urlopen(req) as resp:
                body = resp.read().decode("utf-8")
                res_obj = json.loads(body)
                if "error" in res_obj:
                    raise RuntimeError(f"OpenHarness RPC Error: {res_obj['error']}")
                return res_obj.get("result", {})
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(err_body)
                if "error" in parsed:
                    raise RuntimeError(f"OpenHarness Error ({e.code}): {parsed['error']}")
            except Exception:
                pass
            raise RuntimeError(f"HTTP {e.code}: {err_body}")

    def list_agents(self) -> List[Dict[str, Any]]:
        res = self._call_rpc("agent.list")
        return res.get("agents", [])

    def send_message(self, agent_id: str, text: str, turn_id: Optional[str] = None) -> Iterator[ProviderEvent]:
        """Send a message to an agent and yield streamed ProviderEvents from SSE."""
        tid = turn_id or f"t_{uuid.uuid4().hex[:12]}"
        req_id = str(uuid.uuid4())[:8]
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "agent.send",
            "params": {
                "agentId": agent_id,
                "turnId": tid,
                "message": {"text": text},
            },
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.endpoint_url, data=data, headers=self._make_headers())

        with urllib.request.urlopen(req) as resp:
            for line in resp:
                decoded = line.decode("utf-8")
                if decoded.startswith("data: "):
                    json_str = decoded[6:].strip()
                    if json_str:
                        ev_dict = json.loads(json_str)
                        ev = ProviderEvent(**ev_dict)
                        yield ev
                        if ev.kind in ("turn_completed", "turn_failed", "turn_cancelled", "turn_input_required"):
                            break

    def get_history(self, agent_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        res = self._call_rpc("agent.history", {"agentId": agent_id, "limit": limit})
        return res.get("events", [])

    def cancel_turn(self, turn_id: str) -> bool:
        res = self._call_rpc("turn.cancel", {"turnId": turn_id})
        return res.get("cancelled", False)

    def create_agent(self, name: str, description: Optional[str] = None) -> Dict[str, Any]:
        return self._call_rpc("agent.create", {"name": name, "description": description})

    def rename_agent(self, agent_id: str, name: str) -> Dict[str, Any]:
        return self._call_rpc("agent.rename", {"agentId": agent_id, "name": name})

    def delete_agent(self, agent_id: str) -> bool:
        res = self._call_rpc("agent.delete", {"agentId": agent_id})
        return res.get("deleted", False)

    def get_recap(self, agent_id: str) -> Optional[str]:
        res = self._call_rpc("agent.recap", {"agentId": agent_id})
        return res.get("recap")
