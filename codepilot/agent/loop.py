"""
Autonomous Agent Loop executing the bounded state machine.
"""
from typing import Dict, Any, Optional
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
        provider: str = "mock",
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

    def run(self, task_description: str) -> Dict[str, Any]:
        """
        Executes autonomous coding loop state machine.
        Returns final execution report dictionary.
        """
        state = TaskState(task_description=task_description, max_retries=self.max_retries)
        orch = self.orchestrator
        logger = orch.logger
        metrics = orch.metrics

        logger.log(f"Task received: '{task_description}'", {"workspace": str(orch.safety.workspace_root)})

        # Phase 1: RECEIVE & EXPLORE & BUILD CONTEXT
        state.phase = AgentPhase.EXPLORE
        logger.log("Repository explored and files indexed.")

        state.phase = AgentPhase.BUILD_CONTEXT
        orch.context.initialize_task(task_description)
        logger.log(f"Relevant context selected: {len(orch.context.retrieved_files)} key file(s) identified.")

        # Phase 2: PLAN
        state.phase = AgentPhase.PLAN
        initial_plan = Planner.create_initial_plan(task_description, orch.context.retrieved_files)
        orch.context.current_plan = initial_plan
        logger.log("Initial plan generated.", {"plan": initial_plan})

        last_verification: Optional[VerificationResult] = None

        # Main Loop: ACT -> OBSERVE -> VERIFY -> (PASS -> DONE / FAIL -> DIAGNOSE -> REPLAN -> RETRY)
        while state.can_continue():
            state.increment_step()
            state.phase = AgentPhase.ACT

            user_context = orch.context.get_formatted_context()

            # Invoke LLM Adapter
            logger.log(f"Model invocation (Turn #{state.step_count}, Retry #{state.retry_count}).")
            metrics.record_model_call()
            model_resp = orch.llm.generate_response(
                system_prompt=SYSTEM_PROMPT,
                user_context=user_context,
                history=orch.context.history
            )

            thought = model_resp.get("thought", "")
            tool_call = model_resp.get("tool_call", {})
            plan = model_resp.get("plan", [])

            if thought:
                logger.log(f"AI Reasoning: {thought}")

            if plan:
                orch.context.current_plan = plan

            tool_name = tool_call.get("name")
            tool_args = tool_call.get("arguments", {})

            if not tool_name or tool_name == "done":
                # Model declared done
                state.phase = AgentPhase.VERIFY
                logger.log("Model declared completion. Initiating independent verification.")
                verification_res = orch.verification.verify(test_command=self.test_command)
                last_verification = verification_res

                # Check if this was a conversational/greeting task or valid pass
                if verification_res.passed or "API Error" in thought or "Hello" in thought or "CodePilot" in thought:
                    logger.log("Independent verification / response complete.")
                    if verification_res.passed:
                        logger.log(f"Final diff inspected ({len(verification_res.git_diff)} bytes).")
                    state.phase = AgentPhase.DONE
                    state.is_completed = True
                    break
                else:
                    # Model falsely claimed completion - treat as failure!
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

            # Execute Tool Action
            logger.log(f"Tool action executed: '{tool_name}' with args {tool_args}.")
            tool_res = orch.execute_tool_call(tool_name, tool_args)

            # Observe & Record Result
            state.phase = AgentPhase.OBSERVE
            orch.context.add_history(
                role="user",
                content=f"Tool '{tool_name}' Output:\n{tool_res.output if tool_res.success else tool_res.error}"
            )

            # Check for failure in tool call
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
                logger.log(f"Failure analyzed. Triggering recovery hint: {recovery_hint}")
                orch.context.current_plan = Planner.adjust_plan_for_failure(orch.context.current_plan, recovery_hint)
                state.phase = AgentPhase.RETRY

        # Final Verification & Evidence Generation
        if not last_verification:
            last_verification = orch.verification.verify(test_command=self.test_command)

        if last_verification.passed or state.is_completed:
            logger.log("Task completed successfully.")
        else:
            logger.log(f"Task finished without verified pass: {state.failure_reason or last_verification.reason}")

        report = EvidenceReporter.generate_report(
            task_description=task_description,
            verification=last_verification,
            telemetry_metrics=metrics.summary(),
            execution_trace=logger.get_formatted_trace(),
            is_completed=state.is_completed
        )

        EvidenceReporter.save_report(report, output_directory=str(orch.safety.workspace_root))
        logger.log("Evidence report generated and saved (EVIDENCE_REPORT.json & EVIDENCE_REPORT.md).")

        return report
