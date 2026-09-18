"""Tests for Gemini user-facing API key error mapping."""

from __future__ import annotations

from src.infrastructure.gemini import GeminiChatAdapter


def test_api_key_error_detection():
    assert GeminiChatAdapter.is_api_key_error(Exception("API_KEY_INVALID"))
    assert GeminiChatAdapter.is_api_key_error(
        Exception("API key not valid. Please pass a valid API key.")
    )
    assert not GeminiChatAdapter.is_api_key_error(Exception("timeout waiting for upstream"))


def test_model_error_detection():
    assert GeminiChatAdapter.is_model_error(
        Exception("404 models/gemini-2.0-flash-exp is not found for API version")
    )
    assert not GeminiChatAdapter.is_model_error(Exception("timeout waiting for upstream"))


def test_quota_error_detection():
    assert GeminiChatAdapter.is_quota_error(Exception("429 Resource exhausted: Quota exceeded"))
    assert not GeminiChatAdapter.is_quota_error(Exception("timeout waiting for upstream"))


def test_api_key_user_message_mentions_koyeb_env():
    message = GeminiChatAdapter.api_key_user_message()
    assert "GEMINI_API_KEY" in message
    assert "Koyeb" in message
