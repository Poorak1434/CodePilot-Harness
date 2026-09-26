"""
Failure detector for identifying execution failures, test breakdowns, and runtime crashes.
"""
from typing import Optional, Dict, Any
from codepilot.tools.base import ToolResult


class FailureDetector:
    @staticmethod
    def is_failure(result: ToolResult) -> bool:
        """Determines if tool result represents a failure requiring recovery action."""
        if not result.success:
            return True
        if result.error is not None:
            return True
        # Check test runner specific output signals
        if "FAILED" in result.output or "FAIL:" in result.output or "ERROR:" in result.output:
            if "0 failed" not in result.output.lower() and "failed, 0" not in result.output.lower():
                return True
        return False
