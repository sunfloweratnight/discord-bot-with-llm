"""Fortune question definitions as domain Decision DTOs (no SDK types)."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from src.domain.decision.models import (
    ChoiceQuestion,
    NoulQuestion,
    Question,
    ScoreQuestion,
)

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


def build_fortune_questions() -> dict[str, Question]:
    axis_criteria = {level: f"今日の運勢レベル: {level}" for level in AXIS_LEVELS}
    return {
        "overall": ChoiceQuestion(
            instructions=(
                "総合運。発言の雰囲気・意欲・不安・勢いから、"
                "今日いちばん当てはまる総合運を選ぶ。"
            ),
            criteria={level: f"総合運が{level}" for level in OVERALL_LEVELS},
        ),
        "love": ChoiceQuestion(
            instructions=f"恋愛・対人関係の運。{AXIS_INSTRUCTION}",
            criteria=axis_criteria,
        ),
        "work": ChoiceQuestion(
            instructions=f"仕事・勉強・作業の運。{AXIS_INSTRUCTION}",
            criteria=axis_criteria,
        ),
        "money": ChoiceQuestion(
            instructions=f"金運・支出・買い物の運。{AXIS_INSTRUCTION}",
            criteria=axis_criteria,
        ),
        "health": ChoiceQuestion(
            instructions=f"体調・メンタルの運。{AXIS_INSTRUCTION}",
            criteria=axis_criteria,
        ),
        "mood": ScoreQuestion(
            instructions=(
                "今日の気分の乗りやすさ。1が低調、5が最高潮。"
                "発言のトーンから段階評価する。"
            ),
            criteria=list(MOOD_LEVELS),
        ),
        "caution": NoulQuestion(
            instructions="今日は慎重に動いた方がよいか（Yes=慎重が望ましい）",
        ),
        "advice": ChoiceQuestion(
            instructions=(
                "直近の発言から、今日いちばん役立ちそうな短い行動指針を1つ選ぶ。"
            ),
            criteria=ADVICE_OPTIONS,
        ),
        "lucky_color": ChoiceQuestion(
            instructions="発言の雰囲気に合う、今日のラッキーカラーをかわいく選ぶ。",
            criteria=LUCKY_COLORS,
        ),
        "lucky_item": ChoiceQuestion(
            instructions="今日持ち歩くとよさそうな、かわいいラッキーアイテムを1つ選ぶ。",
            criteria=LUCKY_ITEMS,
        ),
        "lucky_food": ChoiceQuestion(
            instructions="今日のごほうび・ラッキーフードを1つ選ぶ。",
            criteria=LUCKY_FOODS,
        ),
        "lucky_number": ChoiceQuestion(
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
