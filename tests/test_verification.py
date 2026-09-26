import unittest
import tempfile
import os
import subprocess
from pathlib import Path
from codepilot.safety.policy import SafetyPolicy
from codepilot.verification import VerificationRunner, EvidenceReporter


class TestVerification(unittest.TestCase):
    def test_verification_runner_and_evidence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Initialize git repo in tmpdir for verification test
            subprocess.run(["git", "init"], cwd=tmpdir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            safety = SafetyPolicy(workspace_root=tmpdir)
            runner = VerificationRunner(safety)

            # Create test file
            test_file = Path(tmpdir, "test_sample.py")
            test_file.write_text("import unittest\nclass TestSample(unittest.TestCase):\n    def test_ok(self):\n        self.assertEqual(1, 1)\nif __name__ == '__main__':\n    unittest.main()\n")

            # Commit initial state
            subprocess.run(["git", "add", "."], cwd=tmpdir, stdout=subprocess.DEVNULL)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=tmpdir, stdout=subprocess.DEVNULL, env={**os.environ, "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@test.com", "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@test.com"})

            # Modify file to create diff
            test_file.write_text("import unittest\nclass TestSample(unittest.TestCase):\n    def test_ok(self):\n        self.assertEqual(1, 1)\n# edit comment\n")

            res = runner.verify(test_command="python3 -m unittest test_sample.py")
            self.assertTrue(res.passed)
            self.assertIn("test_sample.py", res.files_modified)

            # Generate evidence report
            report = EvidenceReporter.generate_report(
                task_description="Verify test_sample.py modification",
                verification=res,
                telemetry_metrics={"runtime_seconds": 1.2, "tool_calls": 3, "model_calls": 1},
                execution_trace=["[01] Task received", "[02] Tests passed"]
            )
            json_p, md_p = EvidenceReporter.save_report(report, output_directory=tmpdir)
            self.assertTrue(json_p.exists())
            self.assertTrue(md_p.exists())


if __name__ == "__main__":
    unittest.main()
