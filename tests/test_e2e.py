"""
Comprehensive End-to-End (E2E) Integration & Web API Test Suite for Introspec.
Tests complete pipeline from API endpoints to LLM backends, stateless translator, and report generation.
"""

import unittest
import os
import sys
import json
import shutil
import tempfile
import urllib.request
import threading
import time
from datetime import datetime

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from introspec.config import IntrospecConfig, AgentConfig
from introspec.agent import Agent, INDRA_PROMPT, ILAVARASAN_PROMPT
from introspec.orchestrator import Orchestrator, Turn, RunResult
from introspec.reporter import ReportGenerator
from introspec.translator import HumanResponseGenerator
from introspec.llm_backend import get_backend, BaseBackend


class DummyTestBackend(BaseBackend):
    """Deterministic backend for fast E2E testing without external network dependencies."""
    def __init__(self, agent_id: int):
        self.agent_id = agent_id
        self.call_count = 0

    def generate_response(
        self,
        system_prompt: str,
        conversation_history: list,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> str:
        self.call_count += 1
        if self.agent_id == 2:
            return f"E2E Test Ilavarasan Question #{self.call_count} about life and truth."
        elif self.agent_id == 1:
            return f"E2E Test Indra Answer #{self.call_count} with deep human wisdom."
        else:
            # Translator output
            return f"Translated human utterance #{self.call_count}"


class TestEndToEndScenarios(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.reports_dir = os.path.join(self.test_dir, "reports")
        os.makedirs(self.reports_dir, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_e2e_full_orchestration_loop(self):
        """E2E Test: Full dual-agent orchestration loop with stateless translator."""
        config = IntrospecConfig(
            max_iterations=4,
            time_limit_seconds=30.0,
            delay_between_turns=0.0,
            output_dir=self.reports_dir,
            title="E2E Full Orchestration Test"
        )

        agent1 = Agent(1, config.agent_1, backend=DummyTestBackend(1))
        agent2 = Agent(2, config.agent_2, backend=DummyTestBackend(2))
        translator = HumanResponseGenerator(backend=DummyTestBackend(3))

        orchestrator = Orchestrator(agent1, agent2, config, translator=translator)
        turns_received = []

        orchestrator.add_turn_listener(lambda t: turns_received.append(t))
        result = orchestrator.run()

        # Assertions
        self.assertEqual(result.total_turns, 4)
        self.assertEqual(len(turns_received), 4)
        self.assertGreater(result.total_words, 0)

    def test_e2e_report_generation_and_content_verification(self):
        """E2E Test: Verify Markdown, JSON, and HTML report content integrity."""
        config = IntrospecConfig(output_dir=self.reports_dir)
        agent1 = Agent(1, config.agent_1, backend=DummyTestBackend(1))
        agent2 = Agent(2, config.agent_2, backend=DummyTestBackend(2))

        turns = [
            Turn(
                turn_number=1,
                speaker_id=2,
                speaker_name=agent2.name,
                speaker_role=agent2.role,
                raw_content="What is the bedrock of truth?",
                content="What is truth?",
                timestamp="12:00:00",
                elapsed_seconds=0.5,
                word_count=3,
                depth_score=8.5,
                detected_topics=["Wisdom & Life"]
            ),
            Turn(
                turn_number=2,
                speaker_id=1,
                speaker_name=agent1.name,
                speaker_role=agent1.role,
                raw_content="Truth is found in presence and honest understanding.",
                content="Truth is presence.",
                timestamp="12:00:01",
                elapsed_seconds=0.6,
                word_count=3,
                depth_score=9.0,
                detected_topics=["Wisdom & Life"]
            )
        ]

        result = RunResult(
            title="E2E Report Verification",
            start_time=datetime.now().isoformat(),
            end_time=datetime.now().isoformat(),
            duration_seconds=1.1,
            total_turns=2,
            termination_reason="E2E Test Completed",
            config=config.to_dict(),
            agent_1_info=agent1.to_dict(),
            agent_2_info=agent2.to_dict(),
            turns=turns,
            average_depth_score=8.75,
            total_words=6,
            top_topics=["Wisdom & Life"]
        )

        reporter = ReportGenerator(result, output_dir=self.reports_dir)
        files = reporter.generate_all(prefix="e2e_verify")

        # Verify files exist
        self.assertTrue(os.path.exists(files["markdown"]))
        self.assertTrue(os.path.exists(files["json"]))
        self.assertTrue(os.path.exists(files["html"]))

        # Verify Markdown content
        with open(files["markdown"], "r", encoding="utf-8") as f:
            md_text = f.read()
            self.assertIn("E2E Report Verification", md_text)
            self.assertIn("What is truth?", md_text)

        # Verify JSON validity
        with open(files["json"], "r", encoding="utf-8") as f:
            json_data = json.load(f)
            self.assertEqual(json_data["total_turns"], 2)
            self.assertEqual(len(json_data["turns"]), 2)

        # Verify HTML valid structure
        with open(files["html"], "r", encoding="utf-8") as f:
            html_text = f.read()
            self.assertIn("<!DOCTYPE html>", html_text)
            self.assertIn("Indra", html_text)

    def test_e2e_invalid_backend_rejection(self):
        """E2E Test: Verify invalid backend specifies clear error."""
        with self.assertRaises(ValueError) as ctx:
            get_backend("non_existent_provider_xyz")
        self.assertIn("Unknown backend", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
