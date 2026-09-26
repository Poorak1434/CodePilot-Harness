"""
OpenHarness Integration and Conformance Tests.
Validates the Autonomous Machine Provider Protocol (JSON-RPC 2.0 + SSE streaming)
and the Domain-Specific Harness (DSH) registry and execution engine.
"""
import pytest
import time
from pathlib import Path
from codepilot.openharness import (
    start_openharness_provider_server,
    OpenHarnessClient,
    DSHRegistry,
    ProviderEvent,
)


@pytest.fixture(scope="module")
def provider_server(tmp_path_factory):
    workspace = tmp_path_factory.mktemp("oh_workspace")
    port = 4519
    server = start_openharness_provider_server(
        workspace_root=str(workspace),
        port=port,
        auth_token="test-secret-token",
        blocking=False,
    )
    time.sleep(0.5)
    yield f"http://localhost:{port}"
    server.server_close()


class TestOpenHarnessIntegration:
    def test_openharness_agent_list(self, provider_server):
        client = OpenHarnessClient(provider_server, token="test-secret-token")
        agents = client.list_agents()
        assert len(agents) >= 6
        agent_ids = {a["id"] for a in agents}
        assert "central-orchestrator" in agent_ids
        assert "security-auditor" in agent_ids
        assert "code-quality" in agent_ids
        assert "architecture-agent" in agent_ids
        assert "video-demo" in agent_ids
        assert "dsh-polymath" in agent_ids

    def test_openharness_agent_send_sse_stream(self, provider_server):
        client = OpenHarnessClient(provider_server, token="test-secret-token")
        events = list(client.send_message("security-auditor", "Scan current workspace for vulnerabilities"))

        assert len(events) >= 4
        kinds = [ev.kind for ev in events]
        assert "turn_started" in kinds
        assert "user_message" in kinds
        assert "turn_completed" in kinds

        # Verify last event is terminal
        assert kinds[-1] == "turn_completed"

    def test_openharness_agent_history(self, provider_server):
        client = OpenHarnessClient(provider_server, token="test-secret-token")
        # History should contain events from previous turn
        history = client.get_history("security-auditor")
        assert len(history) >= 4
        assert any(e.get("kind") == "turn_started" for e in history)
        assert any(e.get("kind") == "turn_completed" for e in history)

    def test_openharness_agent_recap(self, provider_server):
        client = OpenHarnessClient(provider_server, token="test-secret-token")
        recap = client.get_recap("security-auditor")
        assert recap is not None
        assert "Audited" in recap or "vulnerabilit" in recap.lower()

    def test_openharness_agent_crud(self, provider_server):
        client = OpenHarnessClient(provider_server, token="test-secret-token")
        
        # Create
        created = client.create_agent("Custom Tester Agent", "Assigned to test OpenHarness provider")
        agent_id = created["id"]
        assert created["name"] == "Custom Tester Agent"

        # Rename
        renamed = client.rename_agent(agent_id, "Renamed Tester Agent")
        assert renamed["name"] == "Renamed Tester Agent"

        # Delete
        deleted = client.delete_agent(agent_id)
        assert deleted is True

    def test_openharness_authentication_rejection(self, provider_server):
        # Client without token should be rejected with unauthenticated error
        bad_client = OpenHarnessClient(provider_server, token="wrong-invalid-token")
        with pytest.raises(RuntimeError) as exc_info:
            bad_client.list_agents()
        assert "unauthenticated" in str(exc_info.value)

    def test_openharness_dsh_registry(self, tmp_path):
        registry = DSHRegistry(str(tmp_path))
        harnesses = registry.list_all()
        assert len(harnesses) >= 5

        # Test Blender 3D generation
        b_res = registry.execute_harness("blender", "Create ribbon lamp")
        assert b_res["status"] == "SUCCESS"
        assert Path(b_res["artifacts"]["3d_mesh"]).exists()
        assert Path(b_res["artifacts"]["blender_script"]).exists()

        # Test CircuitJS generation
        c_res = registry.execute_harness("circuitjs", "Design 1kHz filter")
        assert c_res["status"] == "SUCCESS"
        assert Path(c_res["artifacts"]["circuit_netlist"]).exists()

        # Test MuJoCo robotics generation
        m_res = registry.execute_harness("mujoco", "Model robot arm")
        assert m_res["status"] == "SUCCESS"
        assert Path(m_res["artifacts"]["mjcf_model"]).exists()

        # Test Audio synthesis
        s_res = registry.execute_harness("music-studio", "Synthesize synth arpeggio")
        assert s_res["status"] == "SUCCESS"
        assert Path(s_res["artifacts"]["audio_wav"]).exists()
