import types
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from admin_bot.handlers import start


@pytest.mark.asyncio
async def test_toggle_setting_time():
    callback = types.SimpleNamespace(
        from_user=types.SimpleNamespace(id=123),
        message=types.SimpleNamespace(
            edit_text=AsyncMock(),
            edit_reply_markup=AsyncMock(),
        ),
        answer=AsyncMock(),
    )

    db = MagicMock()
    db.get_user_settings = AsyncMock(
        return_value=types.SimpleNamespace(include_timestamp=False)
    )
    db.update_user_settings = AsyncMock()

    with patch.object(start, "_render_settings", new=AsyncMock()) as render:
        await start.toggle_setting_time(callback, db=db)
        render.assert_awaited_once_with(callback, db)

    db.update_user_settings.assert_awaited_once_with(123, include_timestamp=True)
    callback.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_toggle_setting_channel():
    callback = types.SimpleNamespace(
        from_user=types.SimpleNamespace(id=123),
        message=types.SimpleNamespace(
            edit_text=AsyncMock(),
            edit_reply_markup=AsyncMock(),
        ),
        answer=AsyncMock(),
    )

    db = MagicMock()
    db.get_user_settings = AsyncMock(
        return_value=types.SimpleNamespace(include_channel_info=True)
    )
    db.update_user_settings = AsyncMock()

    with patch.object(start, "_render_settings", new=AsyncMock()) as render:
        await start.toggle_setting_channel(callback, db=db)
        render.assert_awaited_once_with(callback, db)

    db.update_user_settings.assert_awaited_once_with(123, include_channel_info=False)
    callback.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_toggle_setting_link():
    callback = types.SimpleNamespace(
        from_user=types.SimpleNamespace(id=123),
        message=types.SimpleNamespace(
            edit_text=AsyncMock(),
            edit_reply_markup=AsyncMock(),
        ),
        answer=AsyncMock(),
    )

    db = MagicMock()
    db.get_user_settings = AsyncMock(
        return_value=types.SimpleNamespace(include_message_link=True)
    )
    db.update_user_settings = AsyncMock()

    with patch.object(start, "_render_settings", new=AsyncMock()) as render:
        await start.toggle_setting_link(callback, db=db)
        render.assert_awaited_once_with(callback, db)

    db.update_user_settings.assert_awaited_once_with(123, include_message_link=False)
    callback.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_toggle_setting_sender():
    callback = types.SimpleNamespace(
        from_user=types.SimpleNamespace(id=123),
        message=types.SimpleNamespace(
            edit_text=AsyncMock(),
            edit_reply_markup=AsyncMock(),
        ),
        answer=AsyncMock(),
    )

    db = MagicMock()
    db.get_user_settings = AsyncMock(
        return_value=types.SimpleNamespace(include_sender_id=False)
    )
    db.update_user_settings = AsyncMock()

    with patch.object(start, "_render_settings", new=AsyncMock()) as render:
        await start.toggle_setting_sender(callback, db=db)
        render.assert_awaited_once_with(callback, db)

    db.update_user_settings.assert_awaited_once_with(123, include_sender_id=True)
    callback.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_change_notification_format():
    callback = types.SimpleNamespace(
        from_user=types.SimpleNamespace(id=123),
        message=types.SimpleNamespace(
            edit_text=AsyncMock(),
            edit_reply_markup=AsyncMock(),
        ),
        answer=AsyncMock(),
    )

    db = MagicMock()
    db.get_user_settings = AsyncMock(
        return_value=types.SimpleNamespace(notification_format="full")
    )
    db.update_user_settings = AsyncMock()

    with patch.object(start, "_render_settings", new=AsyncMock()) as render:
        await start.change_notification_format(callback, db=db)
        render.assert_awaited_once_with(callback, db)

    db.update_user_settings.assert_awaited_once_with(123, notification_format="compact")
    callback.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_change_formatting_mode():
    callback = types.SimpleNamespace(
        from_user=types.SimpleNamespace(id=123),
        message=types.SimpleNamespace(
            edit_text=AsyncMock(),
            edit_reply_markup=AsyncMock(),
        ),
        answer=AsyncMock(),
    )

    db = MagicMock()
    db.get_user_settings = AsyncMock(
        return_value=types.SimpleNamespace(
            forward_as_code=False,
            include_original_formatting=True,
        )
    )
    db.update_user_settings = AsyncMock()

    with patch.object(start, "_render_settings", new=AsyncMock()) as render:
        await start.change_formatting_mode(callback, db=db)
        render.assert_awaited_once_with(callback, db)

    db.update_user_settings.assert_awaited_once_with(
        123,
        include_original_formatting=False,
    )
    callback.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_toggle_settings_monitoring():
    callback = types.SimpleNamespace(
        from_user=types.SimpleNamespace(id=123),
        message=types.SimpleNamespace(
            edit_text=AsyncMock(),
            edit_reply_markup=AsyncMock(),
            answer=AsyncMock(),
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
async def test_toggle_settings_monitoring_disable():
    callback = types.SimpleNamespace(
        from_user=types.SimpleNamespace(id=123),
        message=types.SimpleNamespace(
            edit_text=AsyncMock(),
            edit_reply_markup=AsyncMock(),
            answer=AsyncMock(),
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
