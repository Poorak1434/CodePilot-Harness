"""
Interactive Chat & REPL mode for CodePilot Harness.
"""
import sys
import os
from pathlib import Path
from typing import Optional
from codepilot import __version__
from codepilot.agent.loop import AutonomousAgentLoop
from codepilot.safety.policy import SafetyPolicy
from codepilot.verification import VerificationRunner
from codepilot.tools.git import GitDiffTool, GitStatusTool


class InteractiveShell:
    def __init__(self, initial_repo: str = ".", provider: str = "mock", model_name: Optional[str] = None):
        self.repo_path = Path(initial_repo).resolve()
        self.provider = provider
        self.model_name = model_name
        self.max_retries = 5
        self.test_command: Optional[str] = None

    def start(self) -> None:
        self._print_header()

        while True:
            try:
                prompt_text = f"\033[1;34mcodepilot [{self.repo_path.name}]\033[0m> "
                user_input = input(prompt_text).strip()

                if not user_input:
                    continue

                if user_input.startswith("/"):
                    if not self._handle_slash_command(user_input):
                        break
                    continue

                # Execute task issue
                self._run_task(user_input)

            except (KeyboardInterrupt, EOFError):
                print("\nExiting CodePilot. Goodbye!")
                break

    def _print_header(self) -> None:
        print("\033[1;36m" + "=" * 70 + "\033[0m")
        print(f"\033[1;36m  🚀 CodePilot AI Coding Harness v{__version__} — Interactive Mode\033[0m")
        print("\033[1;36m" + "=" * 70 + "\033[0m")
        print(f" • Target Repository : \033[1;32m{self.repo_path}\033[0m")
        print(f" • Model Provider   : \033[1;32m{self.provider}\033[0m")
        print(f" • Slash Commands   : \033[1;33m/repo <path>, /provider <name>, /verify, /diff, /status, /help, /exit\033[0m")
        print("\033[1;36m" + "=" * 70 + "\033[0m\n")

    def _handle_slash_command(self, cmd_line: str) -> bool:
        parts = cmd_line.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if cmd in ("/exit", "/quit", "/q"):
            print("Goodbye!")
            return False

        elif cmd == "/help":
            print("\nAvailable Commands:")
            print("  /repo <path>      - Set active repository directory")
            print("  /provider <name>  - Set model provider (gemini, openai, anthropic, mock)")
            print("  /test-cmd <cmd>   - Set custom test command (e.g. pytest or python3 -m unittest)")
            print("  /verify           - Run independent verification checks on repo")
            print("  /diff             - Show current uncommitted git diff")
            print("  /status           - Show repository git status")
            print("  /clear            - Clear terminal screen")
            print("  /exit             - Exit interactive shell\n")

        elif cmd == "/repo":
            if not arg:
                print(f"Current repository: {self.repo_path}")
            else:
                new_path = Path(arg).resolve()
                if not new_path.exists():
                    print(f"\033[1;31mError: Path '{new_path}' does not exist.\033[0m")
                else:
                    self.repo_path = new_path
                    print(f"\033[1;32mActive repository updated to: {self.repo_path}\033[0m")

        elif cmd == "/provider":
            if not arg:
                print(f"Current provider: {self.provider}")
            else:
                p_lower = arg.lower()
                if p_lower in ("gemini", "openai", "anthropic", "ollama", "mock"):
                    self.provider = p_lower
                    print(f"\033[1;32mProvider updated to: {self.provider}\033[0m")
                else:
                    print("\033[1;31mInvalid provider. Choose from: gemini, openai, anthropic, ollama, mock\033[0m")

        elif cmd == "/test-cmd":
            if not arg:
                print(f"Current test command: {self.test_command or '(auto-detect)'}")
            else:
                self.test_command = arg
                print(f"\033[1;32mTest command updated to: {self.test_command}\033[0m")

        elif cmd == "/verify":
            print(f"Running independent verification on {self.repo_path}...")
            safety = SafetyPolicy(workspace_root=str(self.repo_path))
            runner = VerificationRunner(safety)
            res = runner.verify(test_command=self.test_command)
            print(f"Result : {'✅ PASS' if res.passed else '❌ FAIL'}")
            print(f"Reason : {res.reason}")
            print(f"Files  : {res.files_modified or 'None'}\n")

        elif cmd == "/diff":
            safety = SafetyPolicy(workspace_root=str(self.repo_path))
            diff_tool = GitDiffTool(safety)
            res = diff_tool.execute()
            print("\n--- Current Git Diff ---")
            print(res.output)
            print("-----------------------\n")

        elif cmd == "/status":
            safety = SafetyPolicy(workspace_root=str(self.repo_path))
            status_tool = GitStatusTool(safety)
            res = status_tool.execute()
            print(f"\n--- Git Status ({self.repo_path.name}) ---")
            print(res.output)
            print("------------------------------------\n")

        elif cmd == "/clear":
            os.system("clear" if os.name != "nt" else "cls")
            self._print_header()

        else:
            print(f"\033[1;31mUnknown slash command '{cmd}'. Type /help for assistance.\033[0m")

        return True

    def _run_task(self, issue_description: str) -> None:
        print("\n" + "=" * 70)
        print(f"▶ EXECUTING TASK: {issue_description}")
        print("=" * 70)

        agent_loop = AutonomousAgentLoop(
            workspace_root=str(self.repo_path),
            provider=self.provider,
            model_name=self.model_name,
            max_retries=self.max_retries,
            test_command=self.test_command,
            verbose=True
        )

        report = agent_loop.run(task_description=issue_description)

        print("\n" + "=" * 70)
        print("📊 TASK RESULT SUMMARY")
        print("=" * 70)
        status_colored = f"\033[1;32m{report['status']}\033[0m" if report["status"] == "VERIFIED_SUCCESS" else f"\033[1;31m{report['status']}\033[0m"
        print(f" • Status           : {status_colored}")
        metrics = report["telemetry"]
        print(f" • Runtime          : {metrics['runtime_seconds']}s")
        print(f" • Model Calls      : {metrics['model_calls']}")
        print(f" • Tool Invocations : {metrics['tool_calls']}")
        print(f" • Retries / Fixes  : {metrics['retry_count']}")
        print(f" • Modified Files   : {', '.join(report['verification']['files_modified']) or 'None'}")
        print(f" • Evidence Report  : EVIDENCE_REPORT.json & EVIDENCE_REPORT.md saved in target repo")
        print("=" * 70 + "\n")
