# CodePilot AI Harness Evidence Report

**Status**: ❌ VERIFICATION FAILED  
**Task**: hi

---

## Execution Telemetry Metrics
- **Total Runtime**: 0.44s
- **Model Interactions**: 6
- **Tool Executions**: 3
- **Retries & Recoveries**: 6
- **Files Modified**: EVIDENCE_REPORT.json, EVIDENCE_REPORT.md, codepilot/interactive.py, codepilot/llm/adapter.py, sandbox_snippet.py

---

## Execution Trace
```
[01] Task received: 'hi'
[02] Repository explored and files indexed.
[03] Relevant context selected: 0 key file(s) identified.
[04] Initial plan generated.
[05] Model invocation (Turn #1, Retry #0).
[06] Tool action executed: 'run_tests' with args {}.
[07] Tool failure detected in 'run_tests'.
[08] Failure analyzed. Triggering recovery hint: RECOVERY HINT: Execution error (). Review tool parameters and error traceback before retrying.
[09] Model invocation (Turn #2, Retry #1).
[10] Tool action executed: 'edit_file' with args {'path': 'math_utils.py', 'old_str': 'price * (discount_percent / 1000)', 'new_str': 'price * (discount_percent / 100)'}.
[11] Tool failure detected in 'edit_file'.
[12] Failure analyzed. Triggering recovery hint: RECOVERY HINT: Execution error (). Review tool parameters and error traceback before retrying.
[13] Model invocation (Turn #3, Retry #2).
[14] Tool action executed: 'run_tests' with args {}.
[15] Tool failure detected in 'run_tests'.
[16] Failure analyzed. Triggering recovery hint: RECOVERY HINT: Execution error (). Review tool parameters and error traceback before retrying.
[17] Model invocation (Turn #4, Retry #3).
[18] Model declared completion. Initiating independent verification.
[19] Verification FAILED: Verification Failed: Unit test execution failed.
[20] Failure analyzed. Re-plan initiated: RECOVERY HINT: Execution error (). Review tool parameters and error traceback before retrying.
[21] Model invocation (Turn #5, Retry #4).
[22] Model declared completion. Initiating independent verification.
[23] Verification FAILED: Verification Failed: Unit test execution failed.
[24] Failure analyzed. Re-plan initiated: RECOVERY HINT: Execution error (). Review tool parameters and error traceback before retrying.
[25] Model invocation (Turn #6, Retry #5).
[26] Model declared completion. Initiating independent verification.
[27] Verification FAILED: Verification Failed: Unit test execution failed.
[28] Failure analyzed. Re-plan initiated: RECOVERY HINT: Execution error (). Review tool parameters and error traceback before retrying.
[29] Task finished without verified pass: Exceeded max retries limit (5).
```

---

## Final Verified Git Diff
```diff
STDOUT:
diff --git a/EVIDENCE_REPORT.json b/EVIDENCE_REPORT.json
index 2bb5581..397f788 100644
--- a/EVIDENCE_REPORT.json
+++ b/EVIDENCE_REPORT.json
@@ -1,17 +1,19 @@
 {
   "title": "CodePilot Harness Execution & Verification Report",
-  "task_description": "main()",
+  "task_description": "Fix and debug the code snippet in sandbox_snippet.py: import mathh\n\ntotal_users = \"10\"\n\ndef greet_user(name, age):\n    message = \"Hello \" + name + \", you ",
   "status": "VERIFICATION_FAILED",
   "verification": {
     "passed": false,
     "tests_executed": true,
     "reason": "Verification Failed: Unit test execution failed.",
-    "files_modified": [],
+    "files_modified": [
+      "sandbox_snippet.py"
+    ],
     "git_diff_length": 16,
     "test_output_preview": "STDOUT:\n\nSTDERR:\n\n----------------------------------------------------------------------\nRan 0 tests in 0.000s\n\nNO TESTS RAN"
   },
   "telemetry": {
-    "runtime_seconds": 0.28,
+    "runtime_seconds": 0.37,
     "model_calls": 6,
     "tool_calls": 3,
     "retry_count": 6,
@@ -25,7 +27,7 @@
     ]
   },
   "execution_trace": [
-    "[01] Task received: 'main()'",
+    "[01] Task received: 'Fix and debug the code snippet in sandbox_snippet.py: import mathh\n\ntotal_users = \"10\"\n\ndef greet_user(name, age):\n    message = \"Hello \" + name + \", you '",
     "[02] Repository explored and files indexed.",
     "[03] Relevant context selected: 5 key file(s) identified.",
     "[04] Initial plan generated.",
diff --git a/EVIDENCE_REPORT.md b/EVIDENCE_REPORT.md
index c285655..c1f4bd5 100644
--- a/EVIDENCE_REPORT.md
+++ b/EVIDENCE_REPORT.md
@@ -1,22 +1,32 @@
 # CodePilot AI Harness Evidence Report
 
 **Status**: ❌ VERIFICATION FAILED  
-**Task**: main()
+**Task**: Fix and debug the code snippet in sandbox_snippet.py: import mathh
+
+total_users = "10"
+
+def greet_user(name, age):
+    message = "Hello " + name + ", you 
 
 ---
 
 ## Execution Telemetry Metrics
-- **Total Runtime**: 0.28s
+- **Total Runtime**: 0.37s
 - **Model Interactions**: 6
 - **Tool Executions**: 3
 - **Retries & Recoveries**: 6
-- **Files Modified**: None
+- **Files Modified**: sandbox_snippet.py
 
 ---
 
 ## Execution Trace
 ```
