"""
Independent verification engine to prove code correctness using test runs and git diff inspection.
"""
from typing import Dict, Any, List, Optional
from codepilot.safety.policy import SafetyPolicy
from codepilot.tools.tests import RunTestsTool
from codepilot.tools.git import GitDiffTool, GitStatusTool


class VerificationResult:
    def __init__(
        self,
        passed: bool,
        tests_executed: bool,
        test_output: str,
        files_modified: List[str],
        git_diff: str,
        reason: str
    ):
        self.passed = passed
        self.tests_executed = tests_executed
        self.test_output = test_output
        self.files_modified = files_modified
        self.git_diff = git_diff
        self.reason = reason

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "tests_executed": self.tests_executed,
            "reason": self.reason,
            "files_modified": self.files_modified,
            "git_diff_length": len(self.git_diff),
            "test_output_preview": self.test_output[:1000]
        }


class VerificationRunner:
    def __init__(self, safety: SafetyPolicy):
        self.safety = safety
        self.test_tool = RunTestsTool(safety)
        self.diff_tool = GitDiffTool(safety)
        self.status_tool = GitStatusTool(safety)

    def verify(self, test_command: Optional[str] = None) -> VerificationResult:
        """
        Executes independent verification pipeline.
        1. Runs test suite
        2. Inspects git status / diff
        3. Validates non-empty change
        """
        test_res = self.test_tool.execute(test_command=test_command)
        diff_res = self.diff_tool.execute()
        status_res = self.status_tool.execute()

        # Parse modified files from git status
        modified_files = []
        for line in status_res.output.splitlines():
            line_str = line.strip()
            if line_str and not line_str.startswith("("):
                parts = line_str.split()
                if len(parts) >= 2:
                    modified_files.append(parts[-1])

        if not test_res.success:
            return VerificationResult(
                passed=False,
                tests_executed=True,
                test_output=test_res.output,
                files_modified=modified_files,
                git_diff=diff_res.output,
                reason="Verification Failed: Unit test execution failed."
            )

        if not modified_files and "(No diff)" in diff_res.output:
            return VerificationResult(
                passed=False,
                tests_executed=True,
                test_output=test_res.output,
                files_modified=[],
                git_diff=diff_res.output,
                reason="Verification Failed: No files were modified in repository."
            )

        return VerificationResult(
            passed=True,
            tests_executed=True,
            test_output=test_res.output,
            files_modified=modified_files,
            git_diff=diff_res.output,
            reason="Verification Passed: Tests executed successfully and verified repository diff."
        )
