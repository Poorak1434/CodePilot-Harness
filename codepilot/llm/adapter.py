"""
Unified LLM Adapter supporting Gemini, OpenAI, Anthropic, Ollama, and Mock providers.
"""
import os
import json
import re
from typing import Dict, Any, Optional, List


class LLMAdapter:
    def __init__(self, provider: str = "mock", model_name: Optional[str] = None, api_key: Optional[str] = None):
        self.provider = provider.lower()
        self.model_name = model_name or self._default_model_name(self.provider)
        self.api_key = api_key or os.getenv(f"{self.provider.upper()}_API_KEY")

        # Mock replay steps for deterministic test execution
        self.mock_script: List[Dict[str, Any]] = []
        self.mock_step_index = 0

    def _default_model_name(self, provider: str) -> str:
        defaults = {
            "gemini": "gemini-2.5-flash",
            "openai": "gpt-4o-mini",
            "anthropic": "claude-3-5-sonnet-20241022",
            "ollama": "llama3",
            "mock": "mock-llm-v1"
        }
        return defaults.get(provider, "mock-llm-v1")

    def set_mock_script(self, script: List[Dict[str, Any]]) -> None:
        """Configures replay sequence for deterministic mock provider."""
        self.mock_script = script
        self.mock_step_index = 0

    def generate_response(self, system_prompt: str, user_context: str, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generates structured JSON response containing thought, plan, and tool_call.
        Returns Dict with keys: thought, plan, tool_call.
        """
        if self.provider == "mock":
            return self._generate_mock_response(user_context)

        if self.provider == "openai":
            return self._call_openai(system_prompt, user_context, history)

        if self.provider == "gemini":
            return self._call_gemini(system_prompt, user_context, history)

        if self.provider == "anthropic":
            return self._call_anthropic(system_prompt, user_context, history)

        # Fallback to mock if API key missing or provider unknown
        return self._generate_mock_response(user_context)

    def _generate_mock_response(self, user_context: str = "") -> Dict[str, Any]:
        if self.mock_script and self.mock_step_index < len(self.mock_script):
            resp = self.mock_script[self.mock_step_index]
            self.mock_step_index += 1
            return resp

        step = self.mock_step_index
        self.mock_step_index += 1

        # Check if context is a snippet debugging task
        if "sandbox_snippet.py" in user_context:
            if step == 0:
                # Fix all syntax/type/runtime errors in sandbox_snippet.py
                fixed_snippet = (
                    "import math\n\n"
                    "total_users = 10\n\n"
                    "def greet_user(name, age):\n"
                    "    return f'Hello {name}, you are {age} years old!'\n\n"
                    "def divide(a, b):\n"
                    "    if b == 0:\n"
                    "        return 'Error: Division by zero'\n"
                    "    return a / b\n\n"
                    "def calculate_average(numbers):\n"
                    "    if not numbers:\n"
                    "        return 0.0\n"
                    "    if isinstance(numbers, str):\n"
                    "        numbers = [float(x) for x in numbers if x.isdigit()]\n"
                    "    total = sum(numbers)\n"
                    "    count = len(numbers)\n"
                    "    return total / count if count > 0 else 0.0\n\n"
                    "def get_user_by_index(users, index):\n"
                    "    if index >= len(users) or index < 0:\n"
                    "        return 'Index out of range'\n"
                    "    return users[index]\n\n"
                    "def main():\n"
                    "    print('Program started')\n"
                    "    greeting = greet_user('Rahul', 25)\n"
                    "    print(greeting)\n"
                    "    result = divide(10, 2)\n"
                    "    print('Division result:', result)\n"
                    "    avg = calculate_average('12345')\n"
                    "    print('Average:', avg)\n"
                    "    users_list = ['Aman', 'Riya', 'Sonal']\n"
                    "    user = get_user_by_index(users_list, 1)\n"
                    "    print('User at index 1:', user)\n"
                    "    active_users = total_users + 5\n"
                    "    print('Active users:', active_users)\n"
                    "    undefined_var = 'Defined value'\n"
                    "    print('Some value:', undefined_var)\n\n"
                    "if __name__ == '__main__':\n"
                    "    main()\n"
                )
                return {
                    "thought": "Debugging sandbox_snippet.py: Fixing syntax errors, imports, zero division, type conversions, and missing variable definitions.",
                    "plan": ["Rewrite sandbox_snippet.py with fixed code", "Run python test verification"],
                    "tool_call": {
                        "name": "create_file",
                        "arguments": {
                            "path": "sandbox_snippet.py",
                            "content": fixed_snippet
                        }
                    }
                }
            elif step == 1:
                return {
                    "thought": "Code snippet fixed and saved. Verifying execution.",
                    "plan": ["Execute python sandbox_snippet.py"],
                    "tool_call": {
                        "name": "run_command",
                        "arguments": {"command": "python3 sandbox_snippet.py"}
                    }
                }
            else:
                return {
                    "thought": "All syntax, type, and runtime errors in code snippet resolved and verified.",
                    "plan": ["Task complete"],
                    "tool_call": {"name": "done", "arguments": {"reason": "Fixed all code snippet errors"}}
                }

        # Default mock sequence for demo repo
        if step == 0:
            return {
                "thought": "Initial step: Run test suite to discover failure trace.",
                "plan": ["Run unit tests", "Analyze failure"],
                "tool_call": {"name": "run_tests", "arguments": {}}
            }
        elif step == 1:
            return {
                "thought": "Test failed with AssertionError. Fixing math_utils.py discount formula.",
                "plan": ["Edit math_utils.py", "Re-run tests"],
                "tool_call": {
                    "name": "edit_file",
                    "arguments": {
                        "path": "math_utils.py",
                        "old_str": "price * (discount_percent / 1000)",
                        "new_str": "price * (discount_percent / 100)"
                    }
                }
            }
        elif step == 2:
            return {
                "thought": "Code modified. Re-executing test suite.",
                "plan": ["Re-run unit tests"],
                "tool_call": {"name": "run_tests", "arguments": {}}
            }
        else:
            return {
                "thought": "All unit tests pass. Task verified successfully.",
                "plan": ["Declare completion"],
                "tool_call": {"name": "done", "arguments": {"reason": "Fixed discount calculation bug"}}
            }

    def _call_openai(self, system_prompt: str, user_context: str, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            messages = [{"role": "system", "content": system_prompt}]
            messages.append({"role": "user", "content": user_context})

            for h in history[-6:]:
                messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})

            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.1
            )
            raw_text = response.choices[0].message.content
            return self._parse_json(raw_text)
        except Exception as e:
            return {
                "thought": f"OpenAI API call error: {str(e)}.",
                "plan": ["Run fallback inspection"],
                "tool_call": {"name": "run_tests", "arguments": {}}
            }

    def _call_gemini(self, system_prompt: str, user_context: str, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            full_prompt = f"{system_prompt}\n\n{user_context}\n"
            for h in history[-6:]:
                full_prompt += f"\n{h.get('role', 'user')}: {h.get('content', '')}"

            response = client.models.generate_content(
                model=self.model_name,
                contents=full_prompt,
                config={"response_mime_type": "application/json"}
            )
            return self._parse_json(response.text)
        except Exception as e:
            return {
                "thought": f"Gemini API call error: {str(e)}.",
                "plan": ["Run fallback inspection"],
                "tool_call": {"name": "run_tests", "arguments": {}}
            }

    def _call_anthropic(self, system_prompt: str, user_context: str, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            messages = [{"role": "user", "content": f"{user_context}\nRespond strictly in JSON format."}]

            response = client.messages.create(
                model=self.model_name,
                max_tokens=2048,
                system=system_prompt,
                messages=messages
            )
            return self._parse_json(response.content[0].text)
        except Exception as e:
            return {
                "thought": f"Anthropic API call error: {str(e)}.",
                "plan": ["Run fallback inspection"],
                "tool_call": {"name": "run_tests", "arguments": {}}
            }

    def _parse_json(self, text: str) -> Dict[str, Any]:
        """Parses LLM text output into structured JSON dictionary."""
        cleaned = text.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0].strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    pass

            return {
                "thought": f"Could not parse response as JSON: {text[:100]}",
                "plan": ["Retry step"],
                "tool_call": {"name": "run_tests", "arguments": {}}
            }
