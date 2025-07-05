import types
import pytest
from unittest.mock import AsyncMock, MagicMock

from admin_bot.handlers import start


@pytest.mark.asyncio
async def test_compose_status_uses_runtime_enabled():
    db = MagicMock()
    db.count_user_filters = AsyncMock(return_value=1)
    db.count_user_channels = AsyncMock(return_value=1)
    db.count_messages_today = AsyncMock(return_value=0)
    db.get_user_settings = AsyncMock(
        return_value=types.SimpleNamespace(monitoring_enabled=False)
    )

    monitor_client = MagicMock()
    monitor_client.running = True
    monitor_client.is_authorized = AsyncMock(return_value=True)
    monitor_client.is_monitoring_enabled = MagicMock(return_value=True)

    text = await start._compose_status_text(123, db=db, monitor_client=monitor_client)

    assert "🔍 Мониторинг: ✅ Включен" in text
    assert "📡 Активность: ✅ Активна" in text


@pytest.mark.asyncio
async def test_compose_status_uses_runtime_disabled():
    db = MagicMock()
    db.count_user_filters = AsyncMock(return_value=1)
    db.count_user_channels = AsyncMock(return_value=1)
    db.count_messages_today = AsyncMock(return_value=0)
    db.get_user_settings = AsyncMock(
        return_value=types.SimpleNamespace(monitoring_enabled=True)
    )

    monitor_client = MagicMock()
    monitor_client.running = True
    monitor_client.is_authorized = AsyncMock(return_value=True)
    monitor_client.is_monitoring_enabled = MagicMock(return_value=False)

    text = await start._compose_status_text(123, db=db, monitor_client=monitor_client)

    assert "🔍 Мониторинг: ❌ Выключен" in text
    assert "📡 Активность: ❌ Неактивна" in text
