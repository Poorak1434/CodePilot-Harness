"""
Interactive Chat & REPL mode for CodePilot Harness.
Supports multi-turn general conversations, repo inspection, code generation, debugging, and live API key management.
"""
import sys
import os
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
from codepilot import __version__
from codepilot.agent.loop import AutonomousAgentLoop
from codepilot.safety.policy import SafetyPolicy
from codepilot.verification import VerificationRunner
from codepilot.tools.git import GitDiffTool, GitStatusTool


class InteractiveShell:
    def __init__(self, initial_repo: str = ".", provider: str = "gemini", model_name: Optional[str] = None):
        self.repo_path = Path(initial_repo).resolve()
        self.provider = provider
        self.model_name = model_name
        self.max_retries = 5
        self.test_command: Optional[str] = None
        self.verbose = False
        self.history: List[Dict[str, Any]] = []

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

                if user_input.startswith("```"):
                    user_input = self._read_multiline_block(first_line=user_input)

                try:
                    self._run_task(user_input)
                except KeyboardInterrupt:
                    print("\n\033[1;31m[Task execution interrupted by user (Ctrl+C). Returning to prompt.]\033[0m\n")

            except EOFError:
                print("\nExiting CodePilot. Goodbye!")
                break
            except KeyboardInterrupt:
                print("\n\033[1;33m[Press Ctrl+C again or type /exit to exit CodePilot]\033[0m")

    def _read_multiline_block(self, first_line: str = "") -> str:
        lines = [first_line] if first_line else []
        print("\033[1;33m[Entering multi-line text mode. Type 'END' or '```' on a new line to finish]\033[0m")
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
        print(f"\033[1;36m  🚀 CodePilot AI Coding Agent v{__version__} — Interactive Shell\033[0m")
        print("\033[1;36m" + "=" * 70 + "\033[0m")
        print(f" • Target Repository : \033[1;32m{self.repo_path}\033[0m")
        print(f" • Model Provider   : \033[1;32m{self.provider}\033[0m")
        print(f" • Slash Commands   : \033[1;33m/paste, /repo <path>, /provider <name>, /key <api_key>, /verify, /diff, /status, /clear, /exit\033[0m")
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
            print("  /paste            - Paste multi-line text or code snippet")
            print("  /audit            - 🛡️ Run Security Auditor on workspace")
            print("  /quality          - 🧹 Run Code Quality & Duplication Agent")
            print("  /arch             - 🏛️ Generate Architecture Documentation & Mermaid Diagrams")
            print("  /demo             - 🎬 Generate Demo Video (storyboard, narration, MP4)")
            print("  /workflow         - ⚡ Run full parallel Multi-Agent Pipeline")
            print("  /agents           - List all registered specialized domain agents")
            print("  /repo <path>      - Set active repository directory")
            print("  /provider <name>  - Set model provider (ollama, groq, gemini, openai, anthropic, mock)")
            print("  /key <api_key>    - Set API Key for current model provider")
            print("  /test-cmd <cmd>   - Set custom test command (e.g. pytest)")
            print("  /verify           - Run independent verification checks on repo")
            print("  /diff             - Show current uncommitted git diff")
            print("  /status           - Show repository git status")
            print("  /clear            - Clear terminal screen and history")
            print("  /exit             - Exit interactive shell\n")

        elif cmd == "/agents":
            loop = AutonomousAgentLoop(workspace_root=str(self.repo_path), provider=self.provider)
            agents = loop.orchestrator.list_agents()
            print("\nRegistered Specialized Agents:")
            for a in agents:
                print(f" • \033[1;36m{a['agent_id']}\033[0m ({a['role']}): {a['description']}")
            print()

        elif cmd == "/audit":
            self._run_task("Audit this repository for security vulnerabilities and produce a detailed audit report.")

        elif cmd == "/quality":
            self._run_task("Scan this repository for code duplication, dead code, and maintainability refactoring opportunities.")

        elif cmd == "/arch":
            self._run_task("Inspect the complete repository structure and generate technical architecture documentation and Mermaid diagrams.")

        elif cmd == "/demo":
            self._run_task("Generate a complete project showcase demo video for hackathon judges.")

        elif cmd == "/workflow":
            self._run_task("Execute full multi-agent workflow: audit security, check code quality, generate architecture documentation, and compile demo video.")

        elif cmd in ("/paste", "/code"):
            code_text = self._read_multiline_block()
            if code_text.strip():
                self._run_task(code_text)

        elif cmd == "/key":
            if not arg:
                print(f"Current API key for {self.provider}: {'[SET]' if os.getenv(f'{self.provider.upper()}_API_KEY') or os.getenv('CODEPILOT_API_KEY') else '[NOT SET]'}")
            else:
                os.environ[f"{self.provider.upper()}_API_KEY"] = arg
                os.environ["CODEPILOT_API_KEY"] = arg
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

        elif cmd in ("/groq", "/gemini", "/openai", "/anthropic", "/ollama", "/mock"):
            p_name = cmd[1:]
            self.provider = p_name
            if arg:
                os.environ[f"{self.provider.upper()}_API_KEY"] = arg
                os.environ["CODEPILOT_API_KEY"] = arg
                print(f"\033[1;32mProvider set to {self.provider.upper()} and API Key updated.\033[0m")
            else:
                print(f"\033[1;32mProvider updated to: {self.provider}\033[0m")

        elif cmd == "/provider":
            if not arg:
                print(f"Current provider: {self.provider}")
            else:
                p_lower = arg.lower()
                if p_lower in ("groq", "gemini", "openai", "anthropic", "ollama", "mock"):
                    self.provider = p_lower
                    print(f"\033[1;32mProvider updated to: {self.provider}\033[0m")
                else:
                    print("\033[1;31mInvalid provider. Choose from: groq, gemini, openai, anthropic, ollama, mock\033[0m")

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

        elif cmd in ("/quiet", "/clean"):
            self.verbose = False
            print("\033[1;32m[Clean Response Mode Enabled]\033[0m")

        elif cmd == "/verbose":
            self.verbose = True
            print("\033[1;32m[Verbose Telemetry Logging Enabled]\033[0m")

        elif cmd == "/clear":
            self.history = []
            os.system("clear" if os.name != "nt" else "cls")
            self._print_header()

        else:
            print(f"\033[1;31mUnknown slash command '{cmd}'. Type /help for assistance.\033[0m")

        return True

    def _run_task(self, user_text: str) -> None:
        agent_loop = AutonomousAgentLoop(
            workspace_root=str(self.repo_path),
            provider=self.provider,
            model_name=self.model_name,
            max_retries=self.max_retries,
            test_command=self.test_command,
            verbose=self.verbose
        )

        report = agent_loop.run(task_description=user_text, history=self.history)

        # Record turns in conversation history
        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": report.get("last_thought", "")})

        is_conversational = report.get("is_conversational", False)
        status = report.get("status")

        if status == "PROVIDER_ERROR":
            print("\n\033[1;31m" + "=" * 70)
            print("❌ LLM PROVIDER ERROR:")
            print("=" * 70 + "\033[0m")
            print(report.get("last_thought", "Provider Error"))
            print("\033[1;31m" + "=" * 70 + "\033[0m\n")
            return

        if is_conversational or not report.get("verification", {}).get("files_modified"):
            # Conversational Response - Render response text directly!
            response_text = report.get("last_thought") or report.get("response_text", "")
            print("\n\033[1;36mCodePilot:\033[0m")
            print(response_text)
            print()
        else:
            # Coding / Agent Mode Task Execution
            if self.verbose:
                print("\n" + "=" * 70)
                print("📊 AGENT TASK RESULT SUMMARY")
                print("=" * 70)
                status_colored = f"\033[1;32m{report['status']}\033[0m" if report["status"] == "VERIFIED_SUCCESS" else f"\033[1;31m{report['status']}\033[0m"
                print(f" • Status           : {status_colored}")
                metrics = report["telemetry"]
                print(f" • Runtime          : {metrics['runtime_seconds']}s")
                print(f" • Model Calls      : {metrics['model_calls']}")
                print(f" • Tool Invocations : {metrics['tool_calls']}")
                print(f" • Retries / Fixes  : {metrics['retry_count']}")
                print(f" • Modified Files   : {', '.join(report['verification']['files_modified']) or 'None'}")
                print("=" * 70 + "\n")

            thought_text = report.get("last_thought", "")
            print("\n\033[1;36mCodePilot:\033[0m")
            print(thought_text)
            print()

        artifacts = report.get("artifacts", {})
        if artifacts:
            print("\033[1;32m📦 Generated Artifacts:\033[0m")
            for name, path_str in sorted(artifacts.items()):
                print(f" • \033[1;33m{name}\033[0m -> {path_str}")
            print()
