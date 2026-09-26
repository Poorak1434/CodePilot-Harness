"""
End-to-End autonomous loop verification test.
"""
import unittest
import tempfile
import shutil
import subprocess
import os
from pathlib import Path
from codepilot.agent.loop import AutonomousAgentLoop


class TestEndToEndHarness(unittest.TestCase):
    def test_full_autonomous_loop_with_recovery(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Copy demo repo files into tmpdir
            demo_src = Path(__file__).parent.parent / "demo_repo"
            for item in ["math_utils.py", "test_math_utils.py", "README.md"]:
                s = demo_src / item
                if s.exists():
                    shutil.copy2(s, Path(tmpdir) / item)

            # Initialize git repository
            subprocess.run(["git", "init"], cwd=tmpdir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["git", "add", "."], cwd=tmpdir, stdout=subprocess.DEVNULL)
            subprocess.run(
                ["git", "commit", "-m", "initial commit"],
                cwd=tmpdir,
                stdout=subprocess.DEVNULL,
                env={**os.environ, "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@test.com", "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@test.com"}
            )

            # Define deterministic LLM script simulating model actions
            mock_script = [
                # Turn 1: Model runs tests to observe failure
                {
                    "thought": "Initial step: execute unit tests to reproduce bug.",
                    "plan": ["Run tests", "Inspect failure"],
                    "tool_call": {
                        "name": "run_tests",
                        "arguments": {"test_command": "python3 -m unittest test_math_utils.py"}
                    }
                },
                # Turn 2: Model edits math_utils.py to fix formula
                {
                    "thought": "Test failed with AssertionError. Fixing math_utils.py discount formula.",
                    "plan": ["Edit math_utils.py", "Re-run tests"],
                    "tool_call": {
                        "name": "edit_file",
                        "arguments": {
                            "path": "math_utils.py",
                            "old_str": "price * (discount_percent / 1000)",
                            "new_str": "price * (discount_percent / 100)"
                        }
                    }
                },
                # Turn 3: Model re-runs tests to check fix
                {
                    "thought": "Code updated. Re-running unit test suite.",
                    "plan": ["Run tests"],
                    "tool_call": {
                        "name": "run_tests",
                        "arguments": {"test_command": "python3 -m unittest test_math_utils.py"}
                    }
                },
                # Turn 4: Model declares completion
                {
                    "thought": "All unit tests pass. Task completed.",
                    "plan": ["Declare completion"],
                    "tool_call": {
                        "name": "done",
                        "arguments": {"reason": "Fixed discount calculation formula"}
                    }
                }
            ]

            loop = AutonomousAgentLoop(
                workspace_root=tmpdir,
                provider="mock",
                test_command="python3 -m unittest test_math_utils.py",
                verbose=False
            )
            loop.orchestrator.llm.set_mock_script(mock_script)

            report = loop.run("Fix the discount calculation bug in math_utils.py")

            self.assertEqual(report["status"], "VERIFIED_SUCCESS")
            self.assertTrue(report["verification"]["passed"])
            self.assertIn("math_utils.py", report["verification"]["files_modified"])
            self.assertGreater(report["telemetry"]["retry_count"], 0)
            self.assertTrue(Path(tmpdir, "EVIDENCE_REPORT.json").exists())
            self.assertTrue(Path(tmpdir, "EVIDENCE_REPORT.md").exists())


if __name__ == "__main__":
    unittest.main()
