"""
Unified LLM Adapter supporting Groq, Gemini, OpenAI, Anthropic, Ollama, and Mock providers.
Follows LLM-first architecture where foundation models drive reasoning and tool selection.
"""
import os
import sys
import json
import re
from pathlib import Path


def load_env_file():
    """Auto-load .env configuration file if present."""
    env_path = Path(".env")
    if env_path.exists():
        try:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    if k.strip() not in os.environ:
                        os.environ[k.strip()] = v.strip().strip('"').strip("'")
        except Exception:
            pass



class LLMAdapter:
    def __init__(self, provider: Optional[str] = None, model_name: Optional[str] = None, api_key: Optional[str] = None):
        load_env_file()
        
        prov_env = os.getenv("CODEPILOT_PROVIDER") or os.getenv("DEFAULT_PROVIDER") or "gemini"
        self.provider = (provider or prov_env).lower()
        self.model_name = model_name or os.getenv("CODEPILOT_MODEL") or self._default_model_name(self.provider)
        self.api_key = api_key or os.getenv("CODEPILOT_API_KEY") or os.getenv(f"{self.provider.upper()}_API_KEY")

        # Mock script replay for deterministic unit test execution ONLY
        self.mock_script: List[Dict[str, Any]] = []
        self.mock_step_index = 0

        self.last_prompt_tokens = 0
        self.last_completion_tokens = 0

    def _default_model_name(self, provider: str) -> str:
        defaults = {
            "gemini": "gemini-2.0-flash",
            "openai": "gpt-4o-mini",
            "anthropic": "claude-3-5-sonnet-20241022",
            "groq": "llama-3.3-70b-versatile",
            "ollama": "qwen2.5-coder:1.5b",
            "on_device": "qwen2.5-coder:1.5b",
            "slm": "qwen2.5-coder:1.5b",
            "mock": "mock-llm-v1"
        }
        return defaults.get(provider.lower(), "qwen2.5-coder:1.5b")

    def set_mock_script(self, script: List[Dict[str, Any]]) -> None:
        """Configures replay sequence for deterministic mock provider during automated testing."""
        self.mock_script = script
        self.mock_step_index = 0

    def generate_response(self, system_prompt: str, user_context: str, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generates structured JSON response containing thought, plan, and tool_call.
        Returns Dict with keys: thought, plan, tool_call, _api_error (optional bool).
        """
        # Ensure fresh API Key lookup if set dynamically
        if not self.api_key or self.api_key == "{{GROQ_API_KEY}}":
            self.api_key = os.getenv("CODEPILOT_API_KEY") or os.getenv(f"{self.provider.upper()}_API_KEY")

        full_prompt = f"{system_prompt}\n{user_context}"
        self.last_prompt_tokens = max(1, len(full_prompt) // 4)

        if self.provider in ("on_device", "slm"):
            resp = self._call_on_device_slm(system_prompt, user_context, history)
        elif self.provider == "groq":
            resp = self._call_groq(system_prompt, user_context, history)
        elif self.provider == "openai":
            resp = self._call_openai(system_prompt, user_context, history)
        elif self.provider == "gemini":
            resp = self._call_gemini(system_prompt, user_context, history)
        elif self.provider == "anthropic":
            resp = self._call_anthropic(system_prompt, user_context, history)
        elif self.provider == "ollama":
            resp = self._call_ollama(system_prompt, user_context, history)
        elif self.provider == "mock":
            resp = self._call_mock(user_context)
        else:
            resp = {
                "_api_error": True,
                "thought": f"Unsupported LLM provider '{self.provider}'. Available providers: on_device, slm, groq, gemini, openai, anthropic, ollama, mock.",
                "plan": [],
                "tool_call": None
            }

        resp_str = str(resp)
        self.last_completion_tokens = max(1, len(resp_str) // 4)
        return resp

    def _call_on_device_slm(self, system_prompt: str, user_context: str, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Executes locally on-device using local Ollama SLM model.
        Reports clear error if Ollama server or model is not installed.
        """
        url = "http://localhost:11434/api/chat"
        messages = [{"role": "system", "content": system_prompt}]
        for h in history[-10:]:
            messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
        messages.append({"role": "user", "content": user_context})

        model_to_use = self.model_name if self.model_name and self.model_name != "slm-3b-local" else "qwen2.5-coder:1.5b"

        payload = json.dumps({
            "model": model_to_use,
            "messages": messages,
            "stream": False,
            "format": "json"
        }).encode("utf-8")

        try:
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = data.get("message", {}).get("content", "")
                return self._parse_json(text)
        except Exception as e:
            return {
                "_api_error": True,
                "thought": (
                    f"Ollama Local SLM Error: {str(e)}.\n\n"
                    "Ollama service or local SLM model is not running at http://localhost:11434.\n"
                    "To use local on-device SLM:\n"
                    " 1. Install Ollama: brew install ollama\n"
                    " 2. Pull model: ollama pull qwen2.5-coder:7b\n"
                    " 3. Start service: ollama serve\n\n"
                    "Alternatively, set a cloud provider API key (e.g. /key <api_key> for Groq, Gemini, OpenAI, or Anthropic)."
                ),
                "plan": [],
                "tool_call": None
            }

    def _call_mock(self, user_context: str = "") -> Dict[str, Any]:
        """Deterministic mock provider for automated unit tests."""
        if self.mock_script and self.mock_step_index < len(self.mock_script):
            resp = self.mock_script[self.mock_step_index]
            self.mock_step_index += 1
            return resp

        self.mock_step_index += 1
        return {
            "thought": "Mock LLM Response: Completed query.",
            "plan": ["Mock step"],
            "tool_call": {"name": "done", "arguments": {"reason": "Mock step complete"}}
        }

    def _call_groq(self, system_prompt: str, user_context: str, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        api_key = self.api_key or os.getenv("GROQ_API_KEY") or os.getenv("CODEPILOT_API_KEY")
        if not api_key or api_key == "{{GROQ_API_KEY}}":
            return {
                "_api_error": True,
                "thought": "Groq API Key is missing. Please configure GROQ_API_KEY in environment or pass API key via CLI/GUI.",
                "plan": [],
                "tool_call": None
            }

        messages = [{"role": "system", "content": system_prompt}]
        for h in history[-10:]:
            messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
        messages.append({"role": "user", "content": user_context})

        try:
            from openai import OpenAI
            client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=api_key)
            response = client.chat.completions.create(
                model=self.model_name or "llama-3.3-70b-versatile",
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.2
            )
            raw_text = response.choices[0].message.content
            return self._parse_json(raw_text)
        except Exception as e:
            try:
                import urllib.request
                url = "https://api.groq.com/openai/v1/chat/completions"
                payload = json.dumps({
                    "model": self.model_name or "llama-3.3-70b-versatile",
                    "messages": messages,
                    "response_format": {"type": "json_object"},
                    "temperature": 0.2
                }).encode("utf-8")

                req = urllib.request.Request(
                    url,
                    data=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {api_key}"
                    }
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    return self._parse_json(text)
            except Exception as e2:
                err_msg = f"Groq API Error: {str(e)}"
                return {
                    "_api_error": True,
                    "thought": err_msg,
                    "plan": [],
                    "tool_call": None
                }

    def _call_gemini(self, system_prompt: str, user_context: str, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        api_key = self.api_key or os.getenv("GEMINI_API_KEY") or os.getenv("CODEPILOT_API_KEY")
        if not api_key:
            return {
                "_api_error": True,
                "thought": "Gemini API Key is missing. Please set GEMINI_API_KEY in environment or pass API key via CLI/GUI.",
                "plan": [],
                "tool_call": None
            }

        full_prompt = f"{system_prompt}\n\nIMPORTANT: You MUST respond strictly in valid JSON format.\n\n"
        for h in history[-10:]:
            full_prompt += f"{h.get('role', 'user')}: {h.get('content', '')}\n"
        full_prompt += f"user: {user_context}"

        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=self.model_name or "gemini-2.0-flash",
                contents=full_prompt,
                config={"response_mime_type": "application/json"}
            )
            return self._parse_json(response.text)
        except Exception as e1:
            try:
                import google.generativeai as genai_legacy
                genai_legacy.configure(api_key=api_key)
                model = genai_legacy.GenerativeModel(self.model_name or "gemini-2.0-flash")
                response = model.generate_content(full_prompt)
                return self._parse_json(response.text)
            except Exception as e2:
                return {
                    "_api_error": True,
                    "thought": f"Gemini API Error: {str(e1)}",
                    "plan": [],
                    "tool_call": None
                }

    def _call_openai(self, system_prompt: str, user_context: str, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        api_key = self.api_key or os.getenv("OPENAI_API_KEY") or os.getenv("CODEPILOT_API_KEY")
        if not api_key:
            return {
                "_api_error": True,
                "thought": "OpenAI API Key is missing. Please set OPENAI_API_KEY in environment or pass API key via CLI/GUI.",
                "plan": [],
                "tool_call": None
            }

        messages = [{"role": "system", "content": system_prompt}]
        for h in history[-10:]:
            messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
        messages.append({"role": "user", "content": user_context})

        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=self.model_name or "gpt-4o-mini",
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.2
            )
            raw_text = response.choices[0].message.content
            return self._parse_json(raw_text)
        except Exception as e:
            return {
                "_api_error": True,
                "thought": f"OpenAI API Error: {str(e)}",
                "plan": [],
                "tool_call": None
            }

    def _call_anthropic(self, system_prompt: str, user_context: str, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        api_key = self.api_key or os.getenv("ANTHROPIC_API_KEY") or os.getenv("CODEPILOT_API_KEY")
        if not api_key:
            return {
                "_api_error": True,
                "thought": "Anthropic API Key is missing. Please set ANTHROPIC_API_KEY in environment or pass API key via CLI/GUI.",
                "plan": [],
                "tool_call": None
            }

        messages = []
        for h in history[-10:]:
            messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
        messages.append({"role": "user", "content": f"{user_context}\nRespond strictly in valid JSON."})

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model=self.model_name or "claude-3-5-sonnet-20241022",
                max_tokens=2048,
                system=system_prompt,
                messages=messages
            )
            return self._parse_json(response.content[0].text)
        except Exception as e:
            return {
                "_api_error": True,
                "thought": f"Anthropic API Error: {str(e)}",
                "plan": [],
                "tool_call": None
            }

    def _call_ollama(self, system_prompt: str, user_context: str, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            import urllib.request
            url = "http://localhost:11434/api/chat"
            messages = [{"role": "system", "content": system_prompt + "\nIMPORTANT: You MUST respond strictly in valid JSON format."}]
            for h in history[-10:]:
                messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
            messages.append({"role": "user", "content": user_context})

            payload = json.dumps({
                "model": self.model_name or "qwen2.5-coder:1.5b",
                "messages": messages,
                "stream": False,
                "format": "json"
            }).encode("utf-8")

            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = data.get("message", {}).get("content", "")
                return self._parse_json(text)
        except Exception as e:
            return {
                "_api_error": True,
                "thought": f"Ollama Local LLM Error: {str(e)}",
                "plan": [],
                "tool_call": None
            }

    def _parse_json(self, text: str) -> Dict[str, Any]:
        cleaned = text.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0].strip()

        data: Optional[Dict[str, Any]] = None
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                data = parsed
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group(0))
                    if isinstance(parsed, dict):
                        data = parsed
                except Exception:
                    pass

        if data is not None:
            if "thought" not in data:
                # Find best thought string from response
                for k in ("response", "answer", "explanation", "message", "text", "description", "summary"):
                    if k in data and isinstance(data[k], str) and data[k].strip():
                        data["thought"] = data[k]
                        break
                if "thought" not in data:
                    str_vals = [f"{k}: {v}" if not isinstance(v, str) else v for k, v in data.items() if k not in ("tool_call", "plan", "code")]
                    data["thought"] = "\n".join(str(s) for s in str_vals) if str_vals else json.dumps(data, indent=2)

            # Check if code field is provided or plan has code objects
            code_content = ""
            if "code" in data:
                if isinstance(data["code"], str) and data["code"].strip():
                    code_content = data["code"].strip()
                elif isinstance(data["code"], list):
                    code_content = "\n".join(str(c) for c in data["code"])
            elif "plan" in data and isinstance(data["plan"], list):
                code_parts = [p.get("code") for p in data["plan"] if isinstance(p, dict) and "code" in p]
                if code_parts:
                    code_content = "\n".join(code_parts)

            if code_content and code_content not in data.get("thought", ""):
                cur_thought = data.get("thought", "").strip()
                lang = "python"
                if "#include" in code_content or "std::" in code_content:
                    lang = "cpp"
                data["thought"] = f"{cur_thought}\n\n```{lang}\n{code_content}\n```".strip()

            if "tool_call" not in data:
                data["tool_call"] = {"name": "done", "arguments": {"reason": "Completed"}}
            return data

        # Wrap plain text responses into thought cleanly
        return {
            "thought": cleaned,
            "plan": [],
            "tool_call": {"name": "done", "arguments": {"reason": "Direct text response"}}
        }
