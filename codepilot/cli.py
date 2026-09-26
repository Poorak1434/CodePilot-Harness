"""
CodePilot CLI Entry Point.
"""
import argparse
import sys
import os
from pathlib import Path
from codepilot import __version__
from codepilot.agent.loop import AutonomousAgentLoop
from codepilot.safety.policy import SafetyPolicy
from codepilot.interactive import InteractiveShell


def load_env_file():
    """Auto-load .env configuration file if present."""
    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip().strip('"').strip("'")


def main():
    load_env_file()
    
    # Determine default provider (default to Cloud Server API gemini)
    default_p = os.getenv("DEFAULT_PROVIDER") or "gemini"

    parser = argparse.ArgumentParser(
        prog="codepilot",
        description="CodePilot - Autonomous Coding-Agent Harness for Foundation Models"
    )
    parser.add_argument("--gui", action="store_true", help="Launch CodePilot Web Studio GUI Interface.")

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # `gui` subcommand
    gui_parser = subparsers.add_parser("gui", help="Launch interactive Web Studio GUI dashboard.")
    gui_parser.add_argument("--repo", type=str, default=".", help="Target repository directory path.")
    gui_parser.add_argument("--port", type=int, default=8080, help="Web server port.")

    # `chat` / interactive subcommand
    chat_parser = subparsers.add_parser("chat", help="Start continuous interactive chat / REPL mode.")
    chat_parser.add_argument("--repo", type=str, default=".", help="Target repository directory path.")
    chat_parser.add_argument("--provider", type=str, default=default_p, choices=["gemini", "openai", "anthropic", "ollama", "mock"], help="LLM Provider.")
    chat_parser.add_argument("--model", type=str, default=None, help="Specific model name.")

    # `fix` subcommand
    fix_parser = subparsers.add_parser("fix", help="Execute autonomous coding loop for a single task.")
    fix_parser.add_argument("--repo", type=str, default=".", help="Target repository directory path.")
    fix_parser.add_argument("--issue", type=str, required=True, help="Task or issue description.")
    fix_parser.add_argument("--provider", type=str, default=default_p, choices=["gemini", "openai", "anthropic", "ollama", "mock"], help="LLM Provider.")
    fix_parser.add_argument("--model", type=str, default=None, help="Specific model name.")
    fix_parser.add_argument("--max-retries", type=int, default=5, help="Maximum number of retry attempts.")
    fix_parser.add_argument("--test-cmd", type=str, default=None, help="Custom test command.")
    fix_parser.add_argument("--quiet", action="store_true", help="Suppress verbose execution trace logs.")

    # `verify` subcommand
    verify_parser = subparsers.add_parser("verify", help="Run independent verification checks on workspace.")
    verify_parser.add_argument("--repo", type=str, default=".", help="Target repository directory path.")
    verify_parser.add_argument("--test-cmd", type=str, default=None, help="Custom test command.")

    args = parser.parse_args()

    if getattr(args, "gui", False) or args.command == "gui":
        from codepilot.gui import start_gui_server
        repo_arg = getattr(args, "repo", ".")
        port_arg = getattr(args, "port", 8080)
        start_gui_server(repo_path=repo_arg, port=port_arg)
        sys.exit(0)

    # Default to interactive chat shell if no command provided
    if not args.command or args.command == "chat":
        repo_arg = getattr(args, "repo", ".")
        provider_arg = getattr(args, "provider", default_p)
        model_arg = getattr(args, "model", None)
        shell = InteractiveShell(initial_repo=repo_arg, provider=provider_arg, model_name=model_arg)
        shell.start()
        sys.exit(0)

    if args.command == "fix":
        repo_path = Path(args.repo).resolve()
        if not repo_path.exists():
            print(f"Error: Target repository path '{repo_path}' does not exist.", file=sys.stderr)
            sys.exit(1)

        print("==========================================================================")
        print(f"AI CODING HARNESS RUN — Task: {args.issue}")
        print(f"Target Repository: {repo_path}")
        print(f"LLM Provider: {args.provider}")
        print("==========================================================================")

        agent_loop = AutonomousAgentLoop(
            workspace_root=str(repo_path),
            provider=args.provider,
            model_name=args.model,
            max_retries=args.max_retries,
            test_command=args.test_cmd,
            verbose=not args.quiet
        )

        report = agent_loop.run(task_description=args.issue)

        print("\n==========================================================================")
        print("EVIDENCE & TELEMETRY SUMMARY")
        print("==========================================================================")
        print(f"Status: {report['status']}")
        metrics = report["telemetry"]
        print(f"Runtime: {metrics['runtime_seconds']}s")
        print(f"Model Interactions: {metrics['model_calls']}")
        print(f"Tool Executions: {metrics['tool_calls']}")
        print(f"Retries / Recovery Steps: {metrics['retry_count']}")
        print(f"Files Modified: {', '.join(report['verification']['files_modified']) or 'None'}")
        print(f"Verification Reason: {report['verification']['reason']}")
        print("==========================================================================")

        if report["status"] == "VERIFIED_SUCCESS":
            sys.exit(0)
        else:
            sys.exit(1)

    elif args.command == "verify":
        repo_path = Path(args.repo).resolve()
        safety = SafetyPolicy(workspace_root=str(repo_path))
        runner = VerificationRunner(safety)
        res = runner.verify(test_command=args.test_cmd)

        print(f"Verification Result: {'PASS' if res.passed else 'FAIL'}")
        print(f"Reason: {res.reason}")
        print(f"Files Modified: {res.files_modified}")
        if res.passed:
            sys.exit(0)
        else:
            sys.exit(1)


if __name__ == "__main__":
    main()
