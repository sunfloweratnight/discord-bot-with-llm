"""Unit tests for fortune parsing (domain)."""

from __future__ import annotations

from src.domain.decision.models import ChoiceAnswer, NoulAnswer, ScoreAnswer
from src.domain.fortune.models import ChoicePick
from src.domain.fortune.parsing import mood_bar, parse_fortune_answers, score_label
from src.presentation.discord.formatters.fortune_embed import (
    build_fortune_embed,
    format_fortune_content,
)


def _sample_answers():
    return {
        "overall": ChoiceAnswer(
            choice="中吉",
            confidence=0.82,
            probabilities={
                "大吉": 0.18,
                "中吉": 0.55,
                "小吉": 0.15,
                "吉": 0.07,
                "末吉": 0.03,
                "凶": 0.01,
                "大凶": 0.01,
            },
        ),
        "love": ChoiceAnswer(choice="順調", confidence=0.7, probabilities={"順調": 0.61}),
        "work": ChoiceAnswer(choice="普通", confidence=0.6, probabilities={"普通": 0.48}),
        "money": ChoiceAnswer(choice="注意", confidence=0.5, probabilities={"注意": 0.4}),
        "health": ChoiceAnswer(
            choice="絶好調", confidence=0.4, probabilities={"絶好調": 0.5}
        ),
        "mood": ScoreAnswer(
            score=3.1,
            legend={
                0: "とても低調で乗らない",
                1: "やや低調",
                2: "ふつう",
                3: "前向きで乗りやすい",
                4: "絶好調で勢いがある",
            },
            confidence=0.77,
        ),
        "caution": NoulAnswer(noul=0.22),
        "advice": ChoiceAnswer(
            choice="笑うことを意識",
            confidence=0.6,
            probabilities={"笑うことを意識": 0.44},
        ),
        "lucky_color": ChoiceAnswer(
            choice="桜ピンク", confidence=0.5, probabilities={"桜ピンク": 0.33}
        ),
        "lucky_item": ChoiceAnswer(
            choice="ぬいぐるみ", confidence=0.5, probabilities={"ぬいぐるみ": 0.29}
        ),
        "lucky_food": ChoiceAnswer(
            choice="いちご", confidence=0.5, probabilities={"いちご": 0.31}
        ),
        "lucky_number": ChoiceAnswer(
            choice="7", confidence=0.5, probabilities={"7": 0.27}
        ),
    }


def test_parse_fortune_answers_picks_top_overall_and_mood_label():
    result = parse_fortune_answers(_sample_answers())
    assert result.overall.label == "中吉"
    assert result.overall.probability == 0.55
    assert result.overall.confidence == 0.82
    assert result.overall_top[0] == ("中吉", 0.55)
    assert result.mood_label == "前向きで乗りやすい"
    assert "{" not in result.mood_label
    assert result.lucky_color.label == "桜ピンク"
    assert result.caution == 0.22


def test_score_label_does_not_dump_legend_dict():
    label, score, confidence = score_label(
        ScoreAnswer(
            score=1.2,
            legend={
                0: "とても低調で乗らない",
                1: "やや低調",
                2: "ふつう",
                3: "前向きで乗りやすい",
                4: "絶好調で勢いがある",
            },
            confidence=0.5,
        )
    )
    assert label == "やや低調"
    assert score == 1.2
    assert confidence == 0.5
    assert "{" not in label


def test_mood_bar_fills_hearts():
    assert mood_bar(None) == "🤍🤍🤍🤍🤍"
    assert mood_bar(3.1).startswith("💖")
    assert mood_bar(3.1).count("💖") == 4


def test_format_and_embed_include_probabilities():
    result = parse_fortune_answers(_sample_answers())
    content = format_fortune_content("花", result)
    assert "中吉" in content
    assert "55%" in content

    embed = build_fortune_embed("花", result)
    assert "Jev確率" in embed.description
    assert "候補ランキング" in embed.description
    field_text = "\n".join(f.value for f in embed.fields)
    assert "61%" in field_text
    assert isinstance(result.love, ChoicePick)
