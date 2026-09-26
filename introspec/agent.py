"""
Agent definition for Introspec orchestrator.
Wraps agent metadata, role description, system instructions, and LLM generation.
"""

from typing import List, Dict, Any, Optional
from .config import AgentConfig, DEFAULT_INDRA_PROMPT, DEFAULT_ILAVARASAN_PROMPT
from .llm_backend import BaseBackend, get_backend

INDRA_PROMPT = DEFAULT_INDRA_PROMPT
ILAVARASAN_PROMPT = DEFAULT_ILAVARASAN_PROMPT


class Agent:
    """Represents an interacting agent in the Introspec orchestra."""

    def __init__(
        self,
        agent_id: int,
        config: AgentConfig,
        backend: Optional[BaseBackend] = None,
        api_key: Optional[str] = None,
        ollama_url: Optional[str] = None,
    ):
        self.agent_id = agent_id
        self.name = config.name
        self.role = config.role
        self.system_prompt = config.system_prompt
        self.temperature = config.temperature
        self.backend_provider = config.backend_provider
        self.model_name = config.model_name

        if backend is not None:
            self.backend = backend
        else:
            self.backend = get_backend(
                provider=config.backend_provider,
                agent_id=agent_id,
                api_key=api_key,
                model=config.model_name,
                ollama_url=ollama_url,
            )

    def speak(
        self,
        conversation_history: List[Dict[str, str]],
        max_tokens: int = 2048,
    ) -> str:
        """
        Generate agent utterance based on historical dialog.
        `conversation_history` is a list of {"role": "user"|"assistant", "content": "..."}
        from this agent's perspective.
        """
        return self.backend.generate_response(
            system_prompt=self.system_prompt,
            conversation_history=conversation_history,
            temperature=self.temperature,
            max_tokens=max_tokens,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role,
            "system_prompt": self.system_prompt,
            "backend_provider": self.backend_provider,
            "model_name": self.model_name,
            "temperature": self.temperature,
        }
