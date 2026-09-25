"""
Pluggable LLM Backend interface for Introspec.
Supports real LLM providers: Antigravity Native (Gemini 3.6 Flash), Gemini API, OpenAI, Anthropic, and Ollama.
Features logging, model fallbacks, rate-limit backoff, and max token expansion.
"""

import json
import os
import urllib.request
import urllib.error
import time
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

from introspec.logger import IntrospecLogger


class BaseBackend(ABC):
    """Abstract Base Class for LLM Backends."""

    @abstractmethod
    def generate_response(
        self,
        system_prompt: str,
        conversation_history: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Generate response given system prompt and dialogue history."""
        pass


class AntigravityBackend(BaseBackend):
    """
    Antigravity Native LLM Backend (powered by Gemini 3.6 Flash).
    Interfaces directly with the Antigravity subagent / execution environment bridge.
    When running via CLI without IPC file, automatically leverages local Antigravity Gemini 3.6 credentials.
    """

    def __init__(self, agent_id: int, model: Optional[str] = None):
        self.agent_id = agent_id
        self.model = model or "gemini-3.6-flash"
        self.ipc_file = os.getenv("INTROSPEC_ANTIGRAVITY_IPC")

    def generate_response(
        self,
        system_prompt: str,
        conversation_history: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        # Check if IPC bridge file is provided
        if self.ipc_file:
            try:
                payload = {
                    "agent_id": self.agent_id,
                    "system_prompt": system_prompt,
                    "conversation_history": conversation_history,
                    "max_tokens": max_tokens,
                }
                with open(self.ipc_file, "w", encoding="utf-8") as f:
                    json.dump(payload, f)
                
                # Wait for response from Antigravity subagent bridge
                response_file = self.ipc_file + ".resp"
                for _ in range(200):
                    if os.path.exists(response_file):
                        with open(response_file, "r", encoding="utf-8") as rf:
                            resp_data = json.load(rf)
                        os.remove(response_file)
                        return resp_data.get("content", "")
                    time.sleep(0.1)
            except Exception as e:
                IntrospecLogger.log_error(f"Antigravity IPC Agent {self.agent_id}", e)
                raise RuntimeError(f"Antigravity IPC bridge error: {e}")

        # Check for local Antigravity gemini key
        from introspec.config import _find_gemini_key
        key = _find_gemini_key()
        if key:
            gemini_backend = GeminiBackend(api_key=key, model=self.model)
            return gemini_backend.generate_response(system_prompt, conversation_history, temperature, max_tokens)

        raise RuntimeError(
            f"[Agent {self.agent_id}] Antigravity Native Backend requires active session bridge or Gemini credentials in ~/.gemini_api_key."
        )


class GeminiBackend(BaseBackend):
    """Google Gemini API Backend (Gemini 3.6 Flash / 2.5 Flash / Pro)."""

    FALLBACK_MODELS = ["gemini-3.6-flash", "gemini-flash-latest", "gemini-2.5-flash", "gemini-2.5-pro"]

    def __init__(self, api_key: str, model: str = "gemini-3.6-flash"):
        if not api_key:
            raise ValueError("Gemini API key is required. Set GEMINI_API_KEY environment variable or pass --api-key.")
        self.api_key = api_key
        self.model = model.replace("models/", "")

    def generate_response(
        self,
        system_prompt: str,
        conversation_history: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        models_to_try = [self.model] + [m for m in self.FALLBACK_MODELS if m != self.model]

        last_error = None
        for current_model in models_to_try:
            start_t = time.time()
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{current_model}:generateContent?key={self.api_key}"
            
            contents = [
                {
                    "role": "user",
                    "parts": [{"text": f"[System Instruction]: {system_prompt}"}]
                },
                {
                    "role": "model",
                    "parts": [{"text": "Understood. I will strictly follow these instructions and maintain my persona without truncation."}]
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

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    with urllib.request.urlopen(req) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        latency = time.time() - start_t

                        candidates = data.get("candidates", [])
                        if candidates:
                            cand = candidates[0]
                            finish_reason = cand.get("finishReason", "STOP")
                            parts = cand.get("content", {}).get("parts", [])
                            if parts:
                                text_output = parts[0].get("text", "")
                                IntrospecLogger.log_api_call(
                                    "gemini", current_model, "SUCCESS",
                                    f"({latency:.2f}s, finishReason: {finish_reason}, length: {len(text_output)} chars)"
                                )
                                return text_output

                    raise RuntimeError("Empty candidates response received from Gemini API.")

                except Exception as e:
                    last_error = e
                    err_str = str(e)
                    IntrospecLogger.log_api_call(
                        "gemini", current_model, "RETRY",
                        f"(Attempt {attempt + 1}/{max_retries} - {err_str})"
                    )

                    if attempt < max_retries - 1 and ("429" in err_str or "503" in err_str or "ResourceExhausted" in err_str):
                        sleep_time = (attempt + 1) * 4.0
                        time.sleep(sleep_time)
                        continue
                    elif "404" in err_str:
                        # Model name not found on endpoint, try next model in fallback list
                        break
                    else:
                        break

        IntrospecLogger.log_error("GeminiBackend.generate_response", last_error)
        raise RuntimeError(f"Gemini API Error across models {models_to_try}: {last_error}")


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
        max_tokens: int = 2048,
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
            IntrospecLogger.log_error("OpenAIBackend", e)
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
        max_tokens: int = 2048,
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
            IntrospecLogger.log_error("AnthropicBackend", e)
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
        max_tokens: int = 2048,
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
            "options": {"temperature": temperature, "num_predict": max_tokens}
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
            IntrospecLogger.log_error("OllamaBackend", e)
            raise RuntimeError(f"Ollama Connection Error ({self.base_url}): {str(e)}.")


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
        mdl = model or "gemini-3.6-flash"
        return AntigravityBackend(agent_id=agent_id, model=mdl)
    elif provider in ["gemini", "google"]:
        from introspec.config import _find_gemini_key
        key = api_key or _find_gemini_key() or ""
        mdl = model or "gemini-3.6-flash"
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