-[01] Task received: 'main()'
+[01] Task received: 'Fix and debug the code snippet in sandbox_snippet.py: import mathh
+
+total_users = "10"
+
+def greet_user(name, age):
+    message = "Hello " + name + ", you '
 [02] Repository explored and files indexed.
 [03] Relevant context selected: 5 key file(s) identified.
 [04] Initial plan generated.
diff --git a/codepilot/interactive.py b/codepilot/interactive.py
index 4cb3286..3ddee4a 100644
--- a/codepilot/interactive.py
+++ b/codepilot/interactive.py
@@ -1,6 +1,6 @@
 """
 Interactive Chat & REPL mode for CodePilot Harness.
-Supports repository tasks, direct code snippet pasting & debugging, and graceful interrupt handling.
+Supports repository tasks, direct code snippet pasting & debugging, system commands, and live API key management.
 """
 import sys
 import os
@@ -64,7 +64,6 @@ class InteractiveShell:
         stripped = text.strip()
         fragments = ("else:", "elif ", "return ", "def ", "class ", "if __name__", "main()", "print(", "greeting =", "active_users =")
         if stripped in ("else:", "main()", "pass") or (len(stripped) < 40 and any(stripped.startswith(f) for f in fragments)):
-            # If it doesn't contain a full sentence or issue task keyword
             if not any(k in stripped.lower() for k in ("fix", "bug", "issue", "create", "add", "update", "test")):
                 return True
         return False
@@ -90,7 +89,7 @@ class InteractiveShell:
         print("\033[1;36m" + "=" * 70 + "\033[0m")
         print(f" • Target Repository : \033[1;32m{self.repo_path}\033[0m")
         print(f" • Model Provider   : \033[1;32m{self.provider}\033[0m")
-        print(f" • Slash Commands   : \033[1;33m/paste, /repo <path>, /provider <name>, /verify, /diff, /status, /help, /exit\033[0m")
+        print(f" • Slash Commands   : \033[1;33m/paste, /repo <path>, /provider <name>, /key <api_key>, /verify, /diff, /status, /help, /exit\033[0m")
         print("\033[1;36m" + "=" * 70 + "\033[0m\n")
 
     def _handle_slash_command(self, cmd_line: str) -> bool:
@@ -107,6 +106,7 @@ class InteractiveShell:
             print("  /paste            - Paste multi-line code snippet for quick debugging & fix")
             print("  /repo <path>      - Set active repository directory")
             print("  /provider <name>  - Set model provider (gemini, openai, anthropic, mock)")
+            print("  /key <api_key>    - Set API Key for current model provider")
             print("  /test-cmd <cmd>   - Set custom test command (e.g. pytest or python3 -m unittest)")
             print("  /verify           - Run independent verification checks on repo")
             print("  /diff             - Show current uncommitted git diff")
@@ -119,6 +119,13 @@ class InteractiveShell:
             if code_text.strip():
                 self._run_snippet_task(code_text)
 
+        elif cmd == "/key":
+            if not arg:
+                print(f"Current API key for {self.provider}: {'[SET]' if os.getenv(f'{self.provider.upper()}_API_KEY') else '[NOT SET]'}")
+            else:
+                os.environ[f"{self.provider.upper()}_API_KEY"] = arg
+                print(f"\033[1;32mAPI Key updated for {self.provider.upper()}.\033[0m")
+
         elif cmd == "/repo":
             if not arg:
                 print(f"Current repository: {self.repo_path}")
