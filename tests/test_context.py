import unittest
import tempfile
from pathlib import Path
from codepilot.safety.policy import SafetyPolicy
from codepilot.context.manager import ContextManager


class TestContextManager(unittest.TestCase):
    def test_context_retrieval_and_compression(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            safety = SafetyPolicy(workspace_root=tmpdir)
            ctx_mgr = ContextManager(safety)

            # Create test files
            Path(tmpdir, "auth_service.py").write_text("def authenticate_user(token):\n    pass\n")
            Path(tmpdir, "test_auth.py").write_text("def test_authenticate():\n    assert False\n")

            ctx_mgr.initialize_task("Fix authentication bug in auth_service and update test_auth")

            formatted = ctx_mgr.get_formatted_context()
            self.assertIn("Fix authentication bug", formatted)
            self.assertIn("auth_service.py", formatted)
            self.assertIn("test_auth.py", formatted)

            # Test failure recording
            ctx_mgr.record_failure({"attempt": 1, "type": "TEST_FAILURE", "output": "AssertionError: Expected True got False"})
            formatted_with_failure = ctx_mgr.get_formatted_context()
            self.assertIn("AssertionError", formatted_with_failure)


if __name__ == "__main__":
    unittest.main()
