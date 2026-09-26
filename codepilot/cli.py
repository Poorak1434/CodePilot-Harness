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
    
    # Determine default provider
    default_p = os.getenv("DEFAULT_PROVIDER") or os.getenv("CODEPILOT_PROVIDER") or "ollama"

    parser = argparse.ArgumentParser(
        prog="codepilot",
        description=f"CodePilot v{__version__} - Autonomous Multi-Agent Software Engineering Harness"
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
    chat_parser.add_argument("--provider", type=str, default=default_p, choices=["ollama", "groq", "gemini", "openai", "anthropic", "mock"], help="LLM Provider.")
    chat_parser.add_argument("--model", type=str, default=None, help="Specific model name.")

    # `run` subcommand
    run_parser = subparsers.add_parser("run", help="Run a natural language prompt directly.")
    run_parser.add_argument("prompt", type=str, help="Prompt or task instruction.")
    run_parser.add_argument("--repo", type=str, default=".", help="Target repository directory path.")
    run_parser.add_argument("--provider", type=str, default=default_p, choices=["ollama", "groq", "gemini", "openai", "anthropic", "mock"], help="LLM Provider.")
    run_parser.add_argument("--model", type=str, default=None, help="Specific model name.")

    # `audit` subcommand
    audit_parser = subparsers.add_parser("audit", help="Run Security Auditor on the repository.")
    audit_parser.add_argument("--repo", type=str, default=".", help="Target repository directory path.")
    audit_parser.add_argument("--provider", type=str, default=default_p, help="LLM Provider.")
    audit_parser.add_argument("--model", type=str, default=None, help="Specific model name.")

    # `quality` subcommand
    quality_parser = subparsers.add_parser("quality", help="Run Code Quality and Duplication Agent.")
    quality_parser.add_argument("--repo", type=str, default=".", help="Target repository directory path.")
    quality_parser.add_argument("--provider", type=str, default=default_p, help="LLM Provider.")
    quality_parser.add_argument("--model", type=str, default=None, help="Specific model name.")

    # `architecture` subcommand
    arch_parser = subparsers.add_parser("architecture", help="Generate technical architecture and Mermaid diagrams.")
    arch_parser.add_argument("--repo", type=str, default=".", help="Target repository directory path.")
    arch_parser.add_argument("--provider", type=str, default=default_p, help="LLM Provider.")
    arch_parser.add_argument("--model", type=str, default=None, help="Specific model name.")

    # `demo` subcommand
    demo_parser = subparsers.add_parser("demo", help="Generate project showcase storyboard, narration, and playable MP4 video.")
    demo_parser.add_argument("--repo", type=str, default=".", help="Target repository directory path.")
    demo_parser.add_argument("--provider", type=str, default=default_p, help="LLM Provider.")
    demo_parser.add_argument("--model", type=str, default=None, help="Specific model name.")

    # `workflow` subcommand
    workflow_parser = subparsers.add_parser("workflow", help="Run full multi-agent pipeline (Security + Quality + Architecture + Demo Video).")
    workflow_parser.add_argument("--repo", type=str, default=".", help="Target repository directory path.")
    workflow_parser.add_argument("--provider", type=str, default=default_p, help="LLM Provider.")
    workflow_parser.add_argument("--model", type=str, default=None, help="Specific model name.")

    # `fix` subcommand
    fix_parser = subparsers.add_parser("fix", help="Execute autonomous coding loop for a single task.")
    fix_parser.add_argument("--repo", type=str, default=".", help="Target repository directory path.")
    fix_parser.add_argument("--issue", type=str, required=True, help="Task or issue description.")
    fix_parser.add_argument("--provider", type=str, default=default_p, choices=["ollama", "groq", "gemini", "openai", "anthropic", "mock"], help="LLM Provider.")
    fix_parser.add_argument("--model", type=str, default=None, help="Specific model name.")
    fix_parser.add_argument("--max-retries", type=int, default=5, help="Maximum number of retry attempts.")
    fix_parser.add_argument("--test-cmd", type=str, default=None, help="Custom test command.")
    fix_parser.add_argument("--quiet", action="store_true", help="Suppress verbose execution trace logs.")

    # `verify` subcommand
    verify_parser = subparsers.add_parser("verify", help="Run independent verification checks on workspace.")
    verify_parser.add_argument("--repo", type=str, default=".", help="Target repository directory path.")
    verify_parser.add_argument("--test-cmd", type=str, default=None, help="Custom test command.")

    # `doctor` subcommand
    doctor_parser = subparsers.add_parser("doctor", help="Run diagnostic health checks on configured LLM provider.")
    doctor_parser.add_argument("--provider", type=str, default=None, help="LLM Provider.")
    doctor_parser.add_argument("--model", type=str, default=None, help="Specific model name.")

    args = parser.parse_args()

    if args.command == "doctor":
        from codepilot.llm.doctor import CodePilotDoctor
        doc = CodePilotDoctor(provider=args.provider, model=args.model)
        healthy = doc.print_report()
        sys.exit(0 if healthy else 1)

    if getattr(args, "gui", False) or args.command == "gui":
        from codepilot.gui import start_gui_server
        repo_arg = getattr(args, "repo", ".")
        port_arg = getattr(args, "port", 8080)
        start_gui_server(repo_path=repo_arg, port=port_arg)
        sys.exit(0)

    # Multi-Agent Subcommands
    if args.command in ("audit", "quality", "architecture", "demo", "workflow", "run"):
        repo_path = Path(args.repo).resolve()
        prompt_map = {
            "audit": "Audit this repository for security vulnerabilities and produce a detailed audit report.",
            "quality": "Scan this repository for code duplication, dead code, and maintainability refactoring opportunities.",
            "architecture": "Inspect the complete repository structure and generate technical architecture documentation and Mermaid diagrams.",
            "demo": "Generate a complete project showcase demo video for hackathon judges.",
            "workflow": "Execute full multi-agent workflow: audit security, check code quality, generate architecture documentation, and compile demo video."
        }
        task_prompt = getattr(args, "prompt", None) or prompt_map[args.command]

        print("=" * 70)
        print(f"🚀 CODEPILOT MULTI-AGENT HARNESS — {args.command.upper()}")
        print(f" • Repository : {repo_path}")
        print(f" • Provider   : {args.provider}")
        print(f" • Task       : {task_prompt}")
        print("=" * 70 + "\n")

        agent_loop = AutonomousAgentLoop(
            workspace_root=str(repo_path),
            provider=args.provider,
            model_name=args.model,
            verbose=True
        )
        orch = agent_loop.orchestrator

        if args.command == "audit":
            tool_res = orch.tools.dispatch("run_security_audit", {"objective": task_prompt})
            print(f"\n{tool_res.output}\n")
            artifacts = tool_res.metadata.get("artifacts", {})
            if artifacts:
                print("📦 Generated Artifacts:")
                for k, v in artifacts.items():
                    print(f" • {k} -> {v}")
            sys.exit(0 if tool_res.success else 1)

        elif args.command == "quality":
            tool_res = orch.tools.dispatch("run_code_quality_check", {"objective": task_prompt})
            print(f"\n{tool_res.output}\n")
            artifacts = tool_res.metadata.get("artifacts", {})
            if artifacts:
                print("📦 Generated Artifacts:")
                for k, v in artifacts.items():
                    print(f" • {k} -> {v}")
            sys.exit(0 if tool_res.success else 1)

        elif args.command == "architecture":
            tool_res = orch.tools.dispatch("generate_architecture_docs", {"objective": task_prompt})
            print(f"\n{tool_res.output}\n")
            artifacts = tool_res.metadata.get("artifacts", {})
            if artifacts:
                print("📦 Generated Artifacts:")
                for k, v in artifacts.items():
                    print(f" • {k} -> {v}")
            sys.exit(0 if tool_res.success else 1)

        elif args.command == "demo":
            tool_res = orch.tools.dispatch("generate_demo_video", {"objective": task_prompt})
            print(f"\n{tool_res.output}\n")
            artifacts = tool_res.metadata.get("artifacts", {})
            if artifacts:
                print("📦 Generated Artifacts:")
                for k, v in artifacts.items():
                    print(f" • {k} -> {v}")
            sys.exit(0 if tool_res.success else 1)

        elif args.command == "workflow":
            tool_res = orch.tools.dispatch("run_multi_agent_workflow", {"include_video": True})
            print(f"\n{tool_res.output}\n")
            sys.exit(0 if tool_res.success else 1)

        else:
            # `run` subcommand: conversational or LLM-driven execution
            report = agent_loop.run(task_description=task_prompt)

            print("\n" + "=" * 70)
            print("📊 EXECUTION SUMMARY")
            print("=" * 70)
            print(f"Status: {report['status']}")
            thought_out = report.get("last_thought") or report.get("response_text", "")
            if thought_out:
                print(f"\nResponse / Thought:\n{thought_out}\n")

            artifacts = report.get("artifacts", {})
            if artifacts:
                print("📦 Generated Artifacts:")
                for name, path_str in sorted(artifacts.items()):
                    print(f" • {name} -> {path_str}")

            sys.exit(0 if report["status"] in ("SUCCESS", "VERIFIED_SUCCESS") else 1)

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
