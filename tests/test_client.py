import asyncio
import types
import pytest
from unittest.mock import AsyncMock, MagicMock

from telethon.tl.types import PeerChannel

from monitor.client import TelegramMonitorClient
from database.models import FoundMessage
from unittest.mock import patch


@pytest.mark.asyncio
async def test_resolve_chat_peer_channel_call():
    client = TelegramMonitorClient(db=MagicMock())
    entity = types.SimpleNamespace(id=1234567890, title="Test", username="test")

    client.client = MagicMock()
    client.client.get_entity = AsyncMock(return_value=entity)

    with patch("monitor.client.get_peer_id", side_effect=lambda e: -(1000000000000 + e.id)):
        result = await client.resolve_chat("-1001234567890")

    client.client.get_entity.assert_awaited_once_with(PeerChannel(1234567890))
    assert result == {"id": -1001234567890, "title": "Test", "username": "test"}


@pytest.mark.asyncio
async def test_resolve_channel_peer_channel_call():
    client = TelegramMonitorClient(db=MagicMock())
    entity = types.SimpleNamespace(id=1234567890, title="Test", username="test")

    client.client = MagicMock()
    client.client.get_entity = AsyncMock(return_value=entity)

    with patch("monitor.client.get_peer_id", side_effect=lambda e: -(1000000000000 + e.id)):
        result = await client.resolve_channel("-1001234567890")

    client.client.get_entity.assert_awaited_once_with(PeerChannel(1234567890))
    assert result == {"id": -1001234567890, "title": "Test", "username": "test"}


@pytest.mark.asyncio
async def test_start_runs_until_disconnected():
    db = MagicMock()
    tele_client = MagicMock()
    tele_client.start = AsyncMock()
    tele_client.run_until_disconnected = AsyncMock()

    with patch("monitor.client.TelegramClient", return_value=tele_client):
        client = TelegramMonitorClient(db=db)
        client._load_data = AsyncMock()
        client._register_handlers = MagicMock()
        await client.start()

    tele_client.start.assert_awaited_once()
    client._register_handlers.assert_called_once()
    tele_client.run_until_disconnected.assert_awaited_once()
    assert client.running is False


@pytest.mark.asyncio
async def test_message_event_triggers_handler():
    db = MagicMock()
    tele_client = MagicMock()
    tele_client.start = AsyncMock()
    run_future = asyncio.Future()

    async def run_until_disconnected():
        await run_future

    tele_client.run_until_disconnected = AsyncMock(side_effect=run_until_disconnected)

    handlers = []

    def on(event):
        def decorator(func):
            handlers.append(func)
            return func
        return decorator

    tele_client.on = on

    with patch("monitor.client.TelegramClient", return_value=tele_client), \
        patch("monitor.client.get_peer_id", lambda chat: chat.id):
        client = TelegramMonitorClient(db=db)

        async def fake_load_data():
            client.monitored_channels = {1: {10}}
            client.user_monitoring = {1: True}

        client._load_data = AsyncMock(side_effect=fake_load_data)
        start_task = asyncio.create_task(client.start())
        await asyncio.sleep(0)  # allow start()

        assert client.running is True
        assert handlers

        handler = handlers[0]
        client._process_new_message = AsyncMock()

        event = types.SimpleNamespace(
            out=False,
            message=types.SimpleNamespace(text="hi", id=5, out=False),
            get_chat=AsyncMock(return_value=types.SimpleNamespace(id=10)),
        )

        await handler(event)
        client._process_new_message.assert_awaited_once_with(event)

        run_future.set_result(None)
        await start_task


@pytest.mark.asyncio
async def test_process_message_saves_sender_id():
    db = MagicMock()
    db.save_found_message = AsyncMock(return_value=1)
    db.get_user_target_chats = AsyncMock(return_value=[])
    db.get_user_settings = AsyncMock()

    client = TelegramMonitorClient(db=db)
    client.running = True
    client.monitored_channels = {1: {10}}
    client.user_monitoring = {1: True}
    client.filter_manager.check_message_all_filters = MagicMock(
        return_value=[types.SimpleNamespace(filter_id=1, matched_keywords=["x"])]
    )
    client._send_notification = AsyncMock()

    message = types.SimpleNamespace(text="x", id=5, sender_id=42)
    event = types.SimpleNamespace(
        out=False,
        message=message,
        get_chat=AsyncMock(return_value=types.SimpleNamespace(id=10)),
        get_sender=AsyncMock(return_value=types.SimpleNamespace(username="bob")),
    )

    with patch("monitor.client.get_peer_id", lambda chat: chat.id):
        await client._process_new_message(event)

    saved = db.save_found_message.call_args.args[0]
    assert saved.sender_id == 42
    assert saved.sender_username == "bob"
