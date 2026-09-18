"""Discord embed formatting for fortune results (Presentation only)."""

from __future__ import annotations

import discord

from src.domain.fortune.models import ChoicePick, FortuneResult
from src.domain.fortune.parsing import mood_bar
from src.domain.fortune.questions import (
    ADVICE_OPTIONS,
    LUCKY_COLORS,
    LUCKY_FOODS,
    LUCKY_ITEMS,
    LUCKY_NUMBERS,
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


def format_fortune_content(display_name: str, result: FortuneResult) -> str:
    sparkle = OVERALL_EMOJI.get(result.overall.label, "✨")
    prob_bit = ""
    if result.overall.probability is not None:
        prob_bit = f"（きらめき `{_pct(result.overall.probability)}`）"
    return (
        f"˚₊·—̳͟͞͞♡ **{display_name}** さんの今日の運勢チェック完了〜！\n"
        f"{sparkle} 総合は **`{result.overall.label}`** {prob_bit} だよ"
    )


def build_fortune_embed(display_name: str, result: FortuneResult) -> discord.Embed:
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

    mood_bits = [f"{mood_bar(result.mood_score)}", f"*{result.mood_label}*"]
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
            f"Jev確率 `{_pct(result.advice.probability)}` "
            f"{_prob_bar(result.advice.probability)}"
        )
    embed.add_field(name="💌 今日のひとこと", value="\n".join(advice_bits), inline=False)

    footer_parts = ["˚₊‧꒰ა Jev System One ໒꒱ ‧₊"]
    if result.overall.probability is not None:
        footer_parts.append(f"top {_pct(result.overall.probability)}")
    if result.overall.confidence is not None:
        footer_parts.append(f"conf {_pct(result.overall.confidence)}")
    embed.set_footer(text=" · ".join(footer_parts))
    return embed
