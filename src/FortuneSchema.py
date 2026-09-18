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

LUCKY_COLORS = {
    "桜ピンク": "やさしくてときめく色",
    "ラベンダー": "ふわっと落ち着く色",
    "水色": "すっきりクリアな色",
    "ミントグリーン": "さっぱり癒やされる色",
    "クリームイエロー": "ぽかぽか明るい色",
    "コーラルオレンジ": "元気が出るあたたかい色",
    "パールホワイト": "きれいめで澄んだ色",
    "ベビーブルー": "やさしい空みたいな色",
    "ももいろ": "あまあまでかわいい色",
    "うすむらさき": "ちょっと神秘的な色",
}

LUCKY_ITEMS = {
    "ぬいぐるみ": "ぎゅっと安心できる相棒",
    "イヤホン": "自分ワールドへの入り口",
    "ふせんメモ": "きらめく小さなアイデア帳",
    "リボン・シュシュ": "今日の気分を上げるワンポイント",
    "マグカップ": "ほっと一息の味方",
    "キーホルダー": "お出かけのお守り",
    "ハンカチ": "きちんとかわいい持ち物",
    "シール・ステッカー": "毎日にきらめきを足す道具",
    "香水・ボディミスト": "気分転換の魔法スプレー",
    "お菓子": "ごほうびタイムの種",
}

LUCKY_FOODS = {
    "いちご": "あまくてハッピー",
    "ぷるんゼリー": "ひんやりごほうび",
    "マカロン": "かわいい一口幸せ",
    "ホットココア": "ぽかぽかおやすみ前",
    "フルーツティー": "軽やかリセット",
    "ヨーグルト": "すっきりチャージ",
    "チョコレート": "どきっと甘やかし",
    "おにぎり": "じぶん応援ごはん",
    "パンケーキ": "ふんわり朝ごほうび",
    "グミ": "ぽいっとご機嫌",
}

LUCKY_NUMBERS = {
    "1": "はじまりの数字",
    "2": "なかよしの数字",
    "3": "きらめきの数字",
    "4": "じっくりの数字",
    "5": "のびのびの数字",
    "6": "まるくおさまる数字",
    "7": "ちょっぴり魔法の数字",
    "8": "ぱわーあっぷの数字",
    "9": "みのりある数字",
}

MOOD_LEVELS = (
    "とても低調で乗らない",
    "やや低調",
    "ふつう",
    "前向きで乗りやすい",
    "絶好調で勢いがある",
)

AXIS_INSTRUCTION = (
    "Infer from the author's recent Discord messages in state. "
    "Pick the level that best matches today's likely trend for this person. "
    "Prefer evidence in their words and tone over generic calendar astrology."
)

OVERALL_EMOJI = {
    "大吉": "✨🌈",
    "中吉": "🌸💫",
    "小吉": "🍀🙂",
    "吉": "☀️🌿",
    "末吉": "🫧🌿",
    "凶": "☁️💭",
    "大凶": "🌧️🫂",
}

AXIS_EMOJI = {
    "絶好調": "💖",
    "順調": "🌷",
    "普通": "🙂",
    "注意": "⚠️",
    "低調": "💤",
}

COLOR_EMOJI = {
    "桜ピンク": "🩷",
    "ラベンダー": "💜",
    "水色": "🩵",
    "ミントグリーン": "💚",
    "クリームイエロー": "💛",
    "コーラルオレンジ": "🧡",
    "パールホワイト": "🤍",
    "ベビーブルー": "💙",
    "ももいろ": "💗",
    "うすむらさき": "💟",
}

OVERALL_EMBED_COLOR = {
    "大吉": 0xFF8EC8,
    "中吉": 0xC9A0FF,
    "小吉": 0x7DD3FC,
    "吉": 0x86EFAC,
    "末吉": 0xFDE68A,
    "凶": 0xA5B4FC,
    "大凶": 0x94A3B8,
}


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
            criteria=list(MOOD_LEVELS),
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
        "lucky_color": Choice(
            instructions=(
                "発言の雰囲気に合う、今日のラッキーカラーをかわいく選ぶ。"
            ),
            criteria=LUCKY_COLORS,
        ),
        "lucky_item": Choice(
            instructions="今日持ち歩くとよさそうな、かわいいラッキーアイテムを1つ選ぶ。",
            criteria=LUCKY_ITEMS,
        ),
        "lucky_food": Choice(
            instructions="今日のごほうび・ラッキーフードを1つ選ぶ。",
            criteria=LUCKY_FOODS,
        ),
        "lucky_number": Choice(
            instructions="今日のラッキーナンバー（1桁）を1つ選ぶ。",
            criteria=LUCKY_NUMBERS,
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
        "task": "今日の運勢を、この人の直近の発言からかわいく判断する",
    }
    if extra:
        state["command_note"] = extra
    return state


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


