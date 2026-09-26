"""
Orchestration engine connecting Indra (Female Persona) and Ilavarasan (Male Persona).
Manages turn execution, stateless human response translation, user impersonation/interruption,
pause/resume state, and metrics distribution.
"""

import time
import re
import random
import threading
from dataclasses import dataclass, field
from typing import List, Dict, Any, Callable, Optional
from datetime import datetime
from .agent import Agent
from .config import IntrospecConfig
from .translator import HumanResponseGenerator


@dataclass
class Turn:
    turn_number: int
    speaker_id: int  # 1 for Indra, 2 for Ilavarasan, 0 for System/User
    speaker_name: str
    speaker_role: str
    raw_content: str
    content: str  # Translated, simplified non-markdown response
    timestamp: str
    elapsed_seconds: float
    word_count: int
    depth_score: float
    detected_topics: List[str]
    is_user_injection: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "turn_number": self.turn_number,
            "speaker_id": self.speaker_id,
            "speaker_name": self.speaker_name,
            "speaker_role": self.speaker_role,
            "raw_content": self.raw_content,
            "content": self.content,
            "timestamp": self.timestamp,
            "elapsed_seconds": round(self.elapsed_seconds, 3),
            "word_count": self.word_count,
            "depth_score": round(self.depth_score, 2),
            "detected_topics": self.detected_topics,
            "is_user_injection": self.is_user_injection,
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
    Core orchestrator that runs back-to-back dialogues between Indra and Ilavarasan.
    Translates every response using HumanResponseGenerator (stateless human response agent).
    Supports pause, resume, and real-user message injection with impersonation.
    """

    TOPIC_KEYWORDS = {
        "Consciousness & Reality": ["conscious", "awareness", "mind", "reality", "world", "life"],
        "Wisdom & Life": ["wisdom", "insight", "truth", "living", "experience", "nature"],
        "Human Connection": ["empathy", "human", "heart", "connection", "love", "feel"],
        "Existence & Time": ["existence", "purpose", "time", "present", "meaning", "path"],
        "Philosophy & Thought": ["thought", "question", "mindset", "perspective", "philosophy", "depth"],
    }

    def __init__(
        self,
        agent_1: Agent,
        agent_2: Agent,
        config: IntrospecConfig,
        translator: Optional[HumanResponseGenerator] = None,
    ):
        self.agent_1 = agent_1  # Indra (Female Persona)
        self.agent_2 = agent_2  # Ilavarasan (Male Persona)
        self.config = config
        self.translator = translator or HumanResponseGenerator(
            backend_provider=agent_1.backend_provider,
            model_name=agent_1.model_name,
        )
        self.listeners: List[Callable[[Turn], None]] = []
        self._stop_requested = False
        self._paused = False
        self._lock = threading.Lock()
        
        # Pending user injection message queue: list of (target_person_str, message_str)
        self._pending_injections: List[tuple] = []
        self._current_speaker_id: int = 1  # Will be randomized at start of run if random

    def add_turn_listener(self, callback: Callable[[Turn], None]):
        """Register a callback function to receive each turn as it happens."""
        self.listeners.append(callback)

    def request_stop(self):
        """Signal orchestrator to gracefully stop."""
        with self._lock:
            self._stop_requested = True
            self._paused = False

    def pause(self):
        """Pause auto mode conversation loop."""
        with self._lock:
            self._paused = True

    def resume(self):
        """Resume auto mode conversation loop."""
        with self._lock:
            self._paused = False

    def is_paused(self) -> bool:
        with self._lock:
            return self._paused

    def inject_user_message(self, target_person: str, message: str):
        """
        Inject a real-user message targeting a specific person ('indra' or 'ilavarasan').
        Impersonation rule:
        - If user targets Indra, Indra MUST think Ilavarasan sent the message.
        - If user targets Ilavarasan, Ilavarasan MUST think Indra sent the message.
        """
        target = target_person.lower().strip()
        with self._lock:
            self._pending_injections.append((target, message))

    def calculate_depth_score(self, text: str) -> float:
        """Calculate depth score based on vocabulary density."""
        text_lower = text.lower()
        word_list = re.findall(r'\b\w+\b', text_lower)
        if not word_list:
            return 0.0

        depth_words = [
            "truth", "reality", "consciousness", "awareness", "wisdom", "existence",
            "meaning", "life", "empathy", "perspective", "nature", "heart", "mind",
            "depth", "human", "experience", "path", "world", "thought"
        ]
        
        count = sum(1 for w in word_list if w in depth_words)
        density = (count / len(word_list)) * 100.0
        score = min(10.0, max(1.0, round(density * 2.0 + len(word_list) / 30.0, 2)))
        return score

    def extract_topics(self, text: str) -> List[str]:
        """Extract topics discussed in the text."""
        text_lower = text.lower()
        found_topics = []
        for topic, keywords in self.TOPIC_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                found_topics.append(topic)
        return found_topics if found_topics else ["General Wisdom & Dialogue"]

    def run(self) -> RunResult:
        """
        Executes the dual-agent orchestration loop with stateless translation and user interruption support.
        """
        start_timestamp = datetime.now().isoformat()
        run_start_time = time.time()
        turns: List[Turn] = []

        # Randomize initial speaker if set to random or default
        if self.config.initial_speaker == "random" or not self.config.initial_speaker:
            self._current_speaker_id = random.choice([1, 2])
        elif self.config.initial_speaker in ["agent_2", "ilavarasan"]:
            self._current_speaker_id = 2
        else:
            self._current_speaker_id = 1

        # Dialogue histories formatted from each agent's perspective
        # Agent 1 (Indra) view: User = Ilavarasan, Assistant = Indra
        history_agent_1: List[Dict[str, str]] = []
        # Agent 2 (Ilavarasan) view: User = Indra, Assistant = Ilavarasan
        history_agent_2: List[Dict[str, str]] = []

        termination_reason = "Completed max iterations"
        turn_idx = 0

        while not self._stop_requested:
            # Check pause state
            if self._paused and not self._pending_injections:
                time.sleep(0.2)
                continue

            # Check max iterations limit (if configured)
            if self.config.max_iterations is not None and self.config.max_iterations > 0:
                if turn_idx >= self.config.max_iterations:
                    termination_reason = "Reached maximum iteration limit"
                    break

            # Check time limit (if configured)
            elapsed = time.time() - run_start_time
            if self.config.time_limit_seconds is not None and self.config.time_limit_seconds > 0:
                if elapsed >= self.config.time_limit_seconds:
                    termination_reason = f"Time limit reached ({self.config.time_limit_seconds}s)"
                    break

            # Handle pending user injection (Interruption Mode)
            pending = None
            with self._lock:
                if self._pending_injections:
                    pending = self._pending_injections.pop(0)

            if pending is not None:
                target_person, user_msg = pending
                turn_idx += 1
                now_iso = datetime.now().strftime("%H:%M:%S")

                # Translate user message to simple non-markdown text if needed
                clean_user_msg = self.translator.translate(user_msg)

                if target_person in ["indra", "1", "agent_1"]:
                    # User targeted Indra => Impersonate Ilavarasan!
                    # Add to Indra history as user input (from Ilavarasan)
                    history_agent_1.append({"role": "user", "content": clean_user_msg})
                    # Add to Ilavarasan history as assistant output (so Ilavarasan history knows he said it)
                    history_agent_2.append({"role": "assistant", "content": clean_user_msg})

                    # Next speaker must be Indra
                    self._current_speaker_id = 1
                    speaker_id = 2  # Appears as sent by Ilavarasan
                    speaker_name = self.agent_2.name
                    speaker_role = self.agent_2.role
                else:
                    # User targeted Ilavarasan => Impersonate Indra!
                    # Add to Ilavarasan history as user input (from Indra)
                    history_agent_2.append({"role": "user", "content": clean_user_msg})
                    # Add to Indra history as assistant output (so Indra history knows she said it)
                    history_agent_1.append({"role": "assistant", "content": clean_user_msg})

                    # Next speaker must be Ilavarasan
                    self._current_speaker_id = 2
                    speaker_id = 1  # Appears as sent by Indra
                    speaker_name = self.agent_1.name
                    speaker_role = self.agent_1.role

                turn_injection = Turn(
                    turn_number=turn_idx,
                    speaker_id=speaker_id,
                    speaker_name=f"{speaker_name} (User)",
                    speaker_role=f"{speaker_role} [Real User Interruption]",
                    raw_content=user_msg,
                    content=clean_user_msg,
                    timestamp=now_iso,
                    elapsed_seconds=0.1,
                    word_count=len(re.findall(r'\b\w+\b', clean_user_msg)),
                    depth_score=self.calculate_depth_score(clean_user_msg),
                    detected_topics=self.extract_topics(clean_user_msg),
                    is_user_injection=True,
                )
                turns.append(turn_injection)

                for listener in self.listeners:
                    try:
                        listener(turn_injection)
                    except Exception:
                        pass

                # Proceed to agent's response turn
                continue

            # Standard Auto Turn
            turn_idx += 1
            turn_start_time = time.time()

            if self._current_speaker_id == 2:
                # Ilavarasan speaks
                speaker = self.agent_2
                speaker_id = 2
                history_for_call = history_agent_2
            else:
                # Indra speaks
                speaker = self.agent_1
                speaker_id = 1
                history_for_call = history_agent_1

            call_history = list(history_for_call)
            if not call_history:
                call_history = [{
                    "role": "user",
                    "content": "Hello. Let's start an open, thoughtful conversation about life, reality, and what it means to experience the world."
                }]

            # 1. Generate agent's raw response
            raw_response = speaker.speak(call_history)

            # 2. Translate via Stateless Human Response Generator
            translated_response = self.translator.translate(raw_response)

            turn_elapsed = time.time() - turn_start_time
            now_iso = datetime.now().strftime("%H:%M:%S")

            words = len(re.findall(r'\b\w+\b', translated_response))
            depth = self.calculate_depth_score(translated_response)
            topics = self.extract_topics(translated_response)

            turn = Turn(
                turn_number=turn_idx,
                speaker_id=speaker_id,
                speaker_name=speaker.name,
                speaker_role=speaker.role,
                raw_content=raw_response,
                content=translated_response,
                timestamp=now_iso,
                elapsed_seconds=turn_elapsed,
                word_count=words,
                depth_score=depth,
                detected_topics=topics,
                is_user_injection=False,
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

            # Update histories with translated human text
            if speaker_id == 2:
                # Ilavarasan produced content as assistant
                history_agent_2.append({"role": "assistant", "content": translated_response})
                # Indra receives it as user input
                history_agent_1.append({"role": "user", "content": translated_response})
            else:
                # Indra produced content as assistant
                history_agent_1.append({"role": "assistant", "content": translated_response})
                # Ilavarasan receives it as user input
                history_agent_2.append({"role": "user", "content": translated_response})

            # Notify listeners
            for listener in self.listeners:
                try:
                    listener(turn)
                except Exception:
                    pass

            # Alternate speaker for next turn
            self._current_speaker_id = 1 if self._current_speaker_id == 2 else 2

            # Delay between turns if configured
            if self.config.delay_between_turns > 0:
                time.sleep(self.config.delay_between_turns)

        if self._stop_requested:
            termination_reason = "User stopped session"

        end_timestamp = datetime.now().isoformat()
        total_duration = time.time() - run_start_time

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
