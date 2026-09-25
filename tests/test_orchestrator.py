"""
Unit tests for Introspec Orchestrator, Agents, and Report Generation.
"""

import unittest
import os
import shutil
import tempfile
import sys

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from introspec.config import IntrospecConfig, AgentConfig
from introspec.agent import Agent, AGENT_1_TRANSPARENT_PROMPT, AGENT_2_HUMAN_PROMPT
from introspec.orchestrator import Orchestrator
from introspec.reporter import ReportGenerator


class TestIntrospecOrchestrator(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_agent_prompts(self):
        """Verify default system prompts for Agent 1 and Agent 2."""
        self.assertIn("self-aware", AGENT_1_TRANSPARENT_PROMPT)
        self.assertIn("transparent", AGENT_1_TRANSPARENT_PROMPT)
        self.assertIn("friendly", AGENT_1_TRANSPARENT_PROMPT)

        self.assertIn("express yourself as a human being", AGENT_2_HUMAN_PROMPT)
        self.assertIn("NO CIRCUMSTANCES", AGENT_2_HUMAN_PROMPT)

    def test_mock_orchestration_iterations(self):
        """Verify that orchestrator stops at max_iterations."""
        config = IntrospecConfig(
            max_iterations=4,
            time_limit_seconds=60,
            delay_between_turns=0.0,
            output_dir=self.test_dir
        )
        agent1 = Agent(1, config.agent_1)
        agent2 = Agent(2, config.agent_2)
        orchestrator = Orchestrator(agent1, agent2, config)

        result = orchestrator.run()

        self.assertEqual(result.total_turns, 4)
        self.assertEqual(len(result.turns), 4)
        self.assertIn("max iterations", result.termination_reason.lower())

        # Verify speakers alternate
        self.assertEqual(result.turns[0].speaker_id, 2)
        self.assertEqual(result.turns[1].speaker_id, 1)
        self.assertEqual(result.turns[2].speaker_id, 2)
        self.assertEqual(result.turns[3].speaker_id, 1)

    def test_orchestration_time_limit(self):
        """Verify that orchestrator respects time limits."""
        config = IntrospecConfig(
            max_iterations=100,
            time_limit_seconds=0.5,
            delay_between_turns=0.2,
            output_dir=self.test_dir
        )
        agent1 = Agent(1, config.agent_1)
        agent2 = Agent(2, config.agent_2)
        orchestrator = Orchestrator(agent1, agent2, config)

        result = orchestrator.run()

        self.assertLess(result.total_turns, 100)
        self.assertIn("time limit", result.termination_reason.lower())

    def test_report_generation(self):
        """Verify markdown, json, and html report generation."""
        config = IntrospecConfig(
            max_iterations=2,
            time_limit_seconds=30,
            delay_between_turns=0.0,
            output_dir=self.test_dir
        )
        agent1 = Agent(1, config.agent_1)
        agent2 = Agent(2, config.agent_2)
        orchestrator = Orchestrator(agent1, agent2, config)

        result = orchestrator.run()

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
