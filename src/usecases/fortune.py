"""Tell fortune use case — depends only on DecisionPort + fortune domain."""

from __future__ import annotations

from src.domain.decision.models import (
    DecisionConfigError,
    DecisionError,
    DecisionRequest,
    DecisionUnavailableError,
)
from src.domain.decision.ports import DecisionPort
from src.domain.fortune.models import (
    FortuneResult,
    InsufficientHistoryError,
    TellFortuneCommand,
)
from src.domain.fortune.parsing import parse_fortune_answers
from src.domain.fortune.questions import build_fortune_questions, build_fortune_state


class TellFortuneUseCase:
    def __init__(self, decision: DecisionPort) -> None:
        self._decision = decision

    async def execute(self, command: TellFortuneCommand) -> FortuneResult:
        messages = [m.strip() for m in command.recent_messages if m and m.strip()]
        if not messages:
            raise InsufficientHistoryError("insufficient history")

        state = build_fortune_state(
            display_name=command.display_name,
            user_id=command.user_id,
            channel_name=command.channel_name,
            channel_id=command.channel_id,
            messages=messages,
            extra=command.note,
        )
        request = DecisionRequest(state=state, questions=build_fortune_questions())
        try:
            response = await self._decision.evaluate(request)
        except DecisionConfigError:
            raise
        except DecisionUnavailableError:
            raise
        except DecisionError:
            raise
        except Exception as exc:
            raise DecisionUnavailableError(str(exc)) from exc

        return parse_fortune_answers(response.answers)
