import asyncio
import types
import signal
import pytest
from unittest.mock import AsyncMock, patch

from main import TelegramMonitorApp


@pytest.mark.asyncio
async def test_signal_shutdown_stops_all_tasks():
    app = TelegramMonitorApp()
    stop_event = asyncio.Event()

    async def wait_stop():
        await stop_event.wait()

    async def trigger_stop():
        stop_event.set()

    app.monitor_client = types.SimpleNamespace(
        start=AsyncMock(side_effect=wait_stop),
        stop=AsyncMock(side_effect=trigger_stop),
        bot=None,
    )
    app.admin_bot = types.SimpleNamespace(
        start=AsyncMock(side_effect=wait_stop),
        stop=AsyncMock(),
        bot=None,
    )

    handlers = {}

    def fake_signal(sig, handler):
        handlers[sig] = handler

    with patch("signal.signal", side_effect=fake_signal), patch(
        "asyncio.sleep", new=AsyncMock()
    ):
        app.setup_signal_handlers()
        task = asyncio.create_task(app.start())
        await asyncio.sleep(0)
        handlers[signal.SIGINT](signal.SIGINT, None)
        await asyncio.wait_for(task, timeout=0.5)

    app.monitor_client.stop.assert_awaited_once()
    app.admin_bot.stop.assert_awaited_once()
    assert app.running is False
