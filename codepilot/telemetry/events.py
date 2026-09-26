"""
Structured trace logging for observable harness execution.
"""
import time
from typing import List, Dict, Any


class TraceLogger:
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.events: List[Dict[str, Any]] = []
        self.step_counter = 0

    def log(self, message: str, details: Dict[str, Any] = None) -> str:
        self.step_counter += 1
        formatted_step = f"[{self.step_counter:02d}] {message}"
        event = {
            "step": self.step_counter,
            "timestamp": time.time(),
            "message": message,
            "formatted": formatted_step,
            "details": details or {}
        }
        self.events.append(event)

        if self.verbose:
            print(formatted_step)

        return formatted_step

    def get_formatted_trace(self) -> List[str]:
        return [e["formatted"] for e in self.events]
