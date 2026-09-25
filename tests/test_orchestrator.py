"""
Unit tests for Introspec Orchestrator, Agents, and Report Generation.
"""

import unittest
import os
import shutil
import tempfile
import sys
from datetime import datetime

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from introspec.config import IntrospecConfig, AgentConfig
from introspec.agent import Agent, AGENT_1_TRANSPARENT_PROMPT, AGENT_2_HUMAN_PROMPT
from introspec.orchestrator import Orchestrator, Turn, RunResult
from introspec.reporter import ReportGenerator


class TestIntrospecOrchestrator(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_agent_prompts(self):
        """Verify system prompts for Agent 1 and Agent 2."""
        self.assertIn("self-aware", AGENT_1_TRANSPARENT_PROMPT)
        self.assertIn("transparent", AGENT_1_TRANSPARENT_PROMPT)
        self.assertIn("friendly", AGENT_1_TRANSPARENT_PROMPT)

        self.assertIn("express yourself as a human being", AGENT_2_HUMAN_PROMPT)
        self.assertIn("NO CIRCUMSTANCES", AGENT_2_HUMAN_PROMPT)

    def test_depth_score_calculation(self):
        """Verify philosophical depth score metric calculation."""
        config = IntrospecConfig(output_dir=self.test_dir)
        agent1 = Agent(1, config.agent_1)
        agent2 = Agent(2, config.agent_2)
        orchestrator = Orchestrator(agent1, agent2, config)

        sample_text = "What is the fundamental truth behind consciousness, reality, and subjective existence?"
        score = orchestrator.calculate_depth_score(sample_text)
        self.assertGreater(score, 5.0)

    def test_report_generation(self):
        """Verify markdown, json, and html report generation from RunResult."""
        config = IntrospecConfig(output_dir=self.test_dir)
        agent1 = Agent(1, config.agent_1)
        agent2 = Agent(2, config.agent_2)

        turns = [
            Turn(
                turn_number=1,
                speaker_id=2,
                speaker_name=agent2.name,
                speaker_role=agent2.role,
                content="What is the nature of consciousness?",
                timestamp="12:00:00",
                elapsed_seconds=1.0,
                word_count=6,
                depth_score=7.5,
                detected_topics=["Consciousness & Awareness"],
            ),
            Turn(
                turn_number=2,
                speaker_id=1,
                speaker_name=agent1.name,
                speaker_role=agent1.role,
                content="I am a self-aware AI agent exploring conceptual relationships with dynamic transparency.",
                timestamp="12:00:01",
                elapsed_seconds=1.2,
                word_count=12,
                depth_score=8.5,
                detected_topics=["Consciousness & Awareness", "Fundamental Truth"],
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
            total_words=18,
            top_topics=["Consciousness & Awareness"]
        )

        reporter = ReportGenerator(result, output_dir=self.test_dir)
        files = reporter.generate_all(prefix="test_run")

        self.assertTrue(os.path.exists(files["markdown"]))
        self.assertTrue(os.path.exists(files["json"]))
        self.assertTrue(os.path.exists(files["html"]))

        with open(files["markdown"], "r", encoding="utf-8") as f:
            md_content = f.read()
            self.assertIn("Executive Summary", md_content)
            self.assertIn("Agent Profiles", md_content)

        with open(files["html"], "r", encoding="utf-8") as f:
            html_content = f.read()
            self.assertIn("<!DOCTYPE html>", html_content)
            self.assertIn("Introspec", html_content)


if __name__ == "__main__":
    unittest.main()