@@ -137,6 +144,12 @@ class InteractiveShell:
                 p_lower = arg.lower()
                 if p_lower in ("gemini", "openai", "anthropic", "ollama", "mock"):
                     self.provider = p_lower
+                    env_var = f"{self.provider.upper()}_API_KEY"
+                    if p_lower != "mock" and not os.getenv(env_var):
+                        print(f"\033[1;33mNote: {env_var} is not set in environment.\033[0m")
+                        key_input = input(f"Enter {self.provider.upper()} API Key (or press Enter to skip): ").strip()
+                        if key_input:
+                            os.environ[env_var] = key_input
                     print(f"\033[1;32mProvider updated to: {self.provider}\033[0m")
                 else:
                     print("\033[1;31mInvalid provider. Choose from: gemini, openai, anthropic, ollama, mock\033[0m")
@@ -190,10 +203,21 @@ class InteractiveShell:
         snippet_file = self.repo_path / "sandbox_snippet.py"
         snippet_file.write_text(clean_code, encoding="utf-8")
 
+        test_cmd = self.test_command or "python3 sandbox_snippet.py"
         task_desc = f"Fix and debug the code snippet in sandbox_snippet.py: {clean_code[:100]}"
-        self._run_task(task_desc)
 
-        # After task completes, output the fixed final code snippet
+        agent_loop = AutonomousAgentLoop(
+            workspace_root=str(self.repo_path),
+            provider=self.provider,
+            model_name=self.model_name,
+            max_retries=self.max_retries,
+            test_command=test_cmd,
+            verbose=True
+        )
+
+        report = agent_loop.run(task_description=task_desc)
+
+        # Output the fixed final code snippet directly in terminal!
         if snippet_file.exists():
             fixed_code = snippet_file.read_text(encoding="utf-8")
             print("\n\033[1;32m" + "=" * 70)
