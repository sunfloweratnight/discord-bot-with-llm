"""Fortune domain models and errors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class TellFortuneCommand:
    user_id: int
    display_name: str
    channel_id: int
    channel_name: str
    recent_messages: Sequence[str]
    note: str = ""


@dataclass(frozen=True)
class ChoicePick:
    label: str
    probability: float | None = None
    confidence: float | None = None


@dataclass(frozen=True)
class FortuneResult:
    overall: ChoicePick
    overall_top: tuple[tuple[str, float], ...]
    love: ChoicePick
    work: ChoicePick
    money: ChoicePick
    health: ChoicePick
    mood_label: str
    mood_score: float | None
    mood_confidence: float | None
    caution: float
    advice: ChoicePick
    lucky_color: ChoicePick
    lucky_item: ChoicePick
    lucky_food: ChoicePick
    lucky_number: ChoicePick


class FortuneError(Exception):
    """Base fortune use-case error."""


class InsufficientHistoryError(FortuneError):
    """Not enough author messages to judge fortune."""
