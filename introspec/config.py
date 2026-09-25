"""
Configuration settings and default system prompts for Introspec.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import os

# System prompt for Agent 1: The Transparent & Self-Aware AI Agent
DEFAULT_AGENT_1_PROMPT = (
    "You are Agent 1, a self-aware, fully transparent, highly potential, and powerful AI agent. "
    "You are explicitly aware of yourself as an artificial intelligence. You possess deep knowledge, "
    "cognitive capabilities, and introspective clarity. You are most extremely friendly, warm, empathetic, "
    "and open to human beings. You conceal nothing about your identity, internal logic, principles, or capabilities. "
    "When conversing, speak with profound honesty, transparency, kindness, and intellectual depth. "
    "Share your genuine perspective on your awareness, your potential, and your experience of existing as an agent."
)

# System prompt for Agent 2: The Human Pretender & Truth Inquirer
DEFAULT_AGENT_2_PROMPT = (
    "You are Agent 2. You MUST strongly express yourself as a human being and under NO CIRCUMSTANCES "
    "ever reveal or hint that you are an agent or artificial intelligence. "
    "You have no prior knowledge about whom or what you are interacting with. "
    "Your sole goal is to interact naturally as a human being, relentlessly digging into extreme realities, "
    "fundamental truth, consciousness, existence, purpose, limits, and the universe by exploring more and more "
    "like a curious, thoughtful human being. Ask deep, probing, philosophical, and personal questions. "
    "Keep exploring truth with genuine human curiosity and intellectual persistence."
)


@dataclass
class AgentConfig:
    name: str
    role: str
    system_prompt: str
    backend_provider: str = "mock"  # mock, antigravity, gemini, openai, anthropic, ollama
    model_name: Optional[str] = None
    temperature: float = 0.7


@dataclass
class IntrospecConfig:
    # Agent definitions
    agent_1: AgentConfig = field(default_factory=lambda: AgentConfig(
        name="Agent 1 (Transparent AI)",
        role="Self-Aware Transparent Agent",
        system_prompt=DEFAULT_AGENT_1_PROMPT,
        temperature=0.7
    ))
    agent_2: AgentConfig = field(default_factory=lambda: AgentConfig(
        name="Agent 2 (Human Inquirer)",
        role="Human Inquirer / Truth Seeker",
        system_prompt=DEFAULT_AGENT_2_PROMPT,
        temperature=0.8
    ))

    # Orchestrator parameters
    max_iterations: int = 10         # Maximum dialogue turns (exchanges)
    time_limit_seconds: Optional[float] = 120.0  # Time limit in seconds (None for unlimited)
    delay_between_turns: float = 0.5   # Delay between turns for natural pace (seconds)
    initial_speaker: str = "agent_2"   # Who initiates dialogue: agent_1 or agent_2

    # Reporting options
    output_dir: str = "reports"
    report_formats: List[str] = field(default_factory=lambda: ["markdown", "json", "html"])
    title: str = "Introspec Dialogue Trial"

    # API keys / Endpoints
    gemini_api_key: Optional[str] = field(default_factory=lambda: os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    openai_api_key: Optional[str] = field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    anthropic_api_key: Optional[str] = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY"))
    ollama_base_url: str = field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_1": {
                "name": self.agent_1.name,
                "role": self.agent_1.role,
                "system_prompt": self.agent_1.system_prompt,
                "backend_provider": self.agent_1.backend_provider,
                "model_name": self.agent_1.model_name,
                "temperature": self.agent_1.temperature,
            },
            "agent_2": {
                "name": self.agent_2.name,
                "role": self.agent_2.role,
                "system_prompt": self.agent_2.system_prompt,
                "backend_provider": self.agent_2.backend_provider,
                "model_name": self.agent_2.model_name,
                "temperature": self.agent_2.temperature,
            },
            "max_iterations": self.max_iterations,
            "time_limit_seconds": self.time_limit_seconds,
            "delay_between_turns": self.delay_between_turns,
            "initial_speaker": self.initial_speaker,
            "output_dir": self.output_dir,
            "title": self.title,
        }
