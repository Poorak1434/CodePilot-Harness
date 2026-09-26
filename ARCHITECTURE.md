# CodePilot AI Coding Harness - Architecture & Design Specification

## Overview
CodePilot is an autonomous coding-agent harness built around foundation models (OpenAI, Gemini, Anthropic, Ollama, Mock). It provides the engineering infrastructure (orchestration, context retrieval, tool routing, failure recovery, safety, verification, and telemetry) required to reliably complete software engineering tasks on real repositories.

---

## Core System Architecture

```
                               ┌───────────────────────────┐
                               │        CLI Input          │
                               │ issue + repository path   │
                               └─────────────┬─────────────┘
                                             │
                                             ▼
                               ┌───────────────────────────┐
                               │        Agent Loop         │
                               │  (Bounded State Machine)  │
                               └─────────────┬─────────────┘
                                             │
      ┌──────────────────────────────────────┼──────────────────────────────────────┐
      │                                      │                                      │
      ▼                                      ▼                                      ▼
┌──────────────┐                       ┌──────────────┐                       ┌──────────────┐
│ Context Mgr  │◄─────────────────────►│ LLM Adapter  │◄─────────────────────►│ Safety Guard │
│ Retrieval &  │                       │ (Gemini/OAI/ │                       │ Path & Cmd   │
│ Compression  │                       │ Anthr/Mock)  │                       │ Sanity Check │
└──────┬───────┘                       └──────┬───────┘                       └──────┬───────┘
       │                                      │                                      │
       └──────────────────────────────────────┼──────────────────────────────────────┘
                                             │
                                             ▼
                               ┌───────────────────────────┐
                               │       Tool Router         │
                               │ (FS, Terminal, Git, Test) │
                               └─────────────┬─────────────┘
                                             │
               ┌─────────────────────────────┴─────────────────────────────┐
               ▼                                                           ▼
┌───────────────────────────┐                               ┌───────────────────────────┐
│     Recovery Engine       │                               │    Verification Engine    │
│ Classify -> Re-plan       │                               │ Test Check -> Diff        │
│ Retry loop (bounded)      │                               │ Evidence Generation       │
└───────────────────────────┘                               └───────────────────────────┘
```

---

## Component Breakdowns

### 1. Safety Policy (`codepilot/safety/policy.py`)
- **Workspace Scoping**: Prevents tools from accessing or modifying paths outside the target repository root.
- **Command Blocklist**: Blocks destructive commands (`rm -rf /`, `mkfs`, `dd`, `git reset --hard` outside repo, network dangerous scripts).
- **Execution Guardrails**: Enforces process timeouts, stdout/stderr byte limits, and max recursion depth.

### 2. Unified LLM Adapter (`codepilot/llm/adapter.py`)
- Abstract interface for structured JSON output / tool calls across different model APIs:
  - Google Gemini API (`gemini-2.5-flash`, `gemini-1.5-pro`)
  - OpenAI API (`gpt-4o`, `gpt-4o-mini`)
  - Anthropic API (`claude-3-5-sonnet`)
  - Mock Provider (Deterministic replay adapter for zero-cost offline testing & unit tests)

### 3. Tool Suite (`codepilot/tools/`)
- `list_dir(path)`: List directory structure.
- `find_file(pattern)`: Search for files by glob/regex.
- `search_code(query)`: Search file contents for code patterns.
- `read_file(path, start_line, end_line)`: Read file snippet with line numbers.
- `edit_file(path, old_str, new_str)`: Exact pattern replacement or line range replacement.
- `create_file(path, content)`: File creation with directory bootstrapping.
- `run_command(cmd, timeout)`: Safe process execution in target workspace.
- `run_tests(test_command)`: Run pytest/unittest and parse failure tracebacks.
- `git_status()`: Get clean status of target repository.
- `git_diff()`: Get uncommitted changes in git patch format.

### 4. Context & Memory Manager (`codepilot/context/`)
- **Retriever**: Keyword & regex search across repo to build initial context package.
- **Compressor**: Summarizes old tool execution logs and truncates repetitive stderr stack traces.
- **Budget Enforcer**: Restricts total token window passed to model per turn.

### 5. Recovery Engine (`codepilot/recovery/`)
- **Detector**: Catches non-zero exit codes, failed test suites, syntax errors, and missing dependency errors.
- **Classifier**: Categorizes errors into `TEST_FAILURE`, `SYNTAX_ERROR`, `IMPORT_ERROR`, `COMMAND_TIMEOUT`, or `LOGIC_FAILURE`.
- **Strategy & Re-planner**: Feeds formatted failure context back into the agent loop and prompts targeted code adjustments.

### 6. Verification & Evidence Engine (`codepilot/verification/`)
- Verifies task completion independently of model output.
- Executes verification tests.
- Checks git diff for affected files.
- Produces `EVIDENCE_REPORT.json` and human-readable Markdown report containing:
  - Task specification & execution trace
  - Files modified
  - Test execution logs (PASS/FAIL)
  - Final git diff
  - Resource usage & execution timing

### 7. Telemetry & Metrics (`codepilot/telemetry/`)
- Tracks model calls, token counts, tool execution count, retry count, total runtime duration, and files modified.
