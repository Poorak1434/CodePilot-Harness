"""
Comprehensive tests for CodePilot Multi-Agent Architecture.
Validates Security Auditor, Code Quality, Architecture Agent, Demo Video Agent,
Concurrent Agent Execution, and Conflict Resolution.
"""
import pytest
import os
import shutil
from pathlib import Path
from codepilot.safety.policy import SafetyPolicy
from codepilot.llm.adapter import LLMAdapter
from codepilot.agent.base_agent import AgentTask, AgentResult
from codepilot.agent.security_agent import SecurityAuditorAgent
from codepilot.agent.quality_agent import CodeQualityAgent
from codepilot.agent.architecture_agent import ArchitectureAgent
from codepilot.agent.video_agent import DemoVideoAgent
from codepilot.agent.orchestrator import AgentOrchestrator


class TestMultiAgentSystem:
    @pytest.fixture(autouse=True)
    def setup_teardown(self, tmp_path):
        self.workspace = tmp_path / "test_workspace"
        self.workspace.mkdir()
        self.safety = SafetyPolicy(workspace_root=str(self.workspace))
        self.llm = LLMAdapter(provider="mock")

        # Create dummy project structure
        src_dir = self.workspace / "codepilot"
        src_dir.mkdir()
        (src_dir / "__init__.py").write_text("# init", encoding="utf-8")
        (src_dir / "app.py").write_text(
            "import os\n"
            "def calculate(a, b):\n"
            "    # logic block\n"
            "    x = a * 2\n"
            "    y = b * 2\n"
            "    z = x + y\n"
            "    return z\n"
            "def unused_func():\n"
            "    return 42\n",
            encoding="utf-8"
        )
        (src_dir / "utils.py").write_text(
            "from codepilot.app import calculate\n"
            "def duplicate_calc(a, b):\n"
            "    # logic block\n"
            "    x = a * 2\n"
            "    y = b * 2\n"
            "    z = x + y\n"
            "    return z\n",
            encoding="utf-8"
        )

        yield

        # Cleanup
        artifacts = self.workspace / "artifacts"
        if artifacts.exists():
            shutil.rmtree(artifacts)

    def test_security_auditor_agent(self):
        # Introduce a dummy vulnerable file
        vuln_file = self.workspace / "codepilot" / "insecure.py"
        vuln_file.write_text(
            "import subprocess\n"
            "def run_bad(cmd):\n"
            "    return subprocess.Popen(cmd, shell=True)\n"
            "def run_eval(code):\n"
            "    return eval(code)\n",
            encoding="utf-8"
        )

        sec_agent = SecurityAuditorAgent(str(self.workspace), self.llm, self.safety)
        task = AgentTask(task_id="sec-1", agent_id=sec_agent.agent_id, objective="Audit workspace")
        res = sec_agent.execute(task)

        assert res.status in ("SUCCESS", "PARTIAL")
        assert len(res.findings) >= 2

        # Verify finding structure
        f = res.findings[0]
        assert "finding_id" in f
        assert "affected_file" in f
        assert "severity" in f
        assert "rationale" in f
        assert "suggested_remediation" in f
        assert "verification_status" in f

        # Verify artifacts
        assert Path(res.artifacts["security_findings_json"]).exists()
        assert Path(res.artifacts["security_audit_md"]).exists()

    def test_code_quality_agent(self):
        qual_agent = CodeQualityAgent(str(self.workspace), self.llm, self.safety)
        task = AgentTask(task_id="qual-1", agent_id=qual_agent.agent_id, objective="Inspect quality")
        res = qual_agent.execute(task)

        assert res.status in ("SUCCESS", "PARTIAL")
        assert len(res.findings) >= 1

        # Check for duplication or dead code findings
        types = [f.get("type") for f in res.findings]
        assert any("DUPLICATE" in t or "UNUSED" in t for t in types)

        # Verify artifacts
        assert Path(res.artifacts["duplication_findings_json"]).exists()
        assert Path(res.artifacts["code_quality_report_md"]).exists()

    def test_architecture_agent(self):
        arch_agent = ArchitectureAgent(str(self.workspace), self.llm, self.safety)
        task = AgentTask(task_id="arch-1", agent_id=arch_agent.agent_id, objective="Generate architecture")
        res = arch_agent.execute(task)

        assert res.status == "SUCCESS"
        assert "architecture.md" in res.artifacts
        assert "system_diagram.md" in res.artifacts
        assert "module_dependency_graph.md" in res.artifacts
        assert "execution_flow.md" in res.artifacts
        assert "agent_interaction.md" in res.artifacts

        for filename, filepath in res.artifacts.items():
            p = Path(filepath)
            assert p.exists()
            assert p.stat().st_size > 0

    def test_demo_video_agent(self):
        vid_agent = DemoVideoAgent(str(self.workspace), self.llm, self.safety)
        task = AgentTask(task_id="vid-1", agent_id=vid_agent.agent_id, objective="Generate demo video")
        res = vid_agent.execute(task)

        assert res.status == "SUCCESS"
        assert "storyboard_md" in res.artifacts
        assert "narration_md" in res.artifacts
        assert "demo_mp4" in res.artifacts

        mp4_path = Path(res.artifacts["demo_mp4"])
        assert mp4_path.exists()
        assert mp4_path.stat().st_size > 0

    def test_orchestrator_concurrent_agents(self):
        orch = AgentOrchestrator(workspace_root=str(self.workspace), provider="mock")
        agents_to_run = ["security_auditor", "code_quality", "architecture_agent"]

        results = orch.run_concurrent_agents(agents_to_run, "Parallel repository inspection")

        assert len(results) == 3
        for aid in agents_to_run:
            assert aid in results
            assert results[aid].status in ("SUCCESS", "PARTIAL")

    def test_orchestrator_conflict_resolution(self):
        orch = AgentOrchestrator(workspace_root=str(self.workspace), provider="mock")

        mixed_findings = [
            {"finding_id": "QUAL-001", "type": "DUPLICATE_CODE_BLOCK", "description": "Duplicate logic"},
            {"finding_id": "SEC-002", "severity": "MEDIUM", "vulnerability": "Medium risk"},
            {"finding_id": "SEC-001", "severity": "CRITICAL", "vulnerability": "Remote Code Execution"},
            {"finding_id": "SEC-003", "severity": "HIGH", "vulnerability": "Command Injection"}
        ]

        resolved = orch.resolve_conflicts(mixed_findings)
        assert resolved[0]["finding_id"] == "SEC-001"  # CRITICAL first
        assert resolved[1]["finding_id"] == "SEC-003"  # HIGH second
        assert resolved[2]["finding_id"] == "SEC-002"  # MEDIUM third
