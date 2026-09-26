"""
Interactive Chat & REPL mode for CodePilot Harness.
Supports repository tasks, direct code snippet pasting & debugging, system commands, and live API key management.
"""
import sys
import os
import re
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

                # Check if input starts a multi-line code block ```
                if user_input.startswith("```"):
                    user_input = self._read_multiline_block(first_line=user_input)

                # Filter out single line code fragments (e.g. 'else:', 'return ...') from accidental multi-line pastes
                if self._is_incomplete_code_fragment(user_input):
                    print("\033[1;33m[Detected partial code line fragment. Use '/paste' command to paste multi-line code.]\033[0m")
                    continue

                # Execute task issue with Ctrl+C interrupt protection
                try:
                    self._run_task(user_input)
                except KeyboardInterrupt:
                    print("\n\033[1;31m[Task execution interrupted by user (Ctrl+C). Returning to prompt.]\033[0m\n")

            except EOFError:
                print("\nExiting CodePilot. Goodbye!")
                break
            except KeyboardInterrupt:
                print("\n\033[1;33m[Press Ctrl+C again or type /exit to exit CodePilot]\033[0m")

    def _is_incomplete_code_fragment(self, text: str) -> bool:
        """Checks if input is a partial code fragment from accidental multi-line paste."""
        stripped = text.strip()
        fragments = ("else:", "elif ", "return ", "def ", "class ", "if __name__", "main()", "print(", "greeting =", "active_users =")
        if stripped in ("else:", "main()", "pass") or (len(stripped) < 40 and any(stripped.startswith(f) for f in fragments)):
            if not any(k in stripped.lower() for k in ("fix", "bug", "issue", "create", "add", "update", "test")):
                return True
        return False

    def _read_multiline_block(self, first_line: str = "") -> str:
        lines = [first_line] if first_line else []
        print("\033[1;33m[Entering multi-line code mode. Type 'END' or '```' on a new line to finish]\033[0m")
        while True:
            try:
                line = input("... ").rstrip()
                if line.strip() in ("END", "```") and len(lines) > 1:
                    if line.strip() == "```":
                        lines.append(line)
                    break
                lines.append(line)
            except (KeyboardInterrupt, EOFError):
                break
        return "\n".join(lines)

    def _print_header(self) -> None:
        print("\033[1;36m" + "=" * 70 + "\033[0m")
        print(f"\033[1;36m  🚀 CodePilot AI Coding Harness v{__version__} — Interactive Mode\033[0m")
        print("\033[1;36m" + "=" * 70 + "\033[0m")
        print(f" • Target Repository : \033[1;32m{self.repo_path}\033[0m")
        print(f" • Model Provider   : \033[1;32m{self.provider}\033[0m")
        print(f" • Slash Commands   : \033[1;33m/paste, /repo <path>, /provider <name>, /key <api_key>, /verify, /diff, /status, /help, /exit\033[0m")
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
            print("  /paste            - Paste multi-line code snippet for quick debugging & fix")
            print("  /repo <path>      - Set active repository directory")
            print("  /provider <name>  - Set model provider (gemini, openai, anthropic, mock)")
            print("  /key <api_key>    - Set API Key for current model provider")
            print("  /test-cmd <cmd>   - Set custom test command (e.g. pytest or python3 -m unittest)")
            print("  /verify           - Run independent verification checks on repo")
            print("  /diff             - Show current uncommitted git diff")
            print("  /status           - Show repository git status")
            print("  /clear            - Clear terminal screen")
            print("  /exit             - Exit interactive shell\n")

        elif cmd in ("/paste", "/code", "/fixcode"):
            code_text = self._read_multiline_block()
            if code_text.strip():
                self._run_snippet_task(code_text)

        elif cmd == "/key":
            if not arg:
                print(f"Current API key for {self.provider}: {'[SET]' if os.getenv(f'{self.provider.upper()}_API_KEY') else '[NOT SET]'}")
            else:
                os.environ[f"{self.provider.upper()}_API_KEY"] = arg
                print(f"\033[1;32mAPI Key updated for {self.provider.upper()}.\033[0m")

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
                    env_var = f"{self.provider.upper()}_API_KEY"
                    if p_lower != "mock" and not os.getenv(env_var):
                        print(f"\033[1;33mNote: {env_var} is not set in environment.\033[0m")
                        key_input = input(f"Enter {self.provider.upper()} API Key (or press Enter to skip): ").strip()
                        if key_input:
                            os.environ[env_var] = key_input
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

    def _run_snippet_task(self, snippet_text: str) -> None:
        """Handles pasted code snippet directly."""
        clean_code = snippet_text.replace("```python", "").replace("```", "").strip()

        # Save snippet to sandbox_snippet.py inside target repo
        snippet_file = self.repo_path / "sandbox_snippet.py"
        snippet_file.write_text(clean_code, encoding="utf-8")

        test_cmd = self.test_command or "python3 sandbox_snippet.py"
        task_desc = f"Fix and debug the code snippet in sandbox_snippet.py: {clean_code[:100]}"

        agent_loop = AutonomousAgentLoop(
            workspace_root=str(self.repo_path),
            provider=self.provider,
            model_name=self.model_name,
            max_retries=self.max_retries,
            test_command=test_cmd,
            verbose=True
        )

        report = agent_loop.run(task_description=task_desc)

        # Output the fixed final code snippet directly in terminal!
        if snippet_file.exists():
            fixed_code = snippet_file.read_text(encoding="utf-8")
            print("\n\033[1;32m" + "=" * 70)
            print("✨ FINAL CORRECTED CODE OUTPUT:")
            print("=" * 70 + "\033[0m")
            print(fixed_code)
            print("\033[1;32m" + "=" * 70 + "\033[0m\n")

    def _run_task(self, issue_description: str) -> None:
        # Check if user input is raw code (contains def/class/function/import or multi-line code)
        if ("def " in issue_description or "class " in issue_description or "import " in issue_description or "\n" in issue_description) and not issue_description.startswith("Fix "):
            print("\033[1;33m[Detected raw code input. Processing code snippet debug & fix...]\033[0m")
            self._run_snippet_task(issue_description)
            return

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
        
        # Display the modified file contents directly if files were changed!
        if report['verification']['files_modified']:
            print("\n\033[1;32m" + "-" * 70)
            print("✨ FINAL CORRECTED FILE CODE OUTPUT:")
            print("-" * 70 + "\033[0m")
            for mod_f in report['verification']['files_modified']:
                mod_path = self.repo_path / mod_f
                if mod_path.is_file():
                    print(f"\033[1;34m[File: {mod_f}]\033[0m")
                    print(mod_path.read_text(encoding="utf-8", errors="replace"))
            print("\033[1;32m" + "-" * 70 + "\033[0m")

        print("=" * 70 + "\n")
