from src.Cogs.Utils import sanitize_args


def test_sanitize_args_strips_mentions_and_joins():
    assert sanitize_args(("<@12345>", "こんにちは")) == "こんにちは"
    assert sanitize_args(("a", "b")) == "a b"
