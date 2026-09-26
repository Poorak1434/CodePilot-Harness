"""
Task state machine and state definitions for CodePilot autonomous agent loop.
"""
from enum import Enum, auto
from typing import Dict, Any, List, Optional


class AgentPhase(Enum):
    RECEIVE = auto()
    EXPLORE = auto()
    BUILD_CONTEXT = auto()
    PLAN = auto()
    ACT = auto()
    OBSERVE = auto()
    VERIFY = auto()
    DIAGNOSE = auto()
    REPLAN = auto()
    RETRY = auto()
    DONE = auto()
    FAILED = auto()


class TaskState:
    def __init__(self, task_description: str, max_retries: int = 5, max_steps: int = 25):
        self.task_description = task_description
        self.phase = AgentPhase.RECEIVE
        self.max_retries = max_retries
        self.max_steps = max_steps
        self.step_count = 0
        self.retry_count = 0
        self.is_completed = False
        self.is_failed = False
        self.failure_reason: Optional[str] = None
        self.plan: List[str] = []

    def can_continue(self) -> bool:
        if self.is_completed or self.is_failed:
            return False
        if self.retry_count > self.max_retries:
            self.is_failed = True
            self.failure_reason = f"Exceeded max retries limit ({self.max_retries})."
            return False
        if self.step_count >= self.max_steps:
            self.is_failed = True
            self.failure_reason = f"Exceeded max step limit ({self.max_steps})."
            return False
        return True

    def increment_step(self) -> None:
        self.step_count += 1

    def increment_retry(self) -> None:
        self.retry_count += 1
