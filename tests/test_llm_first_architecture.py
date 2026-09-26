"""
Unit tests verifying the 7 LLM-first core architecture success criteria.
"""
import unittest
import tempfile
import os
import shutil
from pathlib import Path
from codepilot.agent.loop import AutonomousAgentLoop
from codepilot.llm.adapter import LLMAdapter


class TestLLMFirstArchitecture(unittest.TestCase):
    def test_1_conversational_hi(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_script = [
                {
                    "thought": "Hello! How can I help you today?",
                    "plan": [],
                    "tool_call": {"name": "done", "arguments": {"reason": "Answered greeting"}}
                }
            ]
            loop = AutonomousAgentLoop(workspace_root=tmpdir, provider="mock", verbose=False)
            loop.orchestrator.llm.set_mock_script(mock_script)

            report = loop.run("hi")

            self.assertEqual(report["status"], "SUCCESS")
            self.assertTrue(report.get("is_conversational"))
            self.assertIn("Hello!", report["last_thought"])
            # Evidence report must NOT be saved for simple greetings!
            self.assertFalse(Path(tmpdir, "EVIDENCE_REPORT.json").exists())

    def test_2_conversational_explain(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_script = [
                {
                    "thought": "Binary search is an efficient algorithm for searching a sorted array in O(log n) time.",
                    "plan": [],
                    "tool_call": None
                }
            ]
            loop = AutonomousAgentLoop(workspace_root=tmpdir, provider="mock", verbose=False)
            loop.orchestrator.llm.set_mock_script(mock_script)

            report = loop.run("Explain binary search.")

            self.assertEqual(report["status"], "SUCCESS")
            self.assertTrue(report.get("is_conversational"))
            self.assertIn("Binary search", report["last_thought"])
            self.assertFalse(Path(tmpdir, "EVIDENCE_REPORT.json").exists())

    def test_3_standalone_code_generation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_script = [
                {
                    "thought": "Here is a C++ program to print multiples of 10:\n```cpp\n#include <iostream>\nint main() { for(int i=10; i<=700; i+=10) std::cout << i << std::endl; return 0; }\n```",
                    "plan": [],
                    "tool_call": {"name": "done", "arguments": {"reason": "Generated code"}}
                }
            ]
            loop = AutonomousAgentLoop(workspace_root=tmpdir, provider="mock", verbose=False)
            loop.orchestrator.llm.set_mock_script(mock_script)

            report = loop.run("Write a C++ program to print multiples of 10 till 700")

            self.assertEqual(report["status"], "SUCCESS")
            self.assertTrue(report.get("is_conversational"))
            self.assertIn("for(int i=10; i<=700; i+=10)", report["last_thought"])
            # Should NOT create fake files or evidence reports
            self.assertFalse(Path(tmpdir, "solution.cpp").exists())
            self.assertFalse(Path(tmpdir, "EVIDENCE_REPORT.json").exists())

    def test_4_agent_repo_inspection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "main.py").write_text("print('hello')", encoding="utf-8")

            mock_script = [
                {
                    "thought": "Listing directory contents to inspect workspace.",
                    "plan": ["List files"],
                    "tool_call": {"name": "list_dir", "arguments": {"path": "."}}
                },
                {
                    "thought": "Repository contains main.py which prints 'hello'.",
                    "plan": ["Explain architecture"],
                    "tool_call": {"name": "done", "arguments": {"reason": "Inspected repo"}}
                }
            ]
            loop = AutonomousAgentLoop(workspace_root=tmpdir, provider="mock", verbose=False)
            loop.orchestrator.llm.set_mock_script(mock_script)

            report = loop.run("Inspect this repository and explain its architecture.")

            self.assertIn(report["status"], ("VERIFIED_SUCCESS", "SUCCESS"))
            self.assertFalse(report.get("is_conversational"))
            self.assertIn("main.py", report["last_thought"])

    def test_6_conversation_history(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            history = [
                {"role": "user", "content": "Create a FastAPI server."},
                {"role": "assistant", "content": "Created main.py with FastAPI instance."}
            ]
            mock_script = [
                {
                    "thought": "Adding JWT authentication to the existing main.py FastAPI app based on previous conversation turn.",
                    "plan": ["Add JWT auth"],
                    "tool_call": {"name": "done", "arguments": {"reason": "Added JWT"}}
                }
            ]
            loop = AutonomousAgentLoop(workspace_root=tmpdir, provider="mock", verbose=False)
            loop.orchestrator.llm.set_mock_script(mock_script)

            report = loop.run("Now add JWT authentication.", history=history)

            self.assertEqual(report["status"], "SUCCESS")
            self.assertIn("JWT", report["last_thought"])

    def test_7_provider_error_reporting(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Test provider with missing key (Groq without key)
            adapter = LLMAdapter(provider="groq", api_key=None)
            old_env = os.environ.get("GROQ_API_KEY")
            if "GROQ_API_KEY" in os.environ:
                del os.environ["GROQ_API_KEY"]
            if "CODEPILOT_API_KEY" in os.environ:
                del os.environ["CODEPILOT_API_KEY"]

            try:
                resp = adapter.generate_response("system", "user context", [])
                self.assertTrue(resp.get("_api_error"))
                self.assertTrue("error" in resp.get("thought", "").lower() or "missing" in resp.get("thought", "").lower())

                loop = AutonomousAgentLoop(workspace_root=tmpdir, provider="groq", verbose=False)
                loop.orchestrator.llm = adapter
                report = loop.run("do something")

                self.assertEqual(report["status"], "PROVIDER_ERROR")
                self.assertFalse(Path(tmpdir, "EVIDENCE_REPORT.json").exists())
            finally:
                if old_env:
                    os.environ["GROQ_API_KEY"] = old_env


if __name__ == "__main__":
    unittest.main()
