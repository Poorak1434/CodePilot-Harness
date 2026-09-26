"""
CodePilot Web Studio & Interactive GUI Server.
Provides a modern glassmorphic Web UI dashboard for executing autonomous coding tasks,
monitoring telemetry, viewing git diffs, managing API keys, and cloning repositories.
"""
import sys
import os
import json
import urllib.parse
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Dict, Any, Optional
import threading

from codepilot import __version__
from codepilot.agent.loop import AutonomousAgentLoop
from codepilot.safety.policy import SafetyPolicy
from codepilot.verification import VerificationRunner
from codepilot.tools.git import GitDiffTool, GitStatusTool


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CodePilot AI Studio v0.1.0</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Fira+Code:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0a0d14;
            --bg-card: rgba(18, 24, 38, 0.75);
            --bg-card-border: rgba(255, 255, 255, 0.08);
            --accent-cyan: #00f2fe;
            --accent-purple: #4facfe;
            --accent-green: #10b981;
            --accent-red: #ef4444;
            --text-main: #f3f4f6;
            --text-sub: #9ca3af;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
        body { background: var(--bg-primary); color: var(--text-main); min-height: 100vh; overflow-x: hidden; }

        .app-container { display: grid; grid-template-columns: 280px 1fr 380px; height: 100vh; }
        
        /* Sidebar */
        .sidebar { background: #07090e; border-right: 1px solid var(--bg-card-border); padding: 24px; display: flex; flex-direction: column; gap: 24px; }
        .logo { font-size: 1.25rem; font-weight: 700; background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; display: flex; align-items: center; gap: 10px; }
        
        .section-title { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1.2px; color: var(--text-sub); margin-bottom: 8px; }
        
        .control-group { display: flex; flex-direction: column; gap: 8px; }
        select, input[type="text"] { background: rgba(255, 255, 255, 0.04); border: 1px solid var(--bg-card-border); border-radius: 8px; color: var(--text-main); padding: 10px 14px; font-size: 0.9rem; outline: none; transition: 0.2s ease; }
        select:focus, input[type="text"]:focus { border-color: var(--accent-cyan); background: rgba(0, 242, 254, 0.05); }

        /* Main Studio Workspace */
        .main-workspace { display: flex; flex-direction: column; border-right: 1px solid var(--bg-card-border); background: radial-gradient(circle at top left, rgba(0, 242, 254, 0.03), transparent 40%); }
        .top-bar { padding: 16px 24px; border-bottom: 1px solid var(--bg-card-border); display: flex; justify-content: space-between; align-items: center; background: rgba(7, 9, 14, 0.6); backdrop-filter: blur(10px); }
        
        .status-badge { display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 600; background: rgba(16, 185, 129, 0.15); color: var(--accent-green); border: 1px solid rgba(16, 185, 129, 0.3); }

        .terminal-container { flex: 1; padding: 24px; overflow-y: auto; display: flex; flex-direction: column; gap: 16px; font-family: 'Fira Code', monospace; }
        .log-line { padding: 12px 16px; border-radius: 8px; background: var(--bg-card); border: 1px solid var(--bg-card-border); font-size: 0.88rem; line-height: 1.6; white-space: pre-wrap; word-break: break-word; }
        .log-step { border-left: 3px solid var(--accent-cyan); }
        .log-tool { border-left: 3px solid var(--accent-purple); }
        .log-success { border-left: 3px solid var(--accent-green); background: rgba(16, 185, 129, 0.08); }

        .input-bar-container { padding: 20px 24px; border-top: 1px solid var(--bg-card-border); background: #07090e; }
        .input-box { display: flex; gap: 12px; }
        .prompt-input { flex: 1; background: rgba(255, 255, 255, 0.05); border: 1px solid var(--bg-card-border); border-radius: 10px; color: var(--text-main); padding: 14px 18px; font-size: 0.95rem; outline: none; }
        .prompt-input:focus { border-color: var(--accent-cyan); }
        
        .btn-run { background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple)); border: none; border-radius: 10px; color: #000; font-weight: 700; padding: 0 24px; cursor: pointer; transition: 0.2s ease; display: flex; align-items: center; gap: 8px; }
        .btn-run:hover { opacity: 0.9; transform: translateY(-1px); }

        /* Output & Diff Inspector Side Panel */
        .inspector-panel { background: #07090e; padding: 24px; display: flex; flex-direction: column; gap: 20px; overflow-y: auto; }
        .output-card { background: var(--bg-card); border: 1px solid var(--bg-card-border); border-radius: 12px; padding: 16px; display: flex; flex-direction: column; gap: 12px; }
        .output-header { font-size: 0.85rem; font-weight: 600; color: var(--accent-cyan); display: flex; justify-content: space-between; align-items: center; }
        .code-view { font-family: 'Fira Code', monospace; font-size: 0.82rem; background: rgba(0, 0, 0, 0.4); padding: 14px; border-radius: 8px; overflow-x: auto; color: #e5e7eb; border: 1px solid rgba(255, 255, 255, 0.05); }

        .metric-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        .metric-box { background: rgba(255, 255, 255, 0.03); border: 1px solid var(--bg-card-border); padding: 10px; border-radius: 8px; text-align: center; }
        .metric-value { font-size: 1.1rem; font-weight: 700; color: var(--accent-cyan); }
        .metric-label { font-size: 0.7rem; color: var(--text-sub); }
    </style>
</head>
<body>
    <div class="app-container">
        <!-- Sidebar Controls -->
        <div class="sidebar">
            <div class="logo">🚀 CodePilot Studio</div>
            
            <div class="control-group">
                <div class="section-title">Model Provider</div>
                <select id="providerSelect" onchange="updateProviderKeyInput()">
                    <option value="gemini" selected>Gemini 2.5 Flash (Cloud Server API)</option>
                    <option value="openai">OpenAI GPT-4o-mini (Cloud Server API)</option>
                    <option value="anthropic">Claude 3.5 Sonnet (Cloud Server API)</option>
                    <option value="ollama">Ollama Local LLM</option>
                    <option value="mock">Zero-Shot Agent Engine</option>
                </select>
            </div>

            <div class="control-group" id="keyContainer">
                <div class="section-title">API Key</div>
                <input type="text" id="apiKeyInput" placeholder="Enter API Key...">
            </div>

            <div class="control-group">
                <div class="section-title">Workspace Repo Path</div>
                <input type="text" id="repoPathInput" value="{{REPO_PATH}}">
            </div>

            <div class="control-group" style="margin-top: 10px;">
                <div class="section-title">Clone & Debug Remote Repo</div>
                <input type="text" id="cloneUrlInput" placeholder="https://github.com/user/repo">
                <button class="btn-run" style="margin-top: 8px; padding: 10px; justify-content: center;" onclick="cloneAndFixRepo()">Clone & Fix Repo</button>
            </div>
        </div>

        <!-- Main Workspace -->
        <div class="main-workspace">
            <div class="top-bar">
                <div style="font-weight: 600; font-size: 0.95rem;">Interactive Execution Workspace</div>
                <div class="status-badge">● Engine Ready</div>
            </div>

            <div class="terminal-container" id="terminalLog">
                <div class="log-line log-step">🚀 CodePilot Autonomous Harness Initialized. Enter any coding task in English, Hindi, or Hinglish below!</div>
            </div>

            <div class="input-bar-container">
                <div class="input-box">
                    <input type="text" id="taskInput" class="prompt-input" placeholder="Ask CodePilot to write code, debug repository issues, or run system tasks..." onkeydown="if(event.key==='Enter') runTask()">
                    <button class="btn-run" onclick="runTask()">Run Task ⚡</button>
                </div>
            </div>
        </div>

        <!-- Right Output Inspector Panel -->
        <div class="inspector-panel">
            <div class="section-title">Telemetry & Execution Output</div>
            
            <div class="metric-grid">
                <div class="metric-box">
                    <div class="metric-value" id="valRuntime">0.0s</div>
                    <div class="metric-label">Runtime</div>
                </div>
                <div class="metric-box">
                    <div class="metric-value" id="valTokens">0 / 0</div>
                    <div class="metric-label">Prompt / Comp Tokens</div>
                </div>
            </div>

            <div class="output-card" id="outputCard" style="display: none;">
                <div class="output-header">
                    <span id="outputTitle">✨ OUTPUT</span>
                    <button style="background: transparent; border: none; color: var(--accent-cyan); cursor: pointer;" onclick="copyCode()">Copy</button>
                </div>
                <pre class="code-view" id="outputCode"></pre>
            </div>
        </div>
    </div>

    <script>
        function updateProviderKeyInput() {
            const provider = document.getElementById('providerSelect').value;
            const container = document.getElementById('keyContainer');
            if (provider === 'mock' || provider === 'ollama') {
                container.style.opacity = '0.4';
            } else {
                container.style.opacity = '1.0';
            }
        }

        async function runTask() {
            const task = document.getElementById('taskInput').value.trim();
            if (!task) return;

            const provider = document.getElementById('providerSelect').value;
            const apiKey = document.getElementById('apiKeyInput').value.trim();
            const repo = document.getElementById('repoPathInput').value.trim();

            appendLog(`▶ EXECUTING TASK: ${task}`, 'log-step');
            document.getElementById('taskInput').value = '';

            try {
                const response = await fetch('/api/task', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ issue: task, provider: provider, apiKey: apiKey, repo: repo })
                });

                const data = await response.json();
                
                if (data.status === 'VERIFIED_SUCCESS' || data.status === 'SUCCESS') {
                    appendLog(`✅ TASK VERIFIED SUCCESSFULLY (${data.telemetry.runtime_seconds}s)`, 'log-success');
                } else {
                    appendLog(`⚠️ TASK COMPLETED: ${data.status}`, 'log-step');
                }

                // Update metrics
                document.getElementById('valRuntime').innerText = data.telemetry.runtime_seconds + 's';
                document.getElementById('valTokens').innerText = (data.telemetry.prompt_tokens || 0) + ' / ' + (data.telemetry.completion_tokens || 0);

                // Update Output Box
                const card = document.getElementById('outputCard');
                const title = document.getElementById('outputTitle');
                const code = document.getElementById('outputCode');

                if (data.output_code) {
                    card.style.display = 'flex';
                    title.innerText = `✨ OUTPUT (${data.output_file || 'Solution'})`;
                    code.innerText = data.output_code;
                } else if (data.last_thought) {
                    card.style.display = 'flex';
                    title.innerText = `✨ REASONING OUTPUT`;
                    code.innerText = data.last_thought;
                }

            } catch (err) {
                appendLog(`❌ Error executing task: ${err.message}`, 'log-line');
            }
        }

        async function cloneAndFixRepo() {
            const url = document.getElementById('cloneUrlInput').value.trim();
            if (!url) return;

            appendLog(`🌐 CLONING REMOTE REPOSITORY: ${url}`, 'log-tool');
            try {
                const res = await fetch('/api/clone', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: url })
                });
                const data = await res.json();
                if (data.success) {
                    appendLog(`✅ REPOSITORY CLONED TO: ${data.target_path}`, 'log-success');
                    document.getElementById('repoPathInput').value = data.target_path;
                } else {
                    appendLog(`❌ Clone failed: ${data.error}`, 'log-line');
                }
            } catch (e) {
                appendLog(`❌ Error cloning: ${e.message}`, 'log-line');
            }
        }

        function appendLog(text, className = 'log-line') {
            const logBox = document.getElementById('terminalLog');
            const div = document.createElement('div');
            div.className = `log-line ${className}`;
            div.innerText = text;
            logBox.appendChild(div);
            logBox.scrollTop = logBox.scrollHeight;
        }

        function copyCode() {
            const code = document.getElementById('outputCode').innerText;
            navigator.clipboard.writeText(code);
            alert('Code copied to clipboard!');
        }
    </script>
