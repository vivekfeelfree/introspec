"""
Pluggable LLM Backend interface for Introspec.
Supports real LLM providers: Antigravity Native, Gemini, OpenAI, Anthropic, and Ollama.
No mock backends or canned responses.
"""

import json
import os
import urllib.request
import urllib.error
import time
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod


class BaseBackend(ABC):
    """Abstract Base Class for LLM Backends."""

    @abstractmethod
    def generate_response(
        self,
        system_prompt: str,
        conversation_history: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> str:
        """Generate response given system prompt and dialogue history."""
        pass


class AntigravityBackend(BaseBackend):
    """
    Antigravity Native LLM Backend.
    Interfaces directly with the Antigravity subagent / execution environment bridge.
    Requires an active Antigravity session or bridge environment.
    """

    def __init__(self, agent_id: int):
        self.agent_id = agent_id
        self.ipc_file = os.getenv("INTROSPEC_ANTIGRAVITY_IPC")

    def generate_response(
        self,
        system_prompt: str,
        conversation_history: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> str:
        # Check if IPC bridge file is provided
        if self.ipc_file:
            try:
                payload = {
                    "agent_id": self.agent_id,
                    "system_prompt": system_prompt,
                    "conversation_history": conversation_history,
                }
                with open(self.ipc_file, "w", encoding="utf-8") as f:
                    json.dump(payload, f)
                
                # Wait for response from Antigravity subagent bridge
                response_file = self.ipc_file + ".resp"
                for _ in range(150):
                    if os.path.exists(response_file):
                        with open(response_file, "r", encoding="utf-8") as rf:
                            resp_data = json.load(rf)
                        os.remove(response_file)
                        return resp_data.get("content", "")
                    time.sleep(0.1)
            except Exception as e:
                raise RuntimeError(f"Antigravity IPC bridge error: {e}")

        # If running in terminal environment where IPC file is not set, instruct user cleanly
        raise RuntimeError(
            f"[Agent {self.agent_id}] Antigravity Native Backend requires active session bridge or API key configuration.\n"
            f"Please specify an active backend: --backend gemini (with GEMINI_API_KEY), --backend openai (with OPENAI_API_KEY), "
            f"--backend anthropic (with ANTHROPIC_API_KEY), or --backend ollama (with local Ollama)."
        )


class GeminiBackend(BaseBackend):
    """Google Gemini API Backend using standard urllib."""

    def __init__(self, api_key: str, model: str = "gemini-1.5-pro"):
        if not api_key:
            raise ValueError("Gemini API key is required. Set GEMINI_API_KEY environment variable or pass --api-key.")
        self.api_key = api_key
        self.model = model

    def generate_response(
        self,
        system_prompt: str,
        conversation_history: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        
        contents = [
            {
                "role": "user",
                "parts": [{"text": f"[System Instruction]: {system_prompt}"}]
            },
            {
                "role": "model",
                "parts": [{"text": "Understood. I will strictly follow these instructions and maintain my persona."}]
            }
        ]

        for msg in conversation_history:
            role = "user" if msg["role"] in ["user", "human_inquirer"] else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            }
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "")
            raise RuntimeError("Empty response received from Gemini API.")
        except Exception as e:
            raise RuntimeError(f"Gemini API Error: {str(e)}")


class OpenAIBackend(BaseBackend):
    """OpenAI API Backend using standard urllib."""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        if not api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable or pass --api-key.")
        self.api_key = api_key
        self.model = model

    def generate_response(
        self,
        system_prompt: str,
        conversation_history: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> str:
        url = "https://api.openai.com/v1/chat/completions"
        
        messages = [{"role": "system", "content": system_prompt}]
        for msg in conversation_history:
            role = "user" if msg["role"] in ["user", "human_inquirer"] else "assistant"
            messages.append({"role": role, "content": msg["content"]})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"OpenAI API Error: {str(e)}")


class AnthropicBackend(BaseBackend):
    """Anthropic API Backend using standard urllib."""

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        if not api_key:
            raise ValueError("Anthropic API key is required. Set ANTHROPIC_API_KEY environment variable or pass --api-key.")
        self.api_key = api_key
        self.model = model

    def generate_response(
        self,
        system_prompt: str,
        conversation_history: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> str:
        url = "https://api.anthropic.com/v1/messages"
        
        messages = []
        for msg in conversation_history:
            role = "user" if msg["role"] in ["user", "human_inquirer"] else "assistant"
            messages.append({"role": role, "content": msg["content"]})

        if not messages:
            messages.append({"role": "user", "content": "Hello."})

        payload = {
            "model": self.model,
            "system": system_prompt,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["content"][0]["text"]
        except Exception as e:
            raise RuntimeError(f"Anthropic API Error: {str(e)}")


class OllamaBackend(BaseBackend):
    """Ollama Local Backend using standard urllib."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def generate_response(
        self,
        system_prompt: str,
        conversation_history: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> str:
        url = f"{self.base_url}/api/chat"

        messages = [{"role": "system", "content": system_prompt}]
        for msg in conversation_history:
            role = "user" if msg["role"] in ["user", "human_inquirer"] else "assistant"
            messages.append({"role": role, "content": msg["content"]})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature}
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("message", {}).get("content", "")
        except Exception as e:
            raise RuntimeError(f"Ollama Connection Error ({self.base_url}): {str(e)}. Make sure Ollama server is running.")


def get_backend(
    provider: str,
    agent_id: int = 1,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    ollama_url: Optional[str] = None,
) -> BaseBackend:
    """Factory function to instantiate appropriate LLM backend."""
    provider = provider.lower()
    if provider == "antigravity":
        return AntigravityBackend(agent_id=agent_id)
    elif provider in ["gemini", "google"]:
        key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
        mdl = model or "gemini-1.5-pro"
        return GeminiBackend(api_key=key, model=mdl)
    elif provider == "openai":
        key = api_key or os.getenv("OPENAI_API_KEY") or ""
        mdl = model or "gpt-4o"
        return OpenAIBackend(api_key=key, model=mdl)
    elif provider == "anthropic":
        key = api_key or os.getenv("ANTHROPIC_API_KEY") or ""
        mdl = model or "claude-3-5-sonnet-20241022"
        return AnthropicBackend(api_key=key, model=mdl)
    elif provider == "ollama":
        base_url = ollama_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        mdl = model or "llama3"
        return OllamaBackend(base_url=base_url, model=mdl)
    else:
        raise ValueError(
            f"Unknown backend '{provider}'. Valid backends are: antigravity, gemini, openai, anthropic, ollama."
        )
