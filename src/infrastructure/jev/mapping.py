"""Map domain decision DTOs to/from typesafe_sdk types."""

from __future__ import annotations

from typing import Any, Mapping

from typesafe_sdk import Choice, Noul, Score

from src.domain.decision.models import (
    Answer,
    ChoiceAnswer,
    ChoiceQuestion,
    NoulAnswer,
    NoulQuestion,
    Question,
    ScoreAnswer,
    ScoreQuestion,
)


def to_sdk_questions(questions: Mapping[str, Question]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, question in questions.items():
        if isinstance(question, ChoiceQuestion):
            out[key] = Choice(
                instructions=question.instructions,
                criteria=dict(question.criteria),
            )
        elif isinstance(question, ScoreQuestion):
            out[key] = Score(
                instructions=question.instructions,
                criteria=list(question.criteria),
            )
        elif isinstance(question, NoulQuestion):
            out[key] = Noul(instructions=question.instructions)
        else:
            raise TypeError(f"unsupported question type: {type(question)!r}")
    return out


def _prob_map(raw: Any) -> dict[str, float]:
    if not isinstance(raw, Mapping):
        return {}
    out: dict[str, float] = {}
    for key, value in raw.items():
        try:
            out[str(key)] = float(value)
        except (TypeError, ValueError):
            continue
    return out


def from_sdk_answers(answers: Mapping[str, Any]) -> dict[str, Answer]:
    out: dict[str, Answer] = {}
    for key, answer in answers.items():
        if hasattr(answer, "choice"):
            conf = getattr(answer, "confidence", None)
            try:
                confidence = float(conf) if conf is not None else None
            except (TypeError, ValueError):
                confidence = None
            out[key] = ChoiceAnswer(
                choice=str(getattr(answer, "choice", "") or "不明"),
                confidence=confidence,
                probabilities=_prob_map(getattr(answer, "probabilities", None)),
            )
        elif hasattr(answer, "noul") and not hasattr(answer, "score"):
            try:
                noul = float(getattr(answer, "noul", 0.0))
            except (TypeError, ValueError):
                noul = 0.0
            out[key] = NoulAnswer(noul=noul)
        elif hasattr(answer, "score"):
            score_raw = getattr(answer, "score", None)
            conf = getattr(answer, "confidence", None)
            try:
                score = float(score_raw) if score_raw is not None else None
            except (TypeError, ValueError):
                score = None
            try:
                confidence = float(conf) if conf is not None else None
            except (TypeError, ValueError):
                confidence = None
            out[key] = ScoreAnswer(
                score=score,
                legend=getattr(answer, "legend", None),
                confidence=confidence,
                probabilities=_prob_map(getattr(answer, "probabilities", None)),
            )
        else:
            raise TypeError(f"unsupported answer payload for {key}: {type(answer)!r}")
    return out