diff --git a/codepilot/llm/adapter.py b/codepilot/llm/adapter.py
index 345c983..c2e8f1a 100644
--- a/codepilot/llm/adapter.py
+++ b/codepilot/llm/adapter.py
@@ -38,7 +38,7 @@ class LLMAdapter:
         Returns Dict with keys: thought, plan, tool_call.
         """
         if self.provider == "mock":
-            return self._generate_mock_response()
+            return self._generate_mock_response(user_context)
 
         if self.provider == "openai":
             return self._call_openai(system_prompt, user_context, history)
@@ -50,18 +50,88 @@ class LLMAdapter:
             return self._call_anthropic(system_prompt, user_context, history)
 
         # Fallback to mock if API key missing or provider unknown
-        return self._generate_mock_response()
+        return self._generate_mock_response(user_context)
 
-    def _generate_mock_response(self) -> Dict[str, Any]:
+    def _generate_mock_response(self, user_context: str = "") -> Dict[str, Any]:
         if self.mock_script and self.mock_step_index < len(self.mock_script):
             resp = self.mock_script[self.mock_step_index]
             self.mock_step_index += 1
             return resp
 
-        # Smart default mock sequence for CLI demo testing
         step = self.mock_step_index
         self.mock_step_index += 1
 
+        # Check if context is a snippet debugging task
+        if "sandbox_snippet.py" in user_context:
+            if step == 0:
+                # Fix all syntax/type/runtime errors in sandbox_snippet.py
+                fixed_snippet = (
+                    "import math\n\n"
+                    "total_users = 10\n\n"
+                    "def greet_user(name, age):\n"
+                    "    return f'Hello {name}, you are {age} years old!'\n\n"
+                    "def divide(a, b):\n"
+                    "    if b == 0:\n"
+                    "        return 'Error: Division by zero'\n"
+                    "    return a / b\n\n"
+                    "def calculate_average(numbers):\n"
+                    "    if not numbers:\n"
+                    "        return 0.0\n"
+                    "    if isinstance(numbers, str):\n"
+                    "        numbers = [float(x) for x in numbers if x.isdigit()]\n"
+                    "    total = sum(numbers)\n"
+                    "    count = len(numbers)\n"
+                    "    return total / count if count > 0 else 0.0\n\n"
+                    "def get_user_by_index(users, index):\n"
+                    "    if index >= len(users) or index < 0:\n"
+                    "        return 'Index out of range'\n"
+                    "    return users[index]\n\n"
+                    "def main():\n"
+                    "    print('Program started')\n"
+                    "    greeting = greet_user('Rahul', 25)\n"
+                    "    print(greeting)\n"
+                    "    result = divide(10, 2)\n"
+                    "    print('Division result:', result)\n"
+                    "    avg = calculate_average('12345')\n"
+                    "    print('Average:', avg)\n"
+                    "    users_list = ['Aman', 'Riya', 'Sonal']\n"
+                    "    user = get_user_by_index(users_list, 1)\n"
+                    "    print('User at index 1:', user)\n"
+                    "    active_users = total_users + 5\n"
+                    "    print('Active users:', active_users)\n"
+                    "    undefined_var = 'Defined value'\n"
+                    "    print('Some value:', undefined_var)\n\n"
+                    "if __name__ == '__main__':\n"
+                    "    main()\n"
+                )
+                return {
+                    "thought": "Debugging sandbox_snippet.py: Fixing syntax errors, imports, zero division, type conversions, and missing variable definitions.",
+                    "plan": ["Rewrite sandbox_snippet.py with fixed code", "Run python test verification"],
+                    "tool_call": {
+                        "name": "create_file",
+                        "arguments": {
+                            "path": "sandbox_snippet.py",
+                            "content": fixed_snippet
+                        }
+                    }
+                }
+            elif step == 1:
+                return {
+                    "thought": "Code snippet fixed and saved. Verifying execution.",
+                    "plan": ["Execute python sandbox_snippet.py"],
+                    "tool_call": {
+                        "name": "run_command",
+                        "arguments": {"command": "python3 sandbox_snippet.py"}
+                    }
+                }
+            else:
+                return {
+                    "thought": "All syntax, type, and runtime errors in code snippet resolved and verified.",
+                    "plan": ["Task complete"],
+                    "tool_call": {"name": "done", "arguments": {"reason": "Fixed all code snippet errors"}}
+                }
+
+        # Default mock sequence for demo repo
         if step == 0:
             return {
                 "thought": "Initial step: Run test suite to discover failure trace.",
@@ -113,10 +183,9 @@ class LLMAdapter:
             raw_text = response.choices[0].message.content
             return self._parse_json(raw_text)
         except Exception as e:
-            # On API error, fallback to mock strategy to avoid crash
             return {
-                "thought": f"OpenAI API call failed: {str(e)}. Falling back to automated tool execution.",
-                "plan": ["Run verification tests."],
+                "thought": f"OpenAI API call error: {str(e)}.",
+                "plan": ["Run fallback inspection"],
                 "tool_call": {"name": "run_tests", "arguments": {}}
             }
 
@@ -136,8 +205,8 @@ class LLMAdapter:
             return self._parse_json(response.text)
         except Exception as e:
             return {
-                "thought": f"Gemini API call failed: {str(e)}. Falling back to automated tool execution.",
-                "plan": ["Run verification tests."],
+                "thought": f"Gemini API call error: {str(e)}.",
+                "plan": ["Run fallback inspection"],
                 "tool_call": {"name": "run_tests", "arguments": {}}
             }
 
@@ -145,7 +214,7 @@ class LLMAdapter:
         try:
             import anthropic
             client = anthropic.Anthropic(api_key=self.api_key)
-            messages = [{"role": "user", "content": f"{user_context}\nRespond in JSON format."}]
+            messages = [{"role": "user", "content": f"{user_context}\nRespond strictly in JSON format."}]
 
             response = client.messages.create(
                 model=self.model_name,
@@ -156,8 +225,8 @@ class LLMAdapter:
             return self._parse_json(response.content[0].text)
         except Exception as e:
             return {
-                "thought": f"Anthropic API call failed: {str(e)}. Falling back to automated tool execution.",
-                "plan": ["Run verification tests."],
+                "thought": f"Anthropic API call error: {str(e)}.",
+                "plan": ["Run fallback inspection"],
                 "tool_call": {"name": "run_tests", "arguments": {}}
             }
 
@@ -172,7 +241,6 @@ class LLMAdapter:
         try:
             return json.loads(cleaned)
         except json.JSONDecodeError:
-            # Extract json object using regex
             match = re.search(r"\{.*\}", cleaned, re.DOTALL)
             if match:
                 try:
@@ -182,6 +250,6 @@ class LLMAdapter:
 
             return {
                 "thought": f"Could not parse response as JSON: {text[:100]}",
-                "plan": ["Retry step with explicit tool call."],
+                "plan": ["Retry step"],
                 "tool_call": {"name": "run_tests", "arguments": {}}
             }

STDERR:
```
