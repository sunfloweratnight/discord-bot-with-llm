"""Unit tests for fortune parsing / formatting (no live Jev/Discord)."""

from __future__ import annotations

from src.FortuneSchema import (
    ChoicePick,
    _mood_bar,
    _score_label,
    build_fortune_embed,
    format_fortune_content,
    parse_fortune_answers,
)


class _Ans:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def _sample_answers():
    return {
        "overall": _Ans(
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
        "love": _Ans(choice="順調", confidence=0.7, probabilities={"順調": 0.61}),
        "work": _Ans(choice="普通", confidence=0.6, probabilities={"普通": 0.48}),
        "money": _Ans(choice="注意", confidence=0.5, probabilities={"注意": 0.4}),
        "health": _Ans(choice="絶好調", confidence=0.4, probabilities={"絶好調": 0.5}),
        "mood": _Ans(
            score=3.1,
            legend={
                0: "とても低調で乗らない",
                1: "やや低調",
                2: "ふつう",
                3: "前向きで乗りやすい",
                4: "絶好調で勢いがある",
            },
            confidence=0.77,
            probabilities={},
        ),
        "caution": _Ans(noul=0.22),
        "advice": _Ans(
            choice="笑うことを意識",
            confidence=0.6,
            probabilities={"笑うことを意識": 0.44},
        ),
        "lucky_color": _Ans(
            choice="桜ピンク", confidence=0.5, probabilities={"桜ピンク": 0.33}
        ),
        "lucky_item": _Ans(
            choice="ぬいぐるみ", confidence=0.5, probabilities={"ぬいぐるみ": 0.29}
        ),
        "lucky_food": _Ans(choice="いちご", confidence=0.5, probabilities={"いちご": 0.31}),
        "lucky_number": _Ans(choice="7", confidence=0.5, probabilities={"7": 0.27}),
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
    label, score, confidence = _score_label(
        _Ans(
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
    assert _mood_bar(None) == "🤍🤍🤍🤍🤍"
    assert _mood_bar(3.1).startswith("💖")
    assert _mood_bar(3.1).count("💖") == 4


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
