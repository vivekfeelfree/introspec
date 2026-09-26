"""
Introspec - Human Dialogue Orchestrator.

Orchestrates back-to-back interactions between Indra (Female Persona) and Ilavarasan (Male Persona)
with a stateless Human Response Generator translating all outputs to simple, non-markdown natural text.
"""

__version__ = "1.0.0"
__author__ = "Introspec Team"

from .agent import Agent, INDRA_PROMPT, ILAVARASAN_PROMPT
from .orchestrator import Orchestrator, Turn, RunResult
from .config import IntrospecConfig
from .reporter import ReportGenerator
from .translator import HumanResponseGenerator

__all__ = [
    "Agent",
    "INDRA_PROMPT",
    "ILAVARASAN_PROMPT",
    "Orchestrator",
    "Turn",
    "RunResult",
    "IntrospecConfig",
    "ReportGenerator",
    "HumanResponseGenerator",
]
