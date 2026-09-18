"""Gemini adapter implementing ChatPort."""

from __future__ import annotations

import asyncio

import google.generativeai as genai

from src.domain.chat.models import ChatConfigError, ChatReply, ChatUnavailableError


class GeminiChatAdapter:
    SAFETY_SETTINGS = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]

    def __init__(
        self,
        api_key: str,
        initial_prompt: str,
        *,
        model_name: str = "gemini-2.5-flash",
    ) -> None:
        self._api_key = (api_key or "").strip()
        if not self._api_key:
            raise ChatConfigError("GEMINI_API_KEY is missing")
        genai.configure(api_key=self._api_key)
        generation_config = {
            "temperature": 1,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
        }
        self._model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=generation_config,
            safety_settings=self.SAFETY_SETTINGS,
        )
        self._default_initial_prompt = initial_prompt
        self._current_prompt = initial_prompt
        history = [{"role": "user", "parts": [initial_prompt]}]
        self._chat = self._model.start_chat(history=history)

    @property
    def current_prompt(self) -> str:
        return self._current_prompt

    def reset_prompt(self, prompt: str | None = None) -> None:
        text = prompt if prompt is not None else self._default_initial_prompt
        self._current_prompt = text
        history = [{"role": "user", "parts": [text]}]
        self._chat = self._model.start_chat(history=history)

    def set_prompt(self, prompt: str) -> None:
        self._current_prompt = prompt
        history = [{"role": "user", "parts": [prompt]}]
        self._chat = self._model.start_chat(history=history)

    @staticmethod
    def is_api_key_error(error: Exception) -> bool:
        text = str(error).lower()
        markers = (
            "api_key_invalid",
            "api key not valid",
            "invalid api key",
            "api key expired",
        )
        return any(marker in text for marker in markers)

    @staticmethod
    def is_model_error(error: Exception) -> bool:
        text = str(error).lower()
        specific = (
            "is not found",
            "model_not_found",
            "not found for api version",
            "no longer available to new users",
            "was not found",
            "invalid model name",
            "model does not exist",
        )
        return any(marker in text for marker in specific)

    @staticmethod
    def is_quota_error(error: Exception) -> bool:
        text = str(error).lower()
        markers = (
            "resource_exhausted",
            "quota exceeded",
            "rate limit",
            "429",
            "too many requests",
        )
        return any(marker in text for marker in markers)

    @staticmethod
    def api_key_user_message() -> str:
        return (
            "GeminiのAPIキーが無効か期限切れのようです。"
            "デプロイ先（Koyeb）の環境変数 `GEMINI_API_KEY` を有効なキーに更新して、"
            "サービスを再デプロイしてください。"
        )

    @staticmethod
    def model_user_message() -> str:
        return (
            "Geminiのモデルが利用できないようです（廃止・名称変更の可能性）。"
            "ボット側のモデル設定を更新して再デプロイが必要です。"
        )

    @staticmethod
    def quota_user_message() -> str:
        return (
            "Geminiの利用上限（無料枠・レート制限）に達したようです。"
            "しばらく待つか、Google AI Studioのクォータを確認してください。"
        )

    def _classify_error(self, exc: Exception) -> Exception:
        if self.is_api_key_error(exc):
            return ChatConfigError(self.api_key_user_message())
        if self.is_model_error(exc):
            return ChatUnavailableError(self.model_user_message())
        if self.is_quota_error(exc):
            return ChatUnavailableError(self.quota_user_message())
        return ChatUnavailableError(
            "申し訳ありません。AIへの接続に何度か失敗しました。"
            "しばらく待ってからもう一度試してください。"
        )

    async def generate(self, prompt: str) -> ChatReply:
        max_attempts = 3
        last_error: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                response = await asyncio.get_event_loop().run_in_executor(
                    None, self._chat.send_message, prompt
                )
                text = response.text if hasattr(response, "text") else str(response)
                return ChatReply(text=text)
            except asyncio.TimeoutError as exc:
                last_error = exc
                if attempt == max_attempts:
                    raise ChatUnavailableError(
                        "申し訳ありません。AIの応答が時間内に返りませんでした。"
                        "しばらく待ってからもう一度試してください。"
                    ) from exc
                await asyncio.sleep(1)
            except Exception as exc:
                last_error = exc
                # Credentials / dead model / quota will not recover on retry.
                if (
                    self.is_api_key_error(exc)
                    or self.is_model_error(exc)
                    or self.is_quota_error(exc)
                    or attempt == max_attempts
                ):
                    classified = self._classify_error(exc)
                    raise classified from exc
                await asyncio.sleep(1)
        raise ChatUnavailableError(str(last_error) if last_error else "unknown chat error")

    async def generate_ephemeral(self, prompt: str) -> str:
        """One-off generation without mutating the main chat session."""
        try:
            temp_chat = self._model.start_chat()
            response = await asyncio.get_event_loop().run_in_executor(
                None, temp_chat.send_message, prompt
            )
            return response.text if hasattr(response, "text") else str(response)
        except Exception as exc:
            raise self._classify_error(exc) from exc