def _choice_pick(answer: Any) -> tuple[ChoicePick, dict[str, float]]:
    label = str(getattr(answer, "choice", None) or "不明")
    probs = _as_prob_map(getattr(answer, "probabilities", None))
    confidence_raw = getattr(answer, "confidence", None)
    try:
        confidence = float(confidence_raw) if confidence_raw is not None else None
    except (TypeError, ValueError):
        confidence = None
    probability = probs.get(label)
    return ChoicePick(label=label, probability=probability, confidence=confidence), probs


def _top_probabilities(probs: Mapping[str, float], *, limit: int = 3) -> tuple[tuple[str, float], ...]:
    ranked = sorted(probs.items(), key=lambda kv: kv[1], reverse=True)
    return tuple(ranked[:limit])


def _legend_to_label(legend: Any, score: float | None) -> str | None:
    """Pick a single human label from Jev Score legend (str or index→label map)."""
    if legend is None:
        return None
    if isinstance(legend, str):
        text = legend.strip()
        return text or None
    if isinstance(legend, Mapping):
        if score is not None:
            # Prefer nearest index key: 0..n-1 or 1..n
            idx = int(round(float(score)))
            for key in (idx, idx - 1, str(idx), str(idx - 1)):
                if key in legend:
                    return str(legend[key])
            # Highest-probability key if values look like probs? Otherwise first by sorted index
            try:
                numeric_items = sorted(
                    ((int(k), v) for k, v in legend.items()),
                    key=lambda kv: kv[0],
                )
                if numeric_items and score is not None:
                    # clamp into range
                    lo = numeric_items[0][0]
                    hi = numeric_items[-1][0]
                    clamped = max(lo, min(hi, idx if idx <= hi else idx - 1))
                    for k, v in numeric_items:
                        if k == clamped:
                            return str(v)
                if numeric_items:
                    mid = numeric_items[len(numeric_items) // 2][1]
                    return str(mid)
            except (TypeError, ValueError):
                pass
            # fallback: any value
            first = next(iter(legend.values()), None)
            return str(first) if first is not None else None
        first = next(iter(legend.values()), None)
        return str(first) if first is not None else None
    return None


def _mood_label_from_score(score: float | None) -> str:
    if score is None:
        return "ふつう"
    value = float(score)
    # Jev Score is often 0-indexed across criteria length
    if 0 <= value < len(MOOD_LEVELS):
        idx = int(round(value))
    else:
        # 1..5 style
        idx = int(round(value)) - 1
    idx = max(0, min(len(MOOD_LEVELS) - 1, idx))
    return MOOD_LEVELS[idx]


def _score_label(answer: Any) -> tuple[str, float | None, float | None]:
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
    # Never show raw dict / mapping dumps in Discord
    if label and label.startswith("{") and ":" in label:
        label = None
    if not label:
        label = _mood_label_from_score(score)
    return label, score, confidence


def parse_fortune_answers(answers: Mapping[str, Any]) -> FortuneResult:
    overall, overall_probs = _choice_pick(answers["overall"])
    love, _ = _choice_pick(answers["love"])
    work, _ = _choice_pick(answers["work"])
    money, _ = _choice_pick(answers["money"])
    health, _ = _choice_pick(answers["health"])
    mood_label, mood_score, mood_confidence = _score_label(answers["mood"])
    caution_raw = getattr(answers["caution"], "noul", 0.0)
    try:
        caution = float(caution_raw)
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


def _pct(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.0%}"


def _prob_bar(value: float | None, *, width: int = 8) -> str:
    if value is None:
        return "·" * width
    filled = max(0, min(width, int(round(float(value) * width))))
    return "▓" * filled + "░" * (width - filled)


def _axis_line(pick: ChoicePick) -> str:
    emoji = AXIS_EMOJI.get(pick.label, "✨")
    bits = [f"{emoji} **{pick.label}**"]
    if pick.probability is not None:
        bits.append(f"`{_pct(pick.probability)}` {_prob_bar(pick.probability, width=6)}")
    if pick.confidence is not None:
        bits.append(f"自信 `{_pct(pick.confidence)}`")
    return "\n".join(bits)


def _lucky_line(pick: ChoicePick, blurb: str) -> str:
    bits = [f"**{pick.label}**", f"*{blurb}*"]
    if pick.probability is not None:
        bits.append(f"確率 `{_pct(pick.probability)}`")
    return "\n".join(bits)


def _mood_bar(mood_score: float | None) -> str:
    if mood_score is None:
        return "🤍🤍🤍🤍🤍"
    value = float(mood_score)
    # Normalize 0..4 or 1..5 into filled hearts 1..5
    if 0 <= value < len(MOOD_LEVELS):
        filled = int(round(value)) + 1
    else:
        filled = int(round(value))
    filled = max(1, min(5, filled))
    return "💖" * filled + "🤍" * (5 - filled)


def format_fortune_content(display_name: str, result: FortuneResult) -> str:
    sparkle = OVERALL_EMOJI.get(result.overall.label, "✨")
    prob_bit = ""
    if result.overall.probability is not None:
        prob_bit = f"（きらめき `{_pct(result.overall.probability)}`）"
    return (
        f"˚₊·—̳͟͞͞♡ **{display_name}** さんの今日の運勢チェック完了〜！\n"
        f"{sparkle} 総合は **`{result.overall.label}`** {prob_bit} だよ"
    )


def build_fortune_embed(display_name: str, result: FortuneResult) -> "object":
    """Build a cute Discord embed. Imported discord only at call sites if needed."""
    import discord

    color = OVERALL_EMBED_COLOR.get(result.overall.label, 0xFFB7C5)
    overall_emoji = OVERALL_EMOJI.get(result.overall.label, "✨")
    color_emoji = COLOR_EMOJI.get(result.lucky_color.label, "🎨")
    color_blurb = LUCKY_COLORS.get(result.lucky_color.label, "きらめく色")
    item_blurb = LUCKY_ITEMS.get(result.lucky_item.label, "おたからアイテム")
    food_blurb = LUCKY_FOODS.get(result.lucky_food.label, "ごほうび")
    number_blurb = LUCKY_NUMBERS.get(result.lucky_number.label, "きせきの数字")
    advice_blurb = ADVICE_OPTIONS.get(result.advice.label, "今日をやさしく過ごそう")

    lines = [
        f"{overall_emoji} **総合運** › **`{result.overall.label}`** {overall_emoji}",
    ]
    if result.overall.probability is not None or result.overall.confidence is not None:
        lines.append(
            f"📡 Jev確率 `{_pct(result.overall.probability)}` "
            f"{_prob_bar(result.overall.probability)} · "
            f"自信 `{_pct(result.overall.confidence)}`"
        )
    if result.overall_top:
        ranking = "  ›  ".join(
            f"**{label}** `{_pct(prob)}`" for label, prob in result.overall_top
        )
        lines.append(f"🗳️ 候補ランキング: {ranking}")
    lines.append("")
    lines.append("୨୧┈┈┈┈┈┈┈┈┈┈┈┈┈┈୨୧")
    if result.caution >= 0.6:
        lines.extend(
            [
                f"🫧 *今日はそっと慎重モード* （Noul `{_pct(result.caution)}`）",
                "　無理しないのがいちばんかわいいよ〜",
                "୨୧┈┈┈┈┈┈┈┈┈┈┈┈┈┈୨୧",
            ]
        )
    elif result.caution > 0:
        lines.extend(
            [
                f"🫧 慎重さシグナル `Noul {_pct(result.caution)}`",
                "୨୧┈┈┈┈┈┈┈┈┈┈┈┈┈┈୨୧",
            ]
        )

    embed = discord.Embed(
        title=f"♡ {display_name} さんの今日の運勢 ♡",
        description="\n".join(lines),
        color=color,
    )

    embed.add_field(name="💕 恋愛・対人", value=_axis_line(result.love), inline=True)
    embed.add_field(name="📚 仕事・勉強", value=_axis_line(result.work), inline=True)
    embed.add_field(name="🪙 金運", value=_axis_line(result.money), inline=True)
    embed.add_field(name="🌿 健康", value=_axis_line(result.health), inline=True)

    mood_bits = [f"{_mood_bar(result.mood_score)}", f"*{result.mood_label}*"]
    if result.mood_confidence is not None:
        mood_bits.append(f"自信 `{_pct(result.mood_confidence)}`")
    embed.add_field(name="🎀 気分ゲージ", value="\n".join(mood_bits), inline=True)
    embed.add_field(
        name="🔢 ラッキーナンバー",
        value=_lucky_line(result.lucky_number, number_blurb),
        inline=True,
    )

    embed.add_field(
        name=f"{color_emoji} ラッキーカラー",
        value=_lucky_line(result.lucky_color, color_blurb),
        inline=True,
    )
    embed.add_field(
        name="🧸 ラッキーアイテム",
        value=_lucky_line(result.lucky_item, item_blurb),
        inline=True,
    )
    embed.add_field(
        name="🍬 ラッキーフード",
        value=_lucky_line(result.lucky_food, food_blurb),
        inline=True,
    )

    advice_bits = [f"**{result.advice.label}**", f"> {advice_blurb}"]
    if result.advice.probability is not None:
        advice_bits.append(
            f"Jev確率 `{_pct(result.advice.probability)}` {_prob_bar(result.advice.probability)}"
        )
    embed.add_field(name="💌 今日のひとこと", value="\n".join(advice_bits), inline=False)

    footer_parts = ["˚₊‧꒰ა Jev System One ໒꒱ ‧₊"]
    if result.overall.probability is not None:
        footer_parts.append(f"top {_pct(result.overall.probability)}")
    if result.overall.confidence is not None:
        footer_parts.append(f"conf {_pct(result.overall.confidence)}")
    embed.set_footer(text=" · ".join(footer_parts))
    return embed
