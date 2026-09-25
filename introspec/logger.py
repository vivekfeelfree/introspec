"""
Structured Logging System for Introspec Orchestrator.
Logs timestamps, model invocations, latency, token metrics, finish reasons, and errors
to console and persistent file 'reports/introspec.log'.
"""

import os
import logging
from datetime import datetime
from typing import List, Dict, Any

LOG_FILE_PATH = os.path.join("reports", "introspec.log")


class IntrospecLogger:
    """Centralized logger for Introspec trials."""

    _logger_instance = None

    @classmethod
    def get_logger(cls) -> logging.Logger:
        if cls._logger_instance is None:
            os.makedirs("reports", exist_ok=True)
            logger = logging.getLogger("introspec")
            logger.setLevel(logging.INFO)

            # Prevent duplicate handlers
            if not logger.handlers:
                # File Handler
                file_handler = logging.FileHandler(LOG_FILE_PATH, encoding="utf-8")
                file_formatter = logging.Formatter(
                    "[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
                )
                file_handler.setFormatter(file_formatter)
                logger.addHandler(file_handler)

                # Console Handler
                console_handler = logging.StreamHandler()
                console_formatter = logging.Formatter("[introspec] %(message)s")
                console_handler.setFormatter(console_formatter)
                logger.addHandler(console_handler)

            cls._logger_instance = logger
        return cls._logger_instance

    @classmethod
    def log_turn_event(
        cls,
        turn_number: int,
        speaker_name: str,
        model_name: str,
        duration_sec: float,
        word_count: int,
        depth_score: float,
        finish_reason: str = "STOP",
    ):
        logger = cls.get_logger()
        msg = (
            f"Turn #{turn_number} | {speaker_name} | Model: {model_name} | "
            f"Latency: {duration_sec:.2f}s | Words: {word_count} | Depth: {depth_score}/10 | Finish: {finish_reason}"
        )
        logger.info(msg)

    @classmethod
    def log_api_call(cls, provider: str, model: str, status: str, details: str = ""):
        logger = cls.get_logger()
        msg = f"API Call -> Provider: {provider.upper()} | Model: {model} | Status: {status} {details}".strip()
        logger.info(msg)

    @classmethod
    def log_error(cls, context: str, error: Exception):
        logger = cls.get_logger()
        logger.error(f"Error in {context}: {str(error)}", exc_info=True)

    @classmethod
    def get_recent_logs(cls, max_lines: int = 100) -> List[str]:
        """Read recent logs from file."""
        if not os.path.exists(LOG_FILE_PATH):
            return ["No log file found yet."]
        try:
            with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()
                return [line.strip() for line in lines[-max_lines:]]
        except Exception as e:
            return [f"Error reading logs: {e}"]
