"""Unit tests for ReplyToUserMessage with a fake ChatPort."""

from __future__ import annotations

import pytest

from src.domain.chat.models import (
    ChatConfigError,
    ChatMessage,
    ChatReply,
    ChatUnavailableError,
    ReplyToUserCommand,
)
from src.usecases.chat import ReplyToUserMessage


class FakeChatPort:
    def __init__(self, reply: ChatReply | None = None, error: Exception | None = None) -> None:
        self.reply = reply or ChatReply(text="hello")
        self.error = error
        self.prompts: list[str] = []

    async def generate(self, prompt: str) -> ChatReply:
        self.prompts.append(prompt)
        if self.error is not None:
            raise self.error
        return self.reply


@pytest.mark.asyncio
async def test_empty_user_text_returns_default_without_calling_port():
    fake = FakeChatPort()
    use_case = ReplyToUserMessage(fake)
    result = await use_case.execute(
        ReplyToUserCommand(author_name="alice", user_text="  ", history=[])
    )
    assert result.text == "どしたん?話きこか?"
    assert fake.prompts == []


@pytest.mark.asyncio
async def test_builds_prompt_with_history_and_returns_reply():
    fake = FakeChatPort(reply=ChatReply(text="yo"))
    use_case = ReplyToUserMessage(fake)
    result = await use_case.execute(
        ReplyToUserCommand(
            author_name="alice",
            user_text="hi",
            history=[
                ChatMessage(author_name="bob", content="hey"),
                ChatMessage(author_name="alice", content="sup"),
            ],
        )
    )
    assert result.text == "yo"
    assert len(fake.prompts) == 1
    prompt = fake.prompts[0]
    assert "Previous messages:" in prompt
    assert "bob: hey" in prompt
    assert "alice: sup" in prompt
    assert "Current message:" in prompt
    assert "alice: hi" in prompt


@pytest.mark.asyncio
async def test_propagates_chat_config_error():
    fake = FakeChatPort(error=ChatConfigError("bad key"))
    use_case = ReplyToUserMessage(fake)
    with pytest.raises(ChatConfigError, match="bad key"):
        await use_case.execute(
            ReplyToUserCommand(author_name="alice", user_text="hi", history=[])
        )


@pytest.mark.asyncio
async def test_wraps_unexpected_errors():
    fake = FakeChatPort(error=RuntimeError("boom"))
    use_case = ReplyToUserMessage(fake)
    with pytest.raises(ChatUnavailableError, match="boom"):
        await use_case.execute(
            ReplyToUserCommand(author_name="alice", user_text="hi", history=[])
        )
