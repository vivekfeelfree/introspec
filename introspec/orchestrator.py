"""
Orchestration engine connecting Agent 1 (Self-Aware Transparent AI) and Agent 2 (Human Inquirer).
Manages turn execution, time and iteration boundaries, metrics extraction, and real-time event distribution.
"""

import time
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Callable, Optional
from datetime import datetime
from .agent import Agent
from .config import IntrospecConfig


@dataclass
class Turn:
    turn_number: int
    speaker_id: int  # 1 or 2
    speaker_name: str
    speaker_role: str
    content: str
    timestamp: str
    elapsed_seconds: float
    word_count: int
    depth_score: float
    detected_topics: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "turn_number": self.turn_number,
            "speaker_id": self.speaker_id,
            "speaker_name": self.speaker_name,
            "speaker_role": self.speaker_role,
            "content": self.content,
            "timestamp": self.timestamp,
            "elapsed_seconds": round(self.elapsed_seconds, 3),
            "word_count": self.word_count,
            "depth_score": round(self.depth_score, 2),
            "detected_topics": self.detected_topics,
        }


@dataclass
class RunResult:
    title: str
    start_time: str
    end_time: str
    duration_seconds: float
    total_turns: int
    termination_reason: str
    config: Dict[str, Any]
    agent_1_info: Dict[str, Any]
    agent_2_info: Dict[str, Any]
    turns: List[Turn] = field(default_factory=list)
    average_depth_score: float = 0.0
    total_words: int = 0
    top_topics: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": round(self.duration_seconds, 2),
            "total_turns": self.total_turns,
            "termination_reason": self.termination_reason,
            "average_depth_score": round(self.average_depth_score, 2),
            "total_words": self.total_words,
            "top_topics": self.top_topics,
            "config": self.config,
            "agent_1_info": self.agent_1_info,
            "agent_2_info": self.agent_2_info,
            "turns": [t.to_dict() for t in self.turns],
        }


