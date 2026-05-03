import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test_token")
os.environ.setdefault("OPENROUTER_API_KEY", "test_key")

from services.openrouter import OpenRouterError, RateLimitError


def test_error_hierarchy():
    assert issubclass(RateLimitError, OpenRouterError)
    err = OpenRouterError("test")
    assert str(err) == "test"


def test_rate_limit_error():
    err = RateLimitError("Rate limit hit")
    assert isinstance(err, OpenRouterError)


@pytest.mark.asyncio
async def test_chat_success():
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        "choices": [{"message": {"content": "Привет!"}}],
        "usage": {"total_tokens": 42},
    })
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.post = MagicMock(return_value=mock_response)
    mock_session.closed = False

    with patch("services.openrouter.get_session", return_value=mock_session):
        from services.openrouter import chat
        result, tokens = await chat([{"role": "user", "content": "Привет"}])
        assert result == "Привет!"
        assert tokens == 42


@pytest.mark.asyncio
async def test_chat_error_raises():
    mock_response = MagicMock()
    mock_response.status = 500
    mock_response.text = AsyncMock(return_value="Internal Server Error")
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.post = MagicMock(return_value=mock_response)
    mock_session.closed = False

    with patch("services.openrouter.get_session", return_value=mock_session):
        from services.openrouter import chat
        with pytest.raises(OpenRouterError):
            await chat([{"role": "user", "content": "test"}])
