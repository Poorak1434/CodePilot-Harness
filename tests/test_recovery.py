import unittest
from codepilot.tools.base import ToolResult
from codepilot.recovery import FailureDetector, FailureClassifier, FailureCategory, RecoveryStrategy


class TestRecoveryEngine(unittest.TestCase):
    def test_failure_detection_and_classification(self):
        # 1. Test failure result
        fail_res = ToolResult(
            success=False,
            output="FAILED tests/test_math.py::test_add - AssertionError: assert 5 == 4",
            error="Command exited with return code 1"
        )
        self.assertTrue(FailureDetector.is_failure(fail_res))

        classified = FailureClassifier.classify(fail_res.error, fail_res.output)
        self.assertEqual(classified["category"], FailureCategory.TEST_FAILURE)

        hint = RecoveryStrategy.generate_hint(classified)
        self.assertIn("RECOVERY HINT", hint)
        self.assertIn("AssertionError", hint)

    def test_syntax_error_classification(self):
        classified = FailureClassifier.classify("SyntaxError: invalid syntax", "File 'auth.py', line 10\n    def func(\n            ^")
        self.assertEqual(classified["category"], FailureCategory.SYNTAX_ERROR)


if __name__ == "__main__":
    unittest.main()
