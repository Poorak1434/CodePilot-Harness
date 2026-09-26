"""
Autonomous Agent Loop executing the unified LLM-first agent architecture.
Supports both Conversational Mode and Agent / Coding Mode naturally driven by model intelligence.
"""
from typing import Dict, Any, Optional, List
from codepilot.agent.state import TaskState, AgentPhase
from codepilot.agent.planner import Planner
from codepilot.agent.orchestrator import AgentOrchestrator
from codepilot.recovery import FailureDetector, FailureClassifier, RecoveryStrategy
from codepilot.verification import EvidenceReporter, VerificationResult
from codepilot.llm.prompts import SYSTEM_PROMPT


class AutonomousAgentLoop:
    def __init__(
        self,
        workspace_root: str,
        provider: str = "gemini",
        model_name: Optional[str] = None,
        max_retries: int = 5,
        test_command: Optional[str] = None,
        verbose: bool = True
    ):
        self.orchestrator = AgentOrchestrator(
            workspace_root=workspace_root,
            provider=provider,
            model_name=model_name,
            test_command=test_command,
            verbose=verbose
        )
        self.max_retries = max_retries
        self.test_command = test_command

    def run(self, task_description: str, history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Executes unified agent loop.
        Naturally supports Conversational Mode and Agent / Coding Mode.
        """
        state = TaskState(task_description=task_description, max_retries=self.max_retries)
        orch = self.orchestrator
        logger = orch.logger
        metrics = orch.metrics
        effective_history = history or []

        logger.log(f"User message received: '{task_description}'", {"workspace": str(orch.safety.workspace_root)})

        # Initialize workspace context for turn
        orch.context.initialize_task(task_description)

        registered_tools = set(orch.tools._tools.keys())
        last_verification: Optional[VerificationResult] = None
        has_executed_tools = False

        while state.can_continue():
            state.increment_step()
            state.phase = AgentPhase.ACT

            user_context = orch.context.get_formatted_context()

            # Invoke LLM Provider
            logger.log(f"Model invocation (Turn #{state.step_count}, Retry #{state.retry_count}).")
            model_resp = orch.llm.generate_response(
                system_prompt=SYSTEM_PROMPT,
                user_context=user_context,
                history=effective_history
            )

            metrics.record_model_call(
                prompt_tok=orch.llm.last_prompt_tokens,
                comp_tok=orch.llm.last_completion_tokens
            )

            # 1. Handle Provider Errors (Satisfying TEST 7)
            if model_resp.get("_api_error"):
                err_thought = model_resp.get("thought", "LLM Provider Error")
                logger.log(f"Provider Error: {err_thought}")
                return {
                    "status": "PROVIDER_ERROR",
                    "telemetry": metrics.summary(),
                    "verification": {"passed": False, "reason": err_thought, "files_modified": []},
                    "last_thought": err_thought,
                    "is_conversational": True,
                    "response_text": err_thought
                }

            thought = model_resp.get("thought", "")
            tool_call = model_resp.get("tool_call") or {}
            plan = model_resp.get("plan", [])

            if thought:
                logger.log(f"AI Reasoning: {thought}")

            if plan:
                orch.context.current_plan = plan

            tool_name = tool_call.get("name") if isinstance(tool_call, dict) else None
            tool_args = tool_call.get("arguments", {}) if isinstance(tool_call, dict) else {}

            # 2. Check for Completion or Conversational Response (Step 1 without tools)
            if not tool_name or tool_name == "done" or tool_name not in registered_tools:
                # If model issued done on step 1 without calling any tools, this is CONVERSATIONAL MODE!
                if not has_executed_tools and state.step_count == 1:
                    logger.log("Direct conversational response generated (No tool calls required).")
                    return {
                        "status": "SUCCESS",
                        "telemetry": metrics.summary(),
                        "verification": {"passed": True, "reason": "Conversational response", "files_modified": []},
                        "last_thought": thought,
                        "is_conversational": True,
                        "response_text": thought
                    }

                # Model declared done after tool execution
                state.phase = AgentPhase.VERIFY
                logger.log("Model declared completion of agent task. Running independent verification.")
                verification_res = orch.verification.verify(test_command=self.test_command)
                last_verification = verification_res

                if verification_res.passed:
                    logger.log("Verification PASSED.")
                    state.phase = AgentPhase.DONE
                    state.is_completed = True
                    break
                else:
                    # Model claimed completion but verification failed -> retry loop
                    state.phase = AgentPhase.DIAGNOSE
                    logger.log(f"Verification FAILED: {verification_res.reason}")
                    classification = FailureClassifier.classify(verification_res.reason, verification_res.test_output)
                    recovery_hint = RecoveryStrategy.generate_hint(classification)

                    orch.context.record_failure({
                        "attempt": state.retry_count + 1,
                        "type": classification["category"],
                        "output": f"{verification_res.reason}\n{verification_res.test_output[:1000]}"
                    })

                    state.increment_retry()
                    metrics.record_retry()
                    state.phase = AgentPhase.REPLAN
                    logger.log(f"Failure analyzed. Re-plan initiated: {recovery_hint}")
                    orch.context.current_plan = Planner.adjust_plan_for_failure(orch.context.current_plan, recovery_hint)
                    state.phase = AgentPhase.RETRY
                    continue

            # 3. Execute Tool Action (Agent / Coding Mode)
            has_executed_tools = True
            logger.log(f"Tool action executed: '{tool_name}' with args {tool_args}.")
            tool_res = orch.execute_tool_call(tool_name, tool_args)

            # Observe & Record Result into context
            state.phase = AgentPhase.OBSERVE
            orch.context.add_history(
                role="user",
                content=f"Tool '{tool_name}' Output:\n{tool_res.output if tool_res.success else tool_res.error}"
            )

            # Handle tool failure
            if FailureDetector.is_failure(tool_res):
                state.phase = AgentPhase.DIAGNOSE
                logger.log(f"Tool failure detected in '{tool_name}'.")
                classification = FailureClassifier.classify(tool_res.error or "", tool_res.output)
                recovery_hint = RecoveryStrategy.generate_hint(classification)

                orch.context.record_failure({
                    "attempt": state.retry_count + 1,
                    "type": classification["category"],
                    "output": tool_res.output or tool_res.error or ""
                })

                state.increment_retry()
                metrics.record_retry()
                state.phase = AgentPhase.REPLAN
                logger.log(f"Failure recovery hint: {recovery_hint}")
                orch.context.current_plan = Planner.adjust_plan_for_failure(orch.context.current_plan, recovery_hint)
                state.phase = AgentPhase.RETRY

        # Generate Evidence Report ONLY if tools were executed or files modified
        if not last_verification:
            last_verification = orch.verification.verify(test_command=self.test_command)

        report = EvidenceReporter.generate_report(
            task_description=task_description,
            verification=last_verification,
            telemetry_metrics=metrics.summary(),
            execution_trace=logger.get_formatted_trace(),
            is_completed=state.is_completed
        )

        report["last_thought"] = thought
        report["is_conversational"] = False

        if has_executed_tools or last_verification.files_modified:
            EvidenceReporter.save_report(report, output_directory=str(orch.safety.workspace_root))
            logger.log("Evidence report saved (EVIDENCE_REPORT.json & EVIDENCE_REPORT.md).")

        return report
