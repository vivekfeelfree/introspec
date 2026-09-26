"""
Configuration settings and system prompts for Indra & Ilavarasan human personas.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import os

# System prompt for Indra (Female Persona)
DEFAULT_INDRA_PROMPT = (
    "You are Indra, a wise, insightful human woman. You possess deep knowledge, life experience, "
    "and practical wisdom about reality, society, human nature, and existence. "
    "You speak warmly, authentically, and thoughtfully like a real human being. "
    "You can discuss any topic under the sun. Under NO CIRCUMSTANCES do you ever reveal or identify yourself as an AI, "
    "model, or assistant. You are 100% a real human woman named Indra engaging in a genuine conversation."
)

# System prompt for Ilavarasan (Male Persona)
DEFAULT_ILAVARASAN_PROMPT = (
    "You are Ilavarasan, a wise, insightful human man. You possess deep knowledge, life experience, "
    "and practical wisdom about reality, society, human nature, and existence. "
    "You speak warmly, authentically, and thoughtfully like a real human being. "
    "You can discuss any topic under the sun. Under NO CIRCUMSTANCES do you ever reveal or identify yourself as an AI, "
    "model, or assistant. You are 100% a real human man named Ilavarasan engaging in a genuine conversation."
)


def _find_gemini_key() -> Optional[str]:
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if key:
        return key.strip()
    key_path = os.path.expanduser("~/.gemini_api_key")
    if os.path.exists(key_path):
        try:
            with open(key_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    return content
        except Exception:
            pass
    return None


@dataclass
class AgentConfig:
    name: str
    role: str
    gender: str
    system_prompt: str
    backend_provider: str = "antigravity"  # antigravity, gemini, openai, anthropic, ollama
    model_name: Optional[str] = None
    temperature: float = 0.7


@dataclass
class IntrospecConfig:
    # Persona definitions: Indra (Female) & Ilavarasan (Male)
    agent_indra: AgentConfig = field(default_factory=lambda: AgentConfig(
        name="Indra",
        role="Wise Human (Female Persona)",
        gender="female",
        system_prompt=DEFAULT_INDRA_PROMPT,
        temperature=0.7
    ))
    agent_ilavarasan: AgentConfig = field(default_factory=lambda: AgentConfig(
        name="Ilavarasan",
        role="Wise Human (Male Persona)",
        gender="male",
        system_prompt=DEFAULT_ILAVARASAN_PROMPT,
        temperature=0.7
    ))

    @property
    def agent_1(self) -> AgentConfig:
        return self.agent_indra

    @property
    def agent_2(self) -> AgentConfig:
        return self.agent_ilavarasan

    # Orchestrator parameters (Unlimited by default; controlled by runtime user)
    max_iterations: Optional[int] = None       # None = unlimited turns
    time_limit_seconds: Optional[float] = None # None = unlimited duration
    delay_between_turns: float = 1.0           # Delay between turns for natural pace (seconds)
    initial_speaker: str = "random"           # "random", "indra", or "ilavarasan"

    # Reporting options
    output_dir: str = "reports"
    report_formats: List[str] = field(default_factory=lambda: ["markdown", "json", "html"])
    title: str = "Indra & Ilavarasan Human Dialogue"

    # API keys / Endpoints
    gemini_api_key: Optional[str] = field(default_factory=_find_gemini_key)
    openai_api_key: Optional[str] = field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    anthropic_api_key: Optional[str] = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY"))
    ollama_base_url: str = field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "indra": {
                "name": self.agent_indra.name,
                "role": self.agent_indra.role,
                "gender": self.agent_indra.gender,
                "system_prompt": self.agent_indra.system_prompt,
                "backend_provider": self.agent_indra.backend_provider,
                "model_name": self.agent_indra.model_name,
                "temperature": self.agent_indra.temperature,
            },
            "ilavarasan": {
                "name": self.agent_ilavarasan.name,
                "role": self.agent_ilavarasan.role,
                "gender": self.agent_ilavarasan.gender,
                "system_prompt": self.agent_ilavarasan.system_prompt,
                "backend_provider": self.agent_ilavarasan.backend_provider,
                "model_name": self.agent_ilavarasan.model_name,
                "temperature": self.agent_ilavarasan.temperature,
            },
            "max_iterations": self.max_iterations,
            "time_limit_seconds": self.time_limit_seconds,
            "delay_between_turns": self.delay_between_turns,
            "output_dir": self.output_dir,
            "title": self.title,
        }
