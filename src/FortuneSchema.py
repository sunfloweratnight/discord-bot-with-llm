"""Jev fortune question schema and Discord embed formatting (PROJECT.md §13)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from typesafe_sdk import Choice, Noul, Score

OVERALL_LEVELS = ("大吉", "中吉", "小吉", "吉", "末吉", "凶", "大凶")
AXIS_LEVELS = ("絶好調", "順調", "普通", "注意", "低調")
ADVICE_OPTIONS = {
    "深呼吸してから動く": "焦らず一度止まってから行動する",
    "連絡を大切に": "気になる相手や仲間への一言を優先する",
    "新しいことに触れる": "いつもと違う小さな刺激を取り入れる",
    "休息を優先": "無理せず体と心の回復を先にする",
    "小さな整理をする": "机・メモ・予定など身近なものを整える",
    "笑うことを意識": "軽い冗談や笑顔で空気をやわらげる",
    "早寝を心がける": "夜更かしを避けてリズムを整える",
    "水を多めに": "水分と休憩を意識してペースを保つ",
}

AXIS_INSTRUCTION = (
    "Infer from the author's recent Discord messages in state. "
    "Pick the level that best matches today's likely trend for this person. "
    "Prefer evidence in their words and tone over generic calendar astrology."
)


def build_fortune_questions() -> dict[str, Choice | Score | Noul]:
    axis_criteria = {level: f"今日の運勢レベル: {level}" for level in AXIS_LEVELS}
    return {
        "overall": Choice(
            instructions=(
                "総合運。発言の雰囲気・意欲・不安・勢いから、"
                "今日いちばん当てはまる総合運を選ぶ。"
            ),
            criteria={level: f"総合運が{level}" for level in OVERALL_LEVELS},
        ),
        "love": Choice(
            instructions=f"恋愛・対人関係の運。{AXIS_INSTRUCTION}",
            criteria=axis_criteria,
        ),
        "work": Choice(
            instructions=f"仕事・勉強・作業の運。{AXIS_INSTRUCTION}",
            criteria=axis_criteria,
        ),
        "money": Choice(
            instructions=f"金運・支出・買い物の運。{AXIS_INSTRUCTION}",
            criteria=axis_criteria,
        ),
        "health": Choice(
            instructions=f"体調・メンタルの運。{AXIS_INSTRUCTION}",
            criteria=axis_criteria,
        ),
        "mood": Score(
            instructions=(
                "今日の気分の乗りやすさ。1が低調、5が最高潮。"
                "発言のトーンから段階評価する。"
            ),
            criteria=[
                "とても低調で乗らない",
                "やや低調",
                "ふつう",
                "前向きで乗りやすい",
                "絶好調で勢いがある",
            ],
        ),
        "caution": Noul(
            instructions="今日は慎重に動いた方がよいか（Yes=慎重が望ましい）",
        ),
        "advice": Choice(
            instructions=(
                "直近の発言から、今日いちばん役立ちそうな短い行動指針を1つ選ぶ。"
            ),
            criteria=ADVICE_OPTIONS,
        ),
    }


def build_fortune_state(
    *,
    display_name: str,
    user_id: int,
    channel_name: str,
    channel_id: int,
    messages: Sequence[str],
    extra: str = "",
) -> dict[str, Any]:
    numbered = [f"{i}. {text}" for i, text in enumerate(messages, start=1)]
    state: dict[str, Any] = {
        "display_name": display_name,
        "discord_user_id": str(user_id),
        "channel_name": channel_name,
        "channel_id": str(channel_id),
        "recent_messages": numbered,
        "message_count": len(messages),
        "task": "今日の運勢を、この人の直近の発言から判断する",
    }
    if extra:
        state["command_note"] = extra
    return state


@dataclass(frozen=True)
class FortuneResult:
    overall: str
    overall_confidence: float | None
    overall_probability: float | None
    love: str
    work: str
    money: str
    health: str
    mood_label: str
    mood_score: float | None
    caution: float
    advice: str


def _choice_pick(answer: Any) -> tuple[str, float | None, float | None]:
    choice = getattr(answer, "choice", None) or "不明"
    confidence = getattr(answer, "confidence", None)
    probabilities = getattr(answer, "probabilities", None) or {}
    prob = None
    if isinstance(probabilities, Mapping) and choice in probabilities:
        try:
            prob = float(probabilities[choice])
        except (TypeError, ValueError):
            prob = None
    conf = float(confidence) if confidence is not None else None
    return str(choice), conf, prob


def _score_label(answer: Any) -> tuple[str, float | None]:
    score = getattr(answer, "score", None)
    legend = getattr(answer, "legend", None)
    if legend:
        return str(legend), float(score) if score is not None else None
    if score is None:
        return "不明", None
    # Score may be continuous; map roughly onto 1–5 display
    try:
        value = float(score)
    except (TypeError, ValueError):
        return str(score), None
    clamped = max(1, min(5, int(round(value + 1)) if value < 1.5 else int(round(value))))
    # Prefer showing raw score with simple star hint
    stars = "★" * max(1, min(5, int(round(value)) if value >= 1 else 1))
    return f"{stars} ({value:.2f})", value


def parse_fortune_answers(answers: Mapping[str, Any]) -> FortuneResult:
    overall, overall_conf, overall_prob = _choice_pick(answers["overall"])
    love, _, _ = _choice_pick(answers["love"])
    work, _, _ = _choice_pick(answers["work"])
    money, _, _ = _choice_pick(answers["money"])
    health, _, _ = _choice_pick(answers["health"])
    mood_label, mood_score = _score_label(answers["mood"])
    caution_raw = getattr(answers["caution"], "noul", 0.0)
    try:
        caution = float(caution_raw)
    except (TypeError, ValueError):
        caution = 0.0
    advice, _, _ = _choice_pick(answers["advice"])
    return FortuneResult(
        overall=overall,
        overall_confidence=overall_conf,
        overall_probability=overall_prob,
        love=love,
        work=work,
        money=money,
        health=health,
        mood_label=mood_label,
        mood_score=mood_score,
        caution=caution,
        advice=advice,
    )