</body>
</html>
"""


class CodePilotGUIHandler(BaseHTTPRequestHandler):
    repo_path: str = "."

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            html = HTML_TEMPLATE.replace("{{REPO_PATH}}", str(Path(self.repo_path).resolve()))
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
        elif parsed.path == "/api/status":
            safety = SafetyPolicy(workspace_root=self.repo_path)
            status_tool = GitStatusTool(safety)
            res = status_tool.execute()
            self._send_json({"output": res.output})
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_length)
        
        try:
            payload = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except Exception:
            payload = {}

        if parsed.path == "/api/task":
            issue = payload.get("issue", "")
            provider = payload.get("provider", "mock")
            api_key = payload.get("apiKey")
            repo = payload.get("repo", self.repo_path)

            if api_key:
                os.environ[f"{provider.upper()}_API_KEY"] = api_key

            repo_path = Path(repo).resolve()

            # Clean up stale scratch files before run
            for ks in ("solution.c", "solution.cpp", "solution.py", "solution.js", "solution", "sandbox_snippet.py", "add_numbers.py", "multiply_numbers.py"):
                sp = repo_path / ks
                if sp.exists():
                    try:
                        sp.unlink()
                    except Exception:
                        pass

            agent_loop = AutonomousAgentLoop(
                workspace_root=str(repo_path),
                provider=provider,
                max_retries=5,
                verbose=False
            )

            report = agent_loop.run(task_description=issue)

            # Determine file output for GUI
            task_mod = report.get("telemetry", {}).get("files_modified", [])
            valid_exts = (".py", ".cpp", ".c", ".h", ".hpp", ".js", ".ts", ".java", ".json", ".md")
            src_files = [f for f in task_mod if any(f.endswith(ext) for ext in valid_exts)]
            src_files = [f for f in src_files if not f.endswith("EVIDENCE_REPORT.json") and not f.endswith("EVIDENCE_REPORT.md")]

            output_file = None
            output_code = None

            if src_files:
                output_file = src_files[0]
                mod_path = repo_path / output_file
                if mod_path.is_file():
                    output_code = mod_path.read_text(encoding="utf-8", errors="replace")

            self._send_json({
                "status": report.get("status", "SUCCESS"),
                "telemetry": report.get("telemetry", {}),
                "verification": report.get("verification", {}),
                "last_thought": report.get("last_thought", ""),
                "output_file": output_file,
                "output_code": output_code
            })

        elif parsed.path == "/api/clone":
            url = payload.get("url", "")
            if not url:
                self._send_json({"success": False, "error": "No URL provided"})
                return

            repo_name = url.split("/")[-1].replace(".git", "")
            target_dir = Path(self.repo_path) / "scratch" / repo_name
            target_dir.parent.mkdir(parents=True, exist_ok=True)

            cmd = f"git clone {url} '{target_dir}'"
            ret = os.system(cmd)
            if ret == 0 and target_dir.exists():
                self._send_json({"success": True, "target_path": str(target_dir.resolve())})
            else:
                self._send_json({"success": False, "error": "Git clone failed"})

        else:
            self.send_error(404, "Endpoint not found")

    def _send_json(self, data: Dict[str, Any]):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))


def start_gui_server(repo_path: str = ".", port: int = 8080, open_browser: bool = True):
    CodePilotGUIHandler.repo_path = repo_path
    server_address = ("", port)
    
    try:
        httpd = HTTPServer(server_address, CodePilotGUIHandler)
    except OSError:
        port = port + 1
        httpd = HTTPServer(("", port), CodePilotGUIHandler)

    url = f"http://localhost:{port}"
    print(f"\033[1;32m[🚀 CodePilot Studio GUI Server running at {url}]\033[0m")
    if open_browser:
        webbrowser.open(url)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[Stopping CodePilot GUI Server. Goodbye!]")
        httpd.server_close()
