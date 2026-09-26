import unittest
import tempfile
from pathlib import Path
from codepilot.safety.policy import SafetyPolicy, SafetyViolationError


class TestSafetyPolicy(unittest.TestCase):
    def test_path_validation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = SafetyPolicy(workspace_root=tmpdir)
            
            # Valid path inside workspace
            valid_path = policy.validate_path("sub/file.py")
            self.assertEqual(valid_path, (Path(tmpdir) / "sub/file.py").resolve())
            
            # Path traversal attack
            with self.assertRaises(SafetyViolationError):
                policy.validate_path("../../etc/passwd")

    def test_command_validation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = SafetyPolicy(workspace_root=tmpdir)

            is_valid, reason = policy.validate_command("python3 -m pytest")
            self.assertTrue(is_valid)
            self.assertIsNone(reason)

            is_valid, reason = policy.validate_command("rm -rf /")
            self.assertFalse(is_valid)
            self.assertIn("blocked pattern", reason.lower())

            is_valid, reason = policy.validate_command("sudo apt-get update")
            self.assertFalse(is_valid)


if __name__ == "__main__":
    unittest.main()
