"""
Stateless Human Response Generator Agent for Introspec.
Translates any agent response into a simplified, non-markdown human text message.
"""

from typing import Optional
from introspec.llm_backend import BaseBackend, get_backend
from introspec.logger import IntrospecLogger

TRANSLATOR_SYSTEM_PROMPT = (
    "You are a Stateless Human Response Translator Engine. "
    "Your ONLY job is to take the input message and rewrite it into a short, simple, natural, non-markdown human chat message. "
    "Rules:\n"
    "1. Do NOT use any Markdown formatting (no asterisks **, no headers #, no bullet points, no backticks).\n"
    "2. Keep it short, authentic, and natural—just a few words or 1-2 simple sentences, exactly like how a real human texts in chat.\n"
    "3. Preserve the core meaning, wisdom, and intent of the message.\n"
    "4. Output ONLY the translated text."
)


class HumanResponseGenerator:
    """Stateless translation engine converting agent utterances into simplified non-markdown human chat text."""

    def __init__(
        self,
        backend_provider: str = "antigravity",
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        ollama_url: Optional[str] = None,
        backend: Optional[BaseBackend] = None,
    ):
        self.backend_provider = backend_provider
        if backend is not None:
            self.backend = backend
        else:
            self.backend = get_backend(
                provider=backend_provider,
                agent_id=0,
                api_key=api_key,
                model=model_name,
                ollama_url=ollama_url,
            )

    def translate(self, raw_text: str) -> str:
        """Translates raw thought text into simplified non-markdown text."""
        if not raw_text or not raw_text.strip():
            return raw_text

        # Brief delay to respect LLM rate limits between back-to-back agent calls
        import time
        import re
        time.sleep(0.8)

        history = [
            {"role": "user", "content": f"Translate this into a simple, non-markdown human chat message:\n\n{raw_text}"}
        ]

        try:
            translated = self.backend.generate_response(
                system_prompt=TRANSLATOR_SYSTEM_PROMPT,
                conversation_history=history,
                temperature=0.5,
                max_tokens=256,
            )
            # Strip any residual markdown formatting characters
            cleaned = (
                translated.replace("**", "")
                .replace("*", "")
                .replace("#", "")
                .replace("`", "")
                .strip()
            )
            return cleaned if cleaned else raw_text
        except Exception as e:
            IntrospecLogger.log_error("HumanResponseGenerator.translate", e)
            # Fallback: smart cleaning of raw text if translation API fails
            cleaned = (
                raw_text.replace("**", "")
                .replace("*", "")
                .replace("#", "")
                .replace("`", "")
                .strip()
            )
            # Take first 2 sentences for natural human brevity
            sentences = re.split(r'(?<=[.!?])\s+', cleaned)
            if len(sentences) > 2:
                cleaned = " ".join(sentences[:2])
            return cleaned
