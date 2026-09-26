"""
Autonomous Machine Provider Protocol - Wire types and event definitions.
Follows the openharness specification (autonomous-ai/openharness/provider/spec).
"""
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone


EVENT_KINDS = [
    "turn_started",
    "user_message",
    "thinking_title",
    "thinking_delta",
    "text_delta",
    "tool_start",
    "tool_end",
    "context_compact",
    "done",
    "recap_start",
    "recap_end",
]

TERMINAL_KINDS = [
    "turn_completed",
    "turn_failed",
    "turn_cancelled",
    "turn_input_required",
]

ERROR_CODES = [
    "unauthenticated",
    "not_found",
    "unsupported",
    "invalid_request",
    "rate_limited",
    "internal",
]


def current_iso_time() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ProviderError:
    code: str
    message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {"code": self.code}
        if self.message:
            d["message"] = self.message
        return d


@dataclass
class ProviderEvent:
    kind: Optional[str] = None
    text: Optional[str] = None
    turnId: Optional[str] = None
    agentId: Optional[str] = None
    at: Optional[str] = None
    title: Optional[str] = None
    thinkingId: Optional[str] = None
    toolId: Optional[str] = None
    tool: Optional[str] = None
    input: Optional[Any] = None
    ok: Optional[bool] = None
    output: Optional[str] = None
    summary: Optional[str] = None
    durationSeconds: Optional[float] = None
    recap: Optional[str] = None
    prompt: Optional[str] = None
    error: Optional[ProviderError] = None

    def to_dict(self) -> Dict[str, Any]:
        res: Dict[str, Any] = {}
        for k, v in asdict(self).items():
            if v is not None:
                if k == "error" and isinstance(v, dict):
                    res[k] = v
                else:
                    res[k] = v
        return res


@dataclass
class AgentDescriptor:
    id: str
    name: str
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"id": self.id, "name": self.name}
        if self.description:
            d["description"] = self.description
        return d
