"""
Planner module for task decomposition and recovery adjustments.
Driven dynamically by context and model intelligence without hardcoded routing.
"""
from typing import List, Dict, Any


class Planner:
    @staticmethod
    def create_initial_plan(task_description: str, relevant_files: List[Dict[str, Any]]) -> List[str]:
        """Creates an initial execution plan template grounded in relevant workspace files."""
        file_paths = [f["path"] for f in relevant_files] if relevant_files else []
        plan = [
            f"Analyze user objective: '{task_description}'",
            f"Inspect relevant repository context: {file_paths[:4] if file_paths else 'workspace root'}",
            "Coordinate required tools or specialized agents",
            "Independently verify outcomes and submit verified results"
        ]
        return plan

    @staticmethod
    def adjust_plan_for_failure(current_plan: List[str], recovery_hint: str) -> List[str]:
        """Adjusts current plan to insert a dynamic recovery step when a failure or error occurs."""
        new_plan = list(current_plan)
        new_plan.insert(0, f"RECOVERY STEP: {recovery_hint}")
        return new_plan[:6]
