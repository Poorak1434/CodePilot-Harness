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
from codepilot.verification import VerificationRunner


def main():
    parser = argparse.ArgumentParser(
        prog="codepilot",
        description="CodePilot - Autonomous Coding-Agent Harness for Foundation Models"
    )
    parser.add_argument("--version", action="version", version=f"CodePilot v{__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # `fix` subcommand
    fix_parser = subparsers.add_parser("fix", help="Execute autonomous coding loop to solve an issue.")
    fix_parser.add_argument("--repo", type=str, default=".", help="Target repository directory path.")
    fix_parser.add_argument("--issue", type=str, required=True, help="Task or issue description.")
    fix_parser.add_argument("--provider", type=str, default="mock", choices=["gemini", "openai", "anthropic", "ollama", "mock"], help="LLM Provider.")
    fix_parser.add_argument("--model", type=str, default=None, help="Specific model name.")
    fix_parser.add_argument("--max-retries", type=int, default=5, help="Maximum number of retry attempts.")
    fix_parser.add_argument("--test-cmd", type=str, default=None, help="Custom test command.")
    fix_parser.add_argument("--quiet", action="store_true", help="Suppress verbose execution trace logs.")

    # `verify` subcommand
    verify_parser = subparsers.add_parser("verify", help="Run independent verification checks on workspace.")
    verify_parser.add_argument("--repo", type=str, default=".", help="Target repository directory path.")
    verify_parser.add_argument("--test-cmd", type=str, default=None, help="Custom test command.")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

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
