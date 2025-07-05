import types
import pytest
from unittest.mock import AsyncMock, MagicMock

from config.config import Config
from admin_bot.handlers import start


@pytest.mark.asyncio
async def test_cmd_health_calls_client_and_formats():
    Config.ALLOWED_USERS = [123]
    message = types.SimpleNamespace(
        from_user=types.SimpleNamespace(id=123),
        answer=AsyncMock(),
    )
    monitor_client = MagicMock()
    monitor_client.check_health = AsyncMock(
        return_value={"chan1": True, "chan2": False}
    )

    await start.cmd_health(message, monitor_client=monitor_client)

    monitor_client.check_health.assert_awaited_once_with(123)
    message.answer.assert_awaited()
    text = message.answer.call_args.args[0]
    assert "chan1" in text and "chan2" in text


@pytest.mark.asyncio
async def test_cmd_health_denied_for_unknown_user():
    Config.ALLOWED_USERS = []
    message = types.SimpleNamespace(
        from_user=types.SimpleNamespace(id=555),
        answer=AsyncMock(),
    )
    monitor_client = MagicMock()

    await start.cmd_health(message, monitor_client=monitor_client)

    monitor_client.check_health.assert_not_called()
    message.answer.assert_awaited_once_with("❌ У вас нет доступа к этому боту.")
