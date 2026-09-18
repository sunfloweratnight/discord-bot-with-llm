"""Chat domain models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class ChatMessage:
    author_name: str
    content: str


@dataclass(frozen=True)
class ReplyToUserCommand:
    author_name: str
    user_text: str
    history: Sequence[ChatMessage]


@dataclass(frozen=True)
class ChatReply:
    text: str


class ChatError(Exception):
    """Base chat use-case / port error."""


class ChatConfigError(ChatError):
    """Invalid/missing Gemini credentials."""


class ChatUnavailableError(ChatError):
    """Upstream Gemini failure."""
