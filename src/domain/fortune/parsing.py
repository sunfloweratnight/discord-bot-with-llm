"""Parse DecisionPort answers into FortuneResult (pure, SDK-free)."""

from __future__ import annotations

from typing import Any, Mapping

from src.domain.decision.models import Answer, ChoiceAnswer, NoulAnswer, ScoreAnswer
from src.domain.fortune.models import ChoicePick, FortuneResult
from src.domain.fortune.questions import MOOD_LEVELS


def _as_prob_map(probabilities: Any) -> dict[str, float]:
    if not isinstance(probabilities, Mapping):
        return {}
    out: dict[str, float] = {}
    for key, value in probabilities.items():
        try:
            out[str(key)] = float(value)
        except (TypeError, ValueError):
            continue
    return out


def _choice_pick(answer: Answer | Any) -> tuple[ChoicePick, dict[str, float]]:
    if isinstance(answer, ChoiceAnswer):
        label = answer.choice or "不明"
        probs = _as_prob_map(answer.probabilities)
        return (
            ChoicePick(
                label=label,
                probability=probs.get(label),
                confidence=answer.confidence,
            ),
            probs,
        )
    label = str(getattr(answer, "choice", None) or "不明")
    probs = _as_prob_map(getattr(answer, "probabilities", None))
    confidence_raw = getattr(answer, "confidence", None)
    try:
        confidence = float(confidence_raw) if confidence_raw is not None else None
    except (TypeError, ValueError):
        confidence = None
    return (
        ChoicePick(label=label, probability=probs.get(label), confidence=confidence),
        probs,
    )


def _top_probabilities(
    probs: Mapping[str, float], *, limit: int = 3
) -> tuple[tuple[str, float], ...]:
    ranked = sorted(probs.items(), key=lambda kv: kv[1], reverse=True)
    return tuple(ranked[:limit])


def _legend_to_label(legend: Any, score: float | None) -> str | None:
    if legend is None:
        return None
    if isinstance(legend, str):
        text = legend.strip()
        return text or None
    if isinstance(legend, Mapping):
        if score is not None:
            idx = int(round(float(score)))
            for key in (idx, idx - 1, str(idx), str(idx - 1)):
                if key in legend:
                    return str(legend[key])
            try:
                numeric_items = sorted(
                    ((int(k), v) for k, v in legend.items()),
                    key=lambda kv: kv[0],
                )
                if numeric_items and score is not None:
                    lo = numeric_items[0][0]
                    hi = numeric_items[-1][0]
                    clamped = max(lo, min(hi, idx if idx <= hi else idx - 1))
                    for k, v in numeric_items:
                        if k == clamped:
                            return str(v)
                if numeric_items:
                    return str(numeric_items[len(numeric_items) // 2][1])
            except (TypeError, ValueError):
                pass
            first = next(iter(legend.values()), None)
            return str(first) if first is not None else None
        first = next(iter(legend.values()), None)
        return str(first) if first is not None else None
    return None


def _mood_label_from_score(score: float | None) -> str:
    if score is None:
        return "ふつう"
    value = float(score)
    if 0 <= value < len(MOOD_LEVELS):
        idx = int(round(value))
    else:
        idx = int(round(value)) - 1
    idx = max(0, min(len(MOOD_LEVELS) - 1, idx))
    return MOOD_LEVELS[idx]


def score_label(answer: Answer | Any) -> tuple[str, float | None, float | None]:
    if isinstance(answer, ScoreAnswer):
        score = answer.score
        legend = answer.legend
        confidence = answer.confidence
    else:
        score_raw = getattr(answer, "score", None)
        legend = getattr(answer, "legend", None)
        confidence_raw = getattr(answer, "confidence", None)
        try:
            score = float(score_raw) if score_raw is not None else None
        except (TypeError, ValueError):
            score = None
        try:
            confidence = float(confidence_raw) if confidence_raw is not None else None
        except (TypeError, ValueError):
            confidence = None

    label = _legend_to_label(legend, score)
    if label and label.startswith("{") and ":" in label:
        label = None
    if not label:
        label = _mood_label_from_score(score)
    return label, score, confidence


def mood_bar(mood_score: float | None) -> str:
    if mood_score is None:
        return "🤍🤍🤍🤍🤍"
    value = float(mood_score)
    if 0 <= value < len(MOOD_LEVELS):
        filled = int(round(value)) + 1
    else:
        filled = int(round(value))
    filled = max(1, min(5, filled))
    return "💖" * filled + "🤍" * (5 - filled)


def parse_fortune_answers(answers: Mapping[str, Answer | Any]) -> FortuneResult:
    overall, overall_probs = _choice_pick(answers["overall"])
    love, _ = _choice_pick(answers["love"])
    work, _ = _choice_pick(answers["work"])
    money, _ = _choice_pick(answers["money"])
    health, _ = _choice_pick(answers["health"])
    mood_label, mood_score, mood_confidence = score_label(answers["mood"])

    caution_answer = answers["caution"]
    if isinstance(caution_answer, NoulAnswer):
        caution = float(caution_answer.noul)
    else:
        try:
            caution = float(getattr(caution_answer, "noul", 0.0))
        except (TypeError, ValueError):
            caution = 0.0

    advice, _ = _choice_pick(answers["advice"])
    lucky_color, _ = _choice_pick(answers["lucky_color"])
    lucky_item, _ = _choice_pick(answers["lucky_item"])
    lucky_food, _ = _choice_pick(answers["lucky_food"])
    lucky_number, _ = _choice_pick(answers["lucky_number"])
    return FortuneResult(
        overall=overall,
        overall_top=_top_probabilities(overall_probs),
        love=love,
        work=work,
        money=money,
        health=health,
        mood_label=mood_label,
        mood_score=mood_score,
        mood_confidence=mood_confidence,
        caution=caution,
        advice=advice,
        lucky_color=lucky_color,
        lucky_item=lucky_item,
        lucky_food=lucky_food,
        lucky_number=lucky_number,
    )
