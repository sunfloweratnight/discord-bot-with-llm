"""Domain DTOs for structured decisions (System One / Jev-compatible, SDK-free)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence, Union

JSONState = Union[str, Mapping[str, Any], Sequence[Any]]


@dataclass(frozen=True)
class ChoiceQuestion:
    instructions: str
    criteria: Mapping[str, str]


@dataclass(frozen=True)
class ScoreQuestion:
    instructions: str
    criteria: Sequence[str]


@dataclass(frozen=True)
class NoulQuestion:
    instructions: str


Question = Union[ChoiceQuestion, ScoreQuestion, NoulQuestion]


@dataclass(frozen=True)
class DecisionRequest:
    state: JSONState
    questions: Mapping[str, Question]


@dataclass(frozen=True)
class ChoiceAnswer:
    choice: str
    confidence: float | None = None
    probabilities: Mapping[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class ScoreAnswer:
    score: float | None = None
    legend: Any = None
    confidence: float | None = None
    probabilities: Mapping[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class NoulAnswer:
    noul: float = 0.0


Answer = Union[ChoiceAnswer, ScoreAnswer, NoulAnswer]


@dataclass(frozen=True)
class DecisionResponse:
    answers: Mapping[str, Answer]


class DecisionError(Exception):
    """Base error from a DecisionPort implementation."""


class DecisionConfigError(DecisionError):
    """Missing/invalid credentials or local configuration."""


class DecisionUnavailableError(DecisionError):
    """Upstream failure (timeout, 5xx, unexpected)."""
