"""Thin async wrapper around TypeSafe Jev (System One)."""

from __future__ import annotations

from typing import Any, Mapping

from typesafe_sdk import AsyncTypeSafeClient

from src.FortuneSchema import build_fortune_questions


class JevClientError(Exception):
    """User-safe failure talking to Jev."""


class JevClient:
    def __init__(self, api_key: str, *, model: str = "jev-latest") -> None:
        self._api_key = (api_key or "").strip()
        self._model = model
        self._client: AsyncTypeSafeClient | None = None

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    def _get_client(self) -> AsyncTypeSafeClient:
        if not self.configured:
            raise JevClientError(
                "運勢APIのキーが未設定か無効です。Koyebの環境変数 `TYPESAFE_API_KEY` を確認してください。"
            )
        if self._client is None:
            self._client = AsyncTypeSafeClient(api_key=self._api_key, model=self._model)
        return self._client

    async def evaluate_fortune(self, state: Mapping[str, Any] | str) -> Mapping[str, Any]:
        client = self._get_client()
        try:
            response = await client.system_one(
                state=state,
                questions=build_fortune_questions(),
                model=self._model,
            )
        except JevClientError:
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
                raise JevClientError(
                    "運勢APIのキーが未設定か無効です。Koyebの環境変数 `TYPESAFE_API_KEY` を確認してください。"
                ) from exc
            raise JevClientError(
                "占いに失敗しました。しばらくしてからもう一度試してください。"
            ) from exc
        return response.answers

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
