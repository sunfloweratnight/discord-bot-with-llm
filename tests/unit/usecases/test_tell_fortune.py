"""TellFortuneUseCase tests with FakeDecisionPort."""

from __future__ import annotations

import pytest

from src.domain.decision.models import (
    ChoiceAnswer,
    DecisionConfigError,
    DecisionRequest,
    DecisionResponse,
    DecisionUnavailableError,
    NoulAnswer,
    ScoreAnswer,
)
from src.domain.fortune.models import InsufficientHistoryError, TellFortuneCommand
from src.usecases.fortune import TellFortuneUseCase


class FakeDecisionPort:
    def __init__(self, response: DecisionResponse | None = None, error: Exception | None = None):
        self.response = response
        self.error = error
        self.calls: list[DecisionRequest] = []

    async def evaluate(self, request: DecisionRequest) -> DecisionResponse:
        self.calls.append(request)
        if self.error:
            raise self.error
        assert self.response is not None
        return self.response

    async def aclose(self) -> None:
        return None


def _ok_response() -> DecisionResponse:
    return DecisionResponse(
        answers={
            "overall": ChoiceAnswer("中吉", 0.8, {"中吉": 0.55}),
            "love": ChoiceAnswer("順調", 0.7, {"順調": 0.6}),
            "work": ChoiceAnswer("普通", 0.6, {"普通": 0.5}),
            "money": ChoiceAnswer("注意", 0.5, {"注意": 0.4}),
            "health": ChoiceAnswer("順調", 0.5, {"順調": 0.5}),
            "mood": ScoreAnswer(score=3.0, legend="前向きで乗りやすい", confidence=0.7),
            "caution": NoulAnswer(0.2),
            "advice": ChoiceAnswer("休息を優先", 0.5, {"休息を優先": 0.4}),
            "lucky_color": ChoiceAnswer("桜ピンク", 0.5, {"桜ピンク": 0.3}),
            "lucky_item": ChoiceAnswer("ぬいぐるみ", 0.5, {"ぬいぐるみ": 0.3}),
            "lucky_food": ChoiceAnswer("いちご", 0.5, {"いちご": 0.3}),
            "lucky_number": ChoiceAnswer("7", 0.5, {"7": 0.3}),
        }
    )


@pytest.mark.asyncio
async def test_execute_success():
    fake = FakeDecisionPort(response=_ok_response())
    uc = TellFortuneUseCase(fake)
    result = await uc.execute(
        TellFortuneCommand(
            user_id=1,
            display_name="花",
            channel_id=2,
            channel_name="general",
            recent_messages=["こんにちは", "元気"],
        )
    )
    assert result.overall.label == "中吉"
    assert len(fake.calls) == 1
    assert "overall" in fake.calls[0].questions


@pytest.mark.asyncio
async def test_execute_insufficient_history():
    fake = FakeDecisionPort(response=_ok_response())
    uc = TellFortuneUseCase(fake)
    with pytest.raises(InsufficientHistoryError):
        await uc.execute(
            TellFortuneCommand(
                user_id=1,
                display_name="花",
                channel_id=2,
                channel_name="general",
                recent_messages=[],
            )
        )
    assert fake.calls == []


@pytest.mark.asyncio
async def test_execute_propagates_config_error():
    fake = FakeDecisionPort(error=DecisionConfigError("missing key"))
    uc = TellFortuneUseCase(fake)
    with pytest.raises(DecisionConfigError):
        await uc.execute(
            TellFortuneCommand(
                user_id=1,
                display_name="花",
                channel_id=2,
                channel_name="general",
                recent_messages=["hi"],
            )
        )


@pytest.mark.asyncio
async def test_execute_propagates_unavailable_error():
    fake = FakeDecisionPort(error=DecisionUnavailableError("down"))
    uc = TellFortuneUseCase(fake)
    with pytest.raises(DecisionUnavailableError):
        await uc.execute(
            TellFortuneCommand(
                user_id=1,
                display_name="花",
                channel_id=2,
                channel_name="general",
                recent_messages=["hi"],
            )
        )
