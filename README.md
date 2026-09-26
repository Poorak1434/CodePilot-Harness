# 🚀 CodePilot AI Coding Harness

> **Autonomous, Production-Grade AI Software Engineering & Debugging Agent CLI**  
> Inspired by top-tier agentic systems (Antigravity & Claude Code).

---

## 🌟 Overview

**CodePilot** is an autonomous AI coding agent harness that enables foundation models (Gemini, OpenAI, Anthropic, Ollama, and Mock) to understand complex software engineering tasks, navigate repositories, execute shell commands, edit files safely, automatically recover from errors, and produce independently verified code changes.

---

## 🎯 Key Capabilities

- 🎨 **CodePilot Web Studio GUI Interface**: Modern glassmorphic Web UI dashboard (`codepilot gui` / `codepilot --gui`) featuring real-time log streaming, provider management, telemetry tracking, rendered code inspector, and one-click remote repo cloner!
- 🤖 **Multi-Model Provider Adapter**: Unified support for Google Gemini (`gemini-2.5-flash`), OpenAI (`gpt-4o-mini`), Anthropic (`claude-3-5-sonnet`), Ollama on-device local models (`llama3`), and Zero-Shot Dynamic Code Intelligence fallback.
- ⚡ **Interactive REPL Shell & Slash Commands**: Full-featured interactive CLI with shortcuts:
  - `/gemini [KEY]`, `/openai [KEY]`, `/anthropic [KEY]`, `/ollama`, `/mock`
  - `/paste` (paste multi-line snippets for auto-fixing)
  - `/repo <path>` (switch target repository context)
  - `/key <key>` (manage API keys on-the-fly)
  - `/verify` (run independent verification pipeline)
  - `/diff` (inspect live uncommitted git diff)
  - `/status` (check git repository status)
- 📊 **Real-Time Token Usage & Telemetry**:
  - Live token monitoring (prompt, completion, and total tokens per turn).
  - Complete execution telemetry reporting saved to `EVIDENCE_REPORT.json` & `EVIDENCE_REPORT.md`.
- 🛡️ **Keyless Provider Fallback Engine**:
  - If a primary provider lacks an API key or encounters quota issues, CodePilot automatically triggers an alternative fallback provider without crashing execution.
- 🔄 **Autonomous State Machine & Recovery**:
  - Bounded 5-retry loop featuring failure classification (`TEST_FAILURE`, `SYNTAX_ERROR`, `IMPORT_ERROR`, `LOGIC_FAILURE`), targeted recovery hints, and re-planning.
- 🔒 **Safety & Security Scoping**:
  - Workspace path isolation and blocklists against destructive commands (`rm -rf /`, `sudo`, `dd`, `chmod`).
- 🛠️ **Independent Verification Runner**:
  - Runs targeted test suites (`pytest` / `unittest` / script execution) and git diff validation before declaring completion.

---

## 🚀 Quickstart

### 1. Installation

```bash
# Clone repository
git clone https://github.com/Poorak1434/CodePilot-Harness.git
cd CodePilot-Harness

# Create & activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies in editable mode
pip install -e .
```

### 2. Launch Interactive Mode or Web Studio GUI

```bash
# Launch Terminal Interactive REPL Mode
codepilot

# Launch CodePilot Web Studio GUI Dashboard
codepilot gui
```

### 3. Usage Examples

#### 💬 Interactive Chat & Provider Switching
```bash
codepilot [AI Harness Hackathon]> /gemini AIzaSy...
Provider set to GEMINI and API Key updated.

codepilot [AI Harness Hackathon]> hi
▶ EXECUTING TASK: hi
...
STATUS: VERIFIED_SUCCESS
```

#### 📄 Multi-Line Code Paste & Snippet Debugging
```bash
codepilot [AI Harness Hackathon]> /paste
[Entering multi-line code mode. Type 'END' or '```' on a new line to finish]
... import mathh
... total_users = "10"
... def greet_user(name, age):
...     return "Hello " + name + ", you are " + age + " years old!"
... END

✨ FINAL CORRECTED CODE OUTPUT:
import math

total_users = 10

def greet_user(name, age):
    return f"Hello {name}, you are {age} years old!"
...
```

#### 🛠️ CLI Direct Execution
```bash
# Execute repository task
codepilot fix "Fix discount calculation formula in math_utils.py"

# Run independent verification
codepilot verify
```

---

## 🧪 Running the Test Suite

CodePilot includes 8 unit & integration tests covering safety policies, tool routers, context compression, failure recovery, and verification reporting:

```bash
pytest -v tests/
```

Output:
```
============================= test session starts ==============================
tests/test_context.py::TestContextManager::test_context_retrieval_and_compression PASSED [ 12%]
tests/test_e2e.py::TestEndToEndHarness::test_full_autonomous_loop_with_recovery PASSED [ 25%]
tests/test_recovery.py::TestRecoveryEngine::test_failure_detection_and_classification PASSED [ 37%]
tests/test_recovery.py::TestRecoveryEngine::test_syntax_error_classification PASSED [ 50%]
tests/test_safety.py::TestSafetyPolicy::test_command_validation PASSED   [ 62%]
tests/test_safety.py::TestSafetyPolicy::test_path_validation PASSED      [ 75%]
tests/test_tools.py::TestTools::test_tool_router_and_filesystem_tools PASSED [ 87%]
tests/test_verification.py::TestVerification::test_verification_runner_and_evidence PASSED [100%]
============================== 8 passed in 0.35s ===============================
```

---

## 📐 System Architecture

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for detailed technical specifications on component design, state machine flow, failure classification, and verification runner design.

---

## 📜 License

MIT License © 2026 CodePilot Team
