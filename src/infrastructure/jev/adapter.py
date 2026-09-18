"""Typesafe Jev adapter implementing DecisionPort."""

from __future__ import annotations

from typesafe_sdk import AsyncTypeSafeClient

from src.domain.decision.models import (
    DecisionConfigError,
    DecisionRequest,
    DecisionResponse,
    DecisionUnavailableError,
)
from src.infrastructure.jev.mapping import from_sdk_answers, to_sdk_questions


class TypesafeJevAdapter:
    def __init__(self, api_key: str, *, model: str = "jev-latest") -> None:
        self._api_key = (api_key or "").strip()
        self._model = model
        self._client: AsyncTypeSafeClient | None = None

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    def _get_client(self) -> AsyncTypeSafeClient:
        if not self.configured:
            raise DecisionConfigError(
                "運勢APIのキーが未設定か無効です。Koyebの環境変数 `TYPESAFE_API_KEY` を確認してください。"
            )
        if self._client is None:
            self._client = AsyncTypeSafeClient(api_key=self._api_key, model=self._model)
        return self._client

    async def evaluate(self, request: DecisionRequest) -> DecisionResponse:
        client = self._get_client()
        try:
            response = await client.system_one(
                state=request.state,
                questions=to_sdk_questions(request.questions),
                model=self._model,
            )
        except DecisionConfigError:
            raise
        except Exception as exc:
            text = str(exc).lower()
            if any(
                marker in text
                for marker in (
                    "api key",
                    "unauthorized",
                    "401",
                    "403",
                    "invalid key",
                    "no api key",
                )
            ):
                raise DecisionConfigError(
                    "運勢APIのキーが未設定か無効です。Koyebの環境変数 `TYPESAFE_API_KEY` を確認してください。"
                ) from exc
            raise DecisionUnavailableError(
                "占いに失敗しました。しばらくしてからもう一度試してください。"
            ) from exc
        return DecisionResponse(answers=from_sdk_answers(response.answers))

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
