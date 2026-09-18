"""Assemble chat prompt and call ChatPort."""

from __future__ import annotations

from src.domain.chat.models import (
    ChatConfigError,
    ChatError,
    ChatReply,
    ChatUnavailableError,
    ReplyToUserCommand,
)
from src.domain.chat.ports import ChatPort


class ReplyToUserMessage:
    def __init__(self, chat: ChatPort) -> None:
        self._chat = chat

    def build_prompt(self, command: ReplyToUserCommand) -> str:
        lines = [f"{msg.author_name}: {msg.content}" for msg in command.history]
        context = "Previous messages:\n" + "\n".join(lines) + "\n\nCurrent message:\n"
        return f"{context}{command.author_name}: {command.user_text}"

    async def execute(self, command: ReplyToUserCommand) -> ChatReply:
        if not command.user_text.strip():
            return ChatReply(text="どしたん?話きこか?")
        prompt = self.build_prompt(command)
        try:
            return await self._chat.generate(prompt)
        except (ChatConfigError, ChatUnavailableError):
            raise
        except ChatError:
            raise
        except Exception as exc:
            raise ChatUnavailableError(str(exc)) from exc
