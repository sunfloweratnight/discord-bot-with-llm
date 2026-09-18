"""Tests for Gemini user-facing API key error mapping."""

from __future__ import annotations

from src.Cogs.Gemini import Gemini


def test_api_key_error_detection():
    assert Gemini._is_api_key_error(Exception('API_KEY_INVALID'))
    assert Gemini._is_api_key_error(Exception('API key not valid. Please pass a valid API key.'))
    assert not Gemini._is_api_key_error(Exception('timeout waiting for upstream'))


def test_api_key_user_message_mentions_koyeb_env():
    message = Gemini._api_key_user_message()
    assert "GEMINI_API_KEY" in message
    assert "Koyeb" in message
