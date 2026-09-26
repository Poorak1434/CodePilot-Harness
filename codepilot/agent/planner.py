"""
Planner module for task decomposition and plan adjustments.
"""
from typing import List, Dict, Any


class Planner:
    @staticmethod
    def create_initial_plan(task_description: str, relevant_files: List[Dict[str, Any]]) -> List[str]:
        plan = [
            f"Explore repository and inspect relevant files: {[f['path'] for f in relevant_files]}",
            "Identify buggy functions or missing assertions",
            "Apply code modifications using edit_file / create_file",
            "Run test suite with run_tests to verify fix",
            "Inspect git diff and submit final verified solution"
        ]
        return plan

    @staticmethod
    def adjust_plan_for_failure(current_plan: List[str], recovery_hint: str) -> List[str]:
        new_plan = list(current_plan)
        new_plan.insert(0, f"RECOVERY STEP: {recovery_hint}")
        return new_plan[:6]
