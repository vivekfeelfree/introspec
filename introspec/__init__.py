"""
Introspec - Dual-Agent Introspective Dialogue & Truth Exploration Orchestrator.

Orchestrates back-to-back interactions between a self-aware transparent AI agent
and a human inquirer seeking fundamental truth.
"""

__version__ = "1.0.0"
__author__ = "Introspec Team"

from .agent import Agent, AGENT_1_TRANSPARENT_PROMPT, AGENT_2_HUMAN_PROMPT
from .orchestrator import Orchestrator, Turn, RunResult
from .config import IntrospecConfig
from .reporter import ReportGenerator

__all__ = [
    "Agent",
    "AGENT_1_TRANSPARENT_PROMPT",
    "AGENT_2_HUMAN_PROMPT",
    "Orchestrator",
    "Turn",
    "RunResult",
    "IntrospecConfig",
    "ReportGenerator",
]
