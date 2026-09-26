"""
Recovery Strategy generator for producing re-planning guidance.
"""
from typing import Dict, Any
from codepilot.recovery.classifier import FailureCategory


class RecoveryStrategy:
    @staticmethod
    def generate_hint(classification: Dict[str, Any]) -> str:
        category = classification["category"]
        extract = classification["extract"]

        if category == FailureCategory.TEST_FAILURE:
            return (
                f"RECOVERY HINT: Unit test failed ({extract}). "
                "Inspect the failing assertion in test suite, review logic in target implementation file, "
                "and correct the return value or edge case."
            )

        if category == FailureCategory.SYNTAX_ERROR:
            return (
                f"RECOVERY HINT: Code contains syntax error ({extract}). "
                "Read the modified file lines carefully to check for missing colons, invalid indents, or unclosed brackets."
            )

        if category == FailureCategory.IMPORT_ERROR:
            return (
                f"RECOVERY HINT: Import failed ({extract}). "
                "Verify module import path, standard library availability, or variable names."
            )

        if category == FailureCategory.SAFETY_VIOLATION:
            return (
                f"RECOVERY HINT: Action violated safety policy ({extract}). "
                "Do not attempt dangerous shell commands or paths outside workspace. Use safe standard tools."
            )

        if category == FailureCategory.COMMAND_TIMEOUT:
            return (
                "RECOVERY HINT: Command execution timed out. "
                "Avoid long-running interactive blocking commands. Run concise test commands."
            )

        return f"RECOVERY HINT: Execution error ({extract}). Review tool parameters and error traceback before retrying."
