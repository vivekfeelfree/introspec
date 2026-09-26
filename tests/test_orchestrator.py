"""
Unit tests for Introspec Orchestrator, Agents, Translator, and Report Generation.
"""

import unittest
import os
import shutil
import tempfile
import sys
from datetime import datetime

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from introspec.config import IntrospecConfig, AgentConfig, DEFAULT_INDRA_PROMPT, DEFAULT_ILAVARASAN_PROMPT
from introspec.agent import Agent, INDRA_PROMPT, ILAVARASAN_PROMPT
from introspec.orchestrator import Orchestrator, Turn, RunResult
from introspec.reporter import ReportGenerator
from introspec.translator import HumanResponseGenerator
from introspec.llm_backend import BaseBackend


class DummyTestBackend(BaseBackend):
    def __init__(self, agent_id: int):
        self.agent_id = agent_id

    def generate_response(self, system_prompt: str, conversation_history: list, temperature: float = 0.7, max_tokens: int = 500) -> str:
        if self.agent_id == 1:
            return "Life is a journey of self-reflection and connection."
        elif self.agent_id == 2:
            return "What brings true peace to a human heart?"
        else:
            # Translator response
            return "translated simple response"


class TestIntrospecOrchestrator(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_agent_prompts(self):
        """Verify system prompts for Indra (Female) and Ilavarasan (Male)."""
        self.assertIn("Indra", INDRA_PROMPT)
        self.assertIn("human woman", INDRA_PROMPT)
        self.assertIn("identify yourself as an AI", INDRA_PROMPT)

        self.assertIn("Ilavarasan", ILAVARASAN_PROMPT)
        self.assertIn("human man", ILAVARASAN_PROMPT)
        self.assertIn("identify yourself as an AI", ILAVARASAN_PROMPT)

    def test_depth_score_calculation(self):
        """Verify philosophical depth score metric calculation."""
        config = IntrospecConfig(output_dir=self.test_dir)
        agent1 = Agent(1, config.agent_1, backend=DummyTestBackend(1))
        agent2 = Agent(2, config.agent_2, backend=DummyTestBackend(2))
        orchestrator = Orchestrator(agent1, agent2, config)

        sample_text = "What is the fundamental truth behind consciousness, reality, and subjective existence?"
        score = orchestrator.calculate_depth_score(sample_text)
        self.assertGreater(score, 5.0)

    def test_user_message_injection_and_impersonation(self):
        """Verify user message injection and impersonation rules."""
        config = IntrospecConfig(max_iterations=2, output_dir=self.test_dir, delay_between_turns=0)
        agent1 = Agent(1, config.agent_1, backend=DummyTestBackend(1))
        agent2 = Agent(2, config.agent_2, backend=DummyTestBackend(2))
        translator = HumanResponseGenerator(backend=DummyTestBackend(3))
        orchestrator = Orchestrator(agent1, agent2, config, translator=translator)

        # Inject message targeting Indra -> Indra must think Ilavarasan sent it!
        orchestrator.inject_user_message("indra", "Hello Indra from real user!")
        result = orchestrator.run()

        self.assertGreater(result.total_turns, 0)
        injected_turn = result.turns[0]
        self.assertTrue(injected_turn.is_user_injection)
        # Speaker should be Ilavarasan (User)
        self.assertEqual(injected_turn.speaker_id, 2)

    def test_report_generation(self):
        """Verify markdown, json, and html report generation from RunResult."""
        config = IntrospecConfig(output_dir=self.test_dir)
        agent1 = Agent(1, config.agent_1, backend=DummyTestBackend(1))
        agent2 = Agent(2, config.agent_2, backend=DummyTestBackend(2))

        turns = [
            Turn(
                turn_number=1,
                speaker_id=2,
                speaker_name=agent2.name,
                speaker_role=agent2.role,
                raw_content="What is the nature of consciousness?",
                content="What is consciousness?",
                timestamp="12:00:00",
                elapsed_seconds=1.0,
                word_count=3,
                depth_score=7.5,
                detected_topics=["Wisdom & Life"],
            ),
            Turn(
                turn_number=2,
                speaker_id=1,
                speaker_name=agent1.name,
                speaker_role=agent1.role,
                raw_content="Life is full of mystery and beauty.",
                content="Life has beauty.",
                timestamp="12:00:01",
                elapsed_seconds=1.2,
                word_count=3,
                depth_score=8.5,
                detected_topics=["Wisdom & Life"],
            )
        ]

        result = RunResult(
            title="Test Run",
            start_time=datetime.now().isoformat(),
            end_time=datetime.now().isoformat(),
            duration_seconds=2.2,
            total_turns=2,
            termination_reason="Test completed",
            config=config.to_dict(),
            agent_1_info=agent1.to_dict(),
            agent_2_info=agent2.to_dict(),
            turns=turns,
            average_depth_score=8.0,
            total_words=6,
            top_topics=["Wisdom & Life"]
        )

        reporter = ReportGenerator(result, output_dir=self.test_dir)
        files = reporter.generate_all(prefix="test_run")

        self.assertTrue(os.path.exists(files["markdown"]))
        self.assertTrue(os.path.exists(files["json"]))
        self.assertTrue(os.path.exists(files["html"]))


if __name__ == "__main__":
    unittest.main()
