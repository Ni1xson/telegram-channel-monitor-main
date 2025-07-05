import types
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from config.config import Config
from admin_bot.handlers import start


@pytest.mark.asyncio
async def test_toggle_monitoring_cmd():
    Config.ALLOWED_USERS = [123]
    message = types.SimpleNamespace(
        from_user=types.SimpleNamespace(id=123),
        answer=AsyncMock(),
        bot=MagicMock(),
    )

    db = MagicMock()
    db.get_user_settings = AsyncMock(
        return_value=types.SimpleNamespace(monitoring_enabled=True)
    )
    db.set_monitoring_enabled = AsyncMock()

    monitor_client = MagicMock()
    monitor_client.set_monitoring_enabled = AsyncMock()

    with patch.object(start, "send_monitoring_summary", new=AsyncMock()) as summary:
        await start.toggle_monitoring_cmd(message, db=db, monitor_client=monitor_client)
        summary.assert_not_awaited()

    db.set_monitoring_enabled.assert_awaited_once_with(123, False)
    monitor_client.set_monitoring_enabled.assert_awaited_once_with(123, False)
    message.answer.assert_awaited_once_with("❌ Мониторинг выключен")


@pytest.mark.asyncio
async def test_toggle_monitoring_callback():
    Config.ALLOWED_USERS = [123]
    callback = types.SimpleNamespace(
        from_user=types.SimpleNamespace(id=123),
        message=types.SimpleNamespace(
            edit_text=AsyncMock(), edit_reply_markup=AsyncMock(), answer=AsyncMock()
        ),
        answer=AsyncMock(),
        bot=MagicMock(),
    )

    db = MagicMock()
    db.get_user_settings = AsyncMock(
        return_value=types.SimpleNamespace(monitoring_enabled=False)
    )
    db.set_monitoring_enabled = AsyncMock()

    monitor_client = MagicMock()
    monitor_client.set_monitoring_enabled = AsyncMock()

    with patch.object(start, "_render_settings", new=AsyncMock()) as render, \
        patch.object(start, "send_monitoring_summary", new=AsyncMock()) as summary:
        await start.toggle_monitoring(callback, db=db, monitor_client=monitor_client)
        render.assert_awaited_once_with(callback, db)
        summary.assert_awaited_once_with(callback.bot, db, 123)

    db.set_monitoring_enabled.assert_awaited_once_with(123, True)
    monitor_client.set_monitoring_enabled.assert_awaited_once_with(123, True)
    callback.answer.assert_awaited_once_with("✅ Мониторинг включен")
    callback.message.answer.assert_not_awaited()


@pytest.mark.asyncio
async def test_toggle_monitoring_callback_disable():
    Config.ALLOWED_USERS = [123]
    callback = types.SimpleNamespace(
        from_user=types.SimpleNamespace(id=123),
        message=types.SimpleNamespace(
            edit_text=AsyncMock(), edit_reply_markup=AsyncMock(), answer=AsyncMock()
        ),
        answer=AsyncMock(),
        bot=MagicMock(),
    )

    db = MagicMock()
    db.get_user_settings = AsyncMock(
        return_value=types.SimpleNamespace(monitoring_enabled=True)
    )
    db.set_monitoring_enabled = AsyncMock()

    monitor_client = MagicMock()
    monitor_client.set_monitoring_enabled = AsyncMock()

    with patch.object(start, "_render_settings", new=AsyncMock()) as render, \
        patch.object(start, "send_monitoring_summary", new=AsyncMock()) as summary:
        await start.toggle_monitoring(callback, db=db, monitor_client=monitor_client)
        render.assert_awaited_once_with(callback, db)
        summary.assert_not_awaited()

    db.set_monitoring_enabled.assert_awaited_once_with(123, False)
    monitor_client.set_monitoring_enabled.assert_awaited_once_with(123, False)
    callback.answer.assert_awaited_once_with("❌ Мониторинг выключен")
    callback.message.answer.assert_not_awaited()
