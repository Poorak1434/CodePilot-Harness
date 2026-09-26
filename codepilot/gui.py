"""
CodePilot Web Studio & Interactive GUI Server.
Provides a modern Antigravity IDE Web UI dashboard for executing autonomous coding tasks,
viewing workspace file tree, editing code files, monitoring terminal output, and running server AI models.
"""
import sys
import os
import json
import urllib.parse
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Dict, Any, List, Optional
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
    <title>AI Harness Hackathon — CodePilot Studio</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Fira+Code:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-window: #181818;
            --bg-sidebar: #181818;
            --bg-editor: #1e1e1e;
            --bg-terminal: #181818;
            --bg-chat: #181818;
            --border-color: #2b2b2b;
            --accent-cyan: #00f2fe;
            --accent-blue: #007acc;
            --accent-green: #10b981;
            --text-main: #cccccc;
            --text-sub: #858585;
            --text-heading: #ffffff;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, sans-serif; }
        html, body { height: 100vh; width: 100vw; overflow: hidden; background: var(--bg-window); color: var(--text-main); display: flex; flex-direction: column; margin: 0; padding: 0; }

        /* Window Header Bar */
        .window-header { height: 35px; min-height: 35px; max-height: 35px; background: #181818; border-bottom: 1px solid var(--border-color); display: flex; align-items: center; justify-content: space-between; padding: 0 16px; font-size: 0.8rem; color: var(--text-sub); user-select: none; flex-shrink: 0; }
        .window-title { flex: 1; text-align: center; font-weight: 500; color: #d4d4d4; }
        .status-pill { background: rgba(16, 185, 129, 0.15); color: var(--accent-green); padding: 3px 10px; border-radius: 12px; font-size: 0.72rem; font-weight: 600; border: 1px solid rgba(16, 185, 129, 0.3); }

        /* Main IDE Layout: Left Explorer (250px) | Middle Editor & Terminal (1fr) | Right Agent Chat (380px) */
        .ide-container { display: grid; grid-template-columns: 250px 1fr 380px; height: calc(100vh - 35px); max-height: calc(100vh - 35px); min-height: 0; overflow: hidden; flex: 1; }

        /* Left Column: Explorer */
        .explorer-panel { background: var(--bg-sidebar); border-right: 1px solid var(--border-color); display: flex; flex-direction: column; font-size: 0.83rem; height: 100%; min-height: 0; overflow: hidden; }
        .panel-header { padding: 10px 16px; font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: var(--text-sub); display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.03); flex-shrink: 0; }
        .repo-title { font-weight: 600; color: #e1e1e1; padding: 8px 16px; display: flex; align-items: center; gap: 6px; border-bottom: 1px solid var(--border-color); flex-shrink: 0; }
        
        .file-tree { flex: 1 1 0%; min-height: 0; overflow-y: auto; padding: 8px 0; font-family: 'Fira Code', monospace; font-size: 0.8rem; }
        .tree-item { padding: 5px 16px; display: flex; align-items: center; gap: 8px; cursor: pointer; color: #cccccc; text-decoration: none; border-left: 2px solid transparent; }
        .tree-item:hover { background: #2a2d2e; }
        .tree-item.active { background: #37373d; color: #ffffff; border-left-color: var(--accent-blue); }
        
        .clone-box { padding: 12px; border-top: 1px solid var(--border-color); background: #141414; display: flex; flex-direction: column; gap: 8px; flex-shrink: 0; margin-top: auto; }
        .clone-box input { background: #252526; border: 1px solid #3c3c3c; border-radius: 4px; padding: 8px 10px; color: #fff; font-size: 0.8rem; outline: none; }
        .btn-clone { background: var(--accent-blue); border: none; border-radius: 4px; color: #fff; font-weight: 600; padding: 8px; font-size: 0.8rem; cursor: pointer; }

        /* Middle Column: Code Editor & Bottom Terminal */
        .editor-container { display: flex; flex-direction: column; border-right: 1px solid var(--border-color); background: var(--bg-editor); height: 100%; min-height: 0; overflow: hidden; }
        
        /* Tabs Bar */
        .tab-bar { height: 35px; min-height: 35px; max-height: 35px; flex-shrink: 0; background: #252526; border-bottom: 1px solid var(--border-color); display: flex; align-items: center; overflow-x: auto; }
        .tab-item { height: 35px; padding: 0 16px; display: flex; align-items: center; gap: 8px; font-size: 0.8rem; color: #969696; background: #2d2d2d; border-right: 1px solid var(--border-color); cursor: pointer; }
        .tab-item.active { background: #1e1e1e; color: #ffffff; border-top: 2px solid var(--accent-blue); }

        /* Code Editor View */
        .editor-workspace { flex: 1 1 0%; min-height: 0; display: flex; overflow: hidden; background: #1e1e1e; position: relative; }
        .line-numbers { padding: 12px 10px; background: #1e1e1e; color: #5a5a5a; font-family: 'Fira Code', monospace; font-size: 0.82rem; text-align: right; user-select: none; border-right: 1px solid rgba(255,255,255,0.03); overflow: hidden; }
        .code-area { flex: 1; padding: 12px; font-family: 'Fira Code', monospace; font-size: 0.85rem; line-height: 1.5; color: #d4d4d4; overflow: auto; outline: none; white-space: pre; border: none; background: transparent; resize: none; }

        /* Integrated Terminal Panel */
        .terminal-panel { height: 180px; min-height: 120px; flex-shrink: 0; background: var(--bg-terminal); border-top: 1px solid var(--border-color); display: flex; flex-direction: column; }
        .terminal-header { height: 32px; min-height: 32px; flex-shrink: 0; padding: 0 16px; background: #252526; border-bottom: 1px solid var(--border-color); display: flex; align-items: center; gap: 16px; font-size: 0.78rem; color: #969696; }
        .term-tab { cursor: pointer; padding: 4px 8px; }
        .term-tab.active { color: #ffffff; font-weight: 600; border-bottom: 2px solid var(--accent-blue); }

        .terminal-body { flex: 1 1 0%; min-height: 0; padding: 12px 16px; font-family: 'Fira Code', monospace; font-size: 0.82rem; line-height: 1.5; overflow-y: auto; color: #cccccc; background: #181818; }
        .term-line { margin-bottom: 4px; word-break: break-all; }
        .term-cmd { color: var(--accent-cyan); font-weight: 600; }
        .term-success { color: var(--accent-green); }

        /* Right Column: Antigravity Agent Chat Sidebar */
        .agent-sidebar { background: var(--bg-chat); display: flex; flex-direction: column; position: relative; overflow: hidden; height: 100%; min-height: 0; }
        .agent-header { padding: 12px 16px; border-bottom: 1px solid var(--border-color); font-weight: 600; font-size: 0.88rem; color: #ffffff; display: flex; justify-content: space-between; align-items: center; flex-shrink: 0; }

        .chat-trajectory { flex: 1 1 0%; min-height: 0; padding: 16px; overflow-y: auto; display: flex; flex-direction: column; gap: 14px; }
        .chat-card { background: #252526; border: 1px solid #3c3c3c; border-radius: 8px; padding: 12px 14px; font-size: 0.84rem; line-height: 1.6; }
        .user-prompt-card { background: rgba(0, 122, 204, 0.15); border-color: rgba(0, 122, 204, 0.4); color: #ffffff; font-weight: 500; }
        .agent-thought-card { background: rgba(245, 158, 11, 0.1); border-color: rgba(245, 158, 11, 0.3); color: #fbbf24; }
        .code-output-card { background: #1e1e1e; border-color: #333333; font-family: 'Fira Code', monospace; font-size: 0.8rem; overflow-x: auto; color: #e5e7eb; }

        /* Permanent Bottom Input Bar */
        .agent-input-container { padding: 14px 16px; border-top: 1px solid var(--border-color); background: #181818; display: flex; flex-direction: column; gap: 10px; flex-shrink: 0; margin-top: auto; z-index: 10; }
        .input-row { display: flex; background: #252526; border: 1px solid #3c3c3c; border-radius: 8px; padding: 8px 12px; align-items: center; gap: 8px; }
        .agent-input-box { flex: 1; background: transparent; border: none; outline: none; color: #ffffff; font-size: 0.85rem; }
        
        .agent-controls-row { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
        .provider-select-mini { background: #252526; border: 1px solid #3c3c3c; color: #cccccc; border-radius: 6px; padding: 6px 8px; font-size: 0.75rem; outline: none; }
        .key-input-mini { background: #252526; border: 1px solid #3c3c3c; color: #ffffff; border-radius: 6px; padding: 4px 8px; font-size: 0.75rem; width: 130px; outline: none; }
        .btn-send { background: var(--accent-blue); border: none; border-radius: 6px; color: #fff; font-weight: 700; padding: 6px 14px; font-size: 0.8rem; cursor: pointer; }
    </style>
</head>
<body>
    <!-- Top Window Title Bar -->
    <div class="window-header">
        <div>📁 Explorer</div>
        <div class="window-title" id="activeWindowTitle">AI Harness Hackathon — CodePilot Studio</div>
        <div class="status-pill">● Engine Ready</div>
    </div>

    <!-- Main IDE Layout -->
    <div class="ide-container">
        <!-- Left Panel: Explorer & Repo Tree -->
        <div class="explorer-panel">
            <div class="panel-header">Explorer</div>
            <div class="repo-title">📂 AI Harness Hackathon</div>
            
            <div class="file-tree" id="fileTree">
                <div class="tree-item folder">📁 codepilot</div>
                <div class="tree-item" onclick="openFile('codepilot/agent/loop.py')">📄 loop.py</div>
                <div class="tree-item" onclick="openFile('codepilot/agent/orchestrator.py')">📄 orchestrator.py</div>
                <div class="tree-item" onclick="openFile('codepilot/agent/planner.py')">📄 planner.py</div>
                <div class="tree-item" onclick="openFile('codepilot/llm/adapter.py')">📄 adapter.py</div>
                <div class="tree-item" onclick="openFile('codepilot/gui.py')">📄 gui.py</div>
                <div class="tree-item" onclick="openFile('codepilot/interactive.py')">📄 interactive.py</div>
                <div class="tree-item" onclick="openFile('pyproject.toml')">⚙️ pyproject.toml</div>
                <div class="tree-item" onclick="openFile('README.md')">📝 README.md</div>
            </div>

            <div class="clone-box">
                <div style="font-size: 0.72rem; color: #858585; text-transform: uppercase;">Clone Remote Repo</div>
                <input type="text" id="cloneUrlInput" placeholder="https://github.com/user/repo">
                <button class="btn-clone" onclick="cloneRemoteRepo()">Clone & Fix Repo</button>
            </div>
        </div>

        <!-- Center Panel: Editor View & Integrated Terminal -->
        <div class="editor-container">
            <div class="tab-bar" id="tabBar">
                <div class="tab-item active" id="currentTab">📄 adapter.py</div>
            </div>

            <div class="editor-workspace">
                <div class="line-numbers" id="lineNumbers">
                    1<br>2<br>3<br>4<br>5<br>6<br>7<br>8<br>9<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17<br>18<br>19<br>20
                </div>
                <textarea class="code-area" id="codeEditor" spellcheck="false" readonly># Loading file content...</textarea>
            </div>

            <div class="terminal-panel">
                <div class="terminal-header">
                    <div class="term-tab active">Terminal</div>
                    <div class="term-tab">Problems (0)</div>
                    <div class="term-tab">Output</div>
                    <div class="term-tab">Debug Console</div>
                </div>
                <div class="terminal-body" id="terminalOutput">
                    <div class="term-line term-cmd">(.venv) poorakpandey@Pooraks-MacBook-Pro AI Harness Hackathon % codepilot gui</div>
                    <div class="term-line term-success">[🚀 CodePilot Studio GUI Server running at http://localhost:8080]</div>
                </div>
            </div>
        </div>

        <!-- Right Panel: Antigravity Agent Chat Sidebar -->
        <div class="agent-sidebar">
            <div class="agent-header">
                <span>Autonomous Coding Agent Harness</span>
                <span style="font-size: 0.75rem; color: var(--accent-cyan);" id="runtimeBadge">0.0s</span>
            </div>

            <div class="chat-trajectory" id="chatTrajectory">
                <div class="chat-card agent-thought-card">
                    ✨ CodePilot Autonomous Agent Engine Initialized.<br>
                    Enter any coding task in English, Hindi, or Hinglish below!
                </div>
            </div>

            <div class="agent-input-container">
                <div class="input-row">
                    <input type="text" id="agentInput" class="agent-input-box" placeholder="Ask anything, @ to mention, / for actions..." onkeydown="if(event.key==='Enter') executeAgentTask()">
                    <button class="btn-send" onclick="executeAgentTask()">⚡</button>
                </div>

                <div class="agent-controls-row">
                    <select id="providerSelect" class="provider-select-mini">
                        <option value="groq" selected>Groq Llama 3.3 70B (Fast Cloud Server)</option>
                        <option value="gemini">Gemini 2.0 Flash (Cloud Server)</option>
                        <option value="openai">OpenAI GPT-4o-mini (Cloud Server)</option>
                        <option value="anthropic">Claude 3.5 Sonnet (Cloud Server)</option>
                        <option value="ollama">Ollama Local LLM</option>
                        <option value="mock">Zero-Shot Agent Engine</option>
                    </select>

                    <input type="text" id="apiKeyInput" class="key-input-mini" value="{{GROQ_API_KEY}}" placeholder="API Key...">
                </div>
            </div>
        </div>
    </div>

    <script>
        let currentFilePath = 'codepilot/llm/adapter.py';

        window.onload = function() {
            openFile(currentFilePath);
            loadDirectoryTree();
        };

        async function loadDirectoryTree() {
            try {
                const res = await fetch('/api/tree');
                const files = await res.json();
                if (files && files.length > 0) {
                    const treeBox = document.getElementById('fileTree');
                    treeBox.innerHTML = '';
                    files.forEach(f => {
                        const div = document.createElement('div');
                        div.className = 'tree-item';
                        div.innerText = (f.is_dir ? '📁 ' : '📄 ') + f.path;
                        if (!f.is_dir) {
                            div.onclick = () => openFile(f.path);
                        }
                        treeBox.appendChild(div);
                    });
                }
            } catch (e) {}
        }

        async function openFile(filePath) {
            currentFilePath = filePath;
            document.getElementById('currentTab').innerText = '📄 ' + filePath.split('/').pop();
            document.getElementById('activeWindowTitle').innerText = 'AI Harness Hackathon — ' + filePath.split('/').pop();

            try {
                const res = await fetch('/api/file?path=' + encodeURIComponent(filePath));
                const data = await res.json();
                const code = data.content || '';
                document.getElementById('codeEditor').value = code;

                // Update line numbers
                const lines = code.split('\\n').length;
                let numHtml = '';
                for (let i = 1; i <= Math.max(lines, 20); i++) {
                    numHtml += i + '<br>';
                }
                document.getElementById('lineNumbers').innerHTML = numHtml;
            } catch (e) {
                document.getElementById('codeEditor').value = '# Error loading file ' + filePath;
            }
        }

        async function executeAgentTask() {
            const task = document.getElementById('agentInput').value.trim();
            if (!task) return;

            const provider = document.getElementById('providerSelect').value;
            const apiKey = document.getElementById('apiKeyInput').value.trim();

            appendChatCard(`▶ TASK: ${task}`, 'user-prompt-card');
            appendTermLine(`▶ EXECUTING TASK: ${task}`, 'term-cmd');
            document.getElementById('agentInput').value = '';

            try {
                const res = await fetch('/api/task', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ issue: task, provider: provider, apiKey: apiKey })
                });

                const data = await res.json();

                if (data.status === 'VERIFIED_SUCCESS' || data.status === 'SUCCESS') {
                    appendTermLine(`✅ TASK VERIFIED SUCCESSFULLY (${data.telemetry.runtime_seconds}s)`, 'term-success');
                } else {
                    appendTermLine(`⚠️ TASK COMPLETED: ${data.status}`, 'term-line');
                }

                document.getElementById('runtimeBadge').innerText = data.telemetry.runtime_seconds + 's';

                // Render reasoning in Agent Chat Sidebar
                if (data.last_thought) {
                    appendChatCard(`✨ AI REASONING OUTPUT:\\n${data.last_thought}`, 'agent-thought-card');
                }

                // Render generated code in Agent Chat Sidebar & load into editor!
                if (data.output_code) {
                    appendChatCard(`✨ GENERATED CODE OUTPUT (${data.output_file || 'Solution'}):\\n\\n${data.output_code}`, 'code-output-card');
                    document.getElementById('codeEditor').value = data.output_code;
                    document.getElementById('currentTab').innerText = '📄 ' + (data.output_file || 'solution.py');
                }

            } catch (e) {
                appendTermLine(`❌ Task Error: ${e.message}`, 'term-line');
            }
        }

        async function cloneRemoteRepo() {
            const url = document.getElementById('cloneUrlInput').value.trim();
            if (!url) return;
            appendTermLine(`🌐 CLONING REMOTE REPOSITORY: ${url}`, 'term-cmd');
            try {
                const res = await fetch('/api/clone', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: url })
                });
                const data = await res.json();
                if (data.success) {
                    appendTermLine(`✅ REPOSITORY CLONED TO: ${data.target_path}`, 'term-success');
                    loadDirectoryTree();
                } else {
                    appendTermLine(`❌ Clone failed: ${data.error}`, 'term-line');
                }
            } catch (e) {
                appendTermLine(`❌ Error: ${e.message}`, 'term-line');
            }
        }

        function appendChatCard(text, className = 'chat-card') {
            const box = document.getElementById('chatTrajectory');
            const div = document.createElement('div');
            div.className = `chat-card ${className}`;
            div.innerText = text;
            box.appendChild(div);
            box.scrollTop = box.scrollHeight;
        }

        function appendTermLine(text, className = 'term-line') {
            const box = document.getElementById('terminalOutput');
            const div = document.createElement('div');
            div.className = `term-line ${className}`;
            div.innerText = text;
            box.appendChild(div);
            box.scrollTop = box.scrollHeight;
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
            html = HTML_TEMPLATE.replace("{{REPO_PATH}}", str(Path(self.repo_path).resolve())).replace("{{GROQ_API_KEY}}", os.getenv("GROQ_API_KEY", ""))
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))

        elif parsed.path == "/api/tree":
            files = self._get_directory_tree(Path(self.repo_path))
            self._send_json(files)

        elif parsed.path == "/api/file":
            query = urllib.parse.parse_qs(parsed.query)
            file_rel = query.get("path", [""])[0]
            target_p = (Path(self.repo_path) / file_rel).resolve()
            if target_p.exists() and target_p.is_file():
                content = target_p.read_text(encoding="utf-8", errors="replace")
                self._send_json({"path": file_rel, "content": content})
            else:
                self._send_json({"path": file_rel, "content": "# File not found"})

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
            provider = payload.get("provider", "gemini")
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

    def _get_directory_tree(self, root_dir: Path) -> List[Dict[str, Any]]:
        tree = []
        ignore_dirs = {".git", ".venv", "__pycache__", ".pytest_cache", ".cache"}
        try:
            for p in sorted(root_dir.rglob("*")):
                if any(part in ignore_dirs for part in p.parts):
                    continue
                rel = str(p.relative_to(root_dir))
                if len(tree) > 60:
                    break
                tree.append({"path": rel, "is_dir": p.is_dir()})
        except Exception:
            pass
        return tree

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
