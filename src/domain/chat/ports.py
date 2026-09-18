"""Port for LLM chat backends."""

from __future__ import annotations

from typing import Protocol

from src.domain.chat.models import ChatReply


class ChatPort(Protocol):
    async def generate(self, prompt: str) -> ChatReply:
        """Generate a reply for a fully assembled prompt string."""