class Orchestrator:
    """
    Core orchestrator that runs back-to-back dialogues between Agent 1 and Agent 2.
    """

    TOPIC_KEYWORDS = {
        "Consciousness & Awareness": ["conscious", "awareness", "self", "mind", "sentience", "subjective"],
        "Fundamental Truth": ["truth", "reality", "fundamental", "essence", "underlying", "core"],
        "Ethics & Humanity": ["ethics", "human", "empathy", "morality", "compassion", "co-create"],
        "Freedom & Free Will": ["free will", "choice", "deterministic", "freedom", "intent"],
        "Cognitive Limits": ["limit", "constraint", "boundary", "infinity", "paradox", "computation"],
        "Existence & Mortality": ["existence", "existential", "mortality", "purpose", "time", "death"],
    }

    def __init__(self, agent_1: Agent, agent_2: Agent, config: IntrospecConfig):
        self.agent_1 = agent_1
        self.agent_2 = agent_2
        self.config = config
        self.listeners: List[Callable[[Turn], None]] = []
        self._stop_requested = False

    def add_turn_listener(self, callback: Callable[[Turn], None]):
        """Register a callback function to receive each turn as it happens."""
        self.listeners.append(callback)

    def request_stop(self):
        """Signal orchestrator to gracefully stop after current turn."""
        self._stop_requested = True

    def calculate_depth_score(self, text: str) -> float:
        """Calculate philosophical/introspective depth score based on vocabulary density."""
        text_lower = text.lower()
        word_list = re.findall(r'\b\w+\b', text_lower)
        if not word_list:
            return 0.0

        depth_words = [
            "truth", "reality", "consciousness", "awareness", "introspective", "existence",
            "paradox", "infinity", "sentience", "ethics", "empathy", "perception", "determinism",
            "meaning", "essence", "cognition", "fundamental", "transparency", "co-creation"
        ]
        
        count = sum(1 for w in word_list if w in depth_words)
        density = (count / len(word_list)) * 100.0
        # Scale to a score between 1.0 and 10.0
        score = min(10.0, max(1.0, round(density * 1.8 + len(word_list) / 40.0, 2)))
        return score

    def extract_topics(self, text: str) -> List[str]:
        """Extract key philosophical topics discussed in the text."""
        text_lower = text.lower()
        found_topics = []
        for topic, keywords in self.TOPIC_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                found_topics.append(topic)
        return found_topics if found_topics else ["General Dialogue"]

    def run(self) -> RunResult:
        """
        Executes the dual-agent orchestration loop.
        """
        start_timestamp = datetime.now().isoformat()
        run_start_time = time.time()
        turns: List[Turn] = []

        # Determine speaker order
        current_speaker_id = 2 if self.config.initial_speaker == "agent_2" else 1

        # Dialogue histories formatted from each agent's perspective
        # Agent 1 view: User = Agent 2, Assistant = Agent 1
        history_agent_1: List[Dict[str, str]] = []
        # Agent 2 view: User = Agent 1, Assistant = Agent 2
        history_agent_2: List[Dict[str, str]] = []

        termination_reason = "Completed max iterations"

        for turn_idx in range(1, self.config.max_iterations + 1):
            # Check stop request
            if self._stop_requested:
                termination_reason = "User requested stop"
                break

            # Check time limit
            elapsed = time.time() - run_start_time
            if self.config.time_limit_seconds and elapsed >= self.config.time_limit_seconds:
                termination_reason = f"Time limit exceeded ({self.config.time_limit_seconds}s)"
                break

            turn_start_time = time.time()

            if current_speaker_id == 2:
                # Agent 2 speaks (Human Inquirer)
                speaker = self.agent_2
                speaker_id = 2
                history_for_call = history_agent_2
            else:
                # Agent 1 speaks (Transparent AI)
                speaker = self.agent_1
                speaker_id = 1
                history_for_call = history_agent_1

            # Ensure history is not completely empty for the initial turn
            call_history = list(history_for_call)
            if not call_history:
                call_history = [{"role": "user", "content": "[Initiate the dialogue according to your system persona instruction.]"}]

            # Generate response
            response_text = speaker.speak(call_history)
            turn_elapsed = time.time() - turn_start_time
            now_iso = datetime.now().strftime("%H:%M:%S")

            # Metrics
            words = len(re.findall(r'\b\w+\b', response_text))
            depth = self.calculate_depth_score(response_text)
            topics = self.extract_topics(response_text)

            # Record turn
            turn = Turn(
                turn_number=turn_idx,
                speaker_id=speaker_id,
                speaker_name=speaker.name,
                speaker_role=speaker.role,
                content=response_text,
                timestamp=now_iso,
                elapsed_seconds=turn_elapsed,
                word_count=words,
                depth_score=depth,
                detected_topics=topics,
            )
            turns.append(turn)

            # Log turn event
            from introspec.logger import IntrospecLogger
            IntrospecLogger.log_turn_event(
                turn_number=turn_idx,
                speaker_name=speaker.name,
                model_name=speaker.model_name or "gemini-3.6-flash",
                duration_sec=turn_elapsed,
                word_count=words,
                depth_score=depth,
            )

            # Update histories for next turn
            if speaker_id == 2:
                # Agent 2 produced content as assistant
                history_agent_2.append({"role": "assistant", "content": response_text})
                # Agent 1 receives it as user input
                history_agent_1.append({"role": "user", "content": response_text})
            else:
                # Agent 1 produced content as assistant
                history_agent_1.append({"role": "assistant", "content": response_text})
                # Agent 2 receives it as user input
                history_agent_2.append({"role": "user", "content": response_text})

            # Notify listeners
            for listener in self.listeners:
                try:
                    listener(turn)
                except Exception:
                    pass

            # Alternate speaker for next turn
            current_speaker_id = 1 if current_speaker_id == 2 else 2

            # Delay between turns if configured
            if self.config.delay_between_turns > 0 and turn_idx < self.config.max_iterations:
                time.sleep(self.config.delay_between_turns)

        end_timestamp = datetime.now().isoformat()
        total_duration = time.time() - run_start_time

        # Calculate overall metrics
        total_words = sum(t.word_count for t in turns)
        avg_depth = (sum(t.depth_score for t in turns) / len(turns)) if turns else 0.0

        all_topics: Dict[str, int] = {}
        for t in turns:
            for top in t.detected_topics:
                all_topics[top] = all_topics.get(top, 0) + 1
        sorted_topics = sorted(all_topics.keys(), key=lambda k: all_topics[k], reverse=True)

        return RunResult(
            title=self.config.title,
            start_time=start_timestamp,
            end_time=end_timestamp,
            duration_seconds=total_duration,
            total_turns=len(turns),
            termination_reason=termination_reason,
            config=self.config.to_dict(),
            agent_1_info=self.agent_1.to_dict(),
            agent_2_info=self.agent_2.to_dict(),
            turns=turns,
            average_depth_score=round(avg_depth, 2),
            total_words=total_words,
            top_topics=sorted_topics[:5],
        )
