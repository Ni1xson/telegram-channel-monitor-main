import types
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from monitor.client import TelegramMonitorClient


@pytest.mark.asyncio
async def test_format_notification_wraps_code_block():
    client = TelegramMonitorClient(db=MagicMock())
    settings = types.SimpleNamespace(
        include_channel_info=False,
        include_timestamp=False,
        include_message_link=False,
        include_original_formatting=True,
        forward_as_code=True,
        max_message_length=4000,
        include_sender_id=False,
    )
    found_message = types.SimpleNamespace(message_text="print('hi')", matched_keywords=[])
    chat = types.SimpleNamespace()
    original_message = types.SimpleNamespace(date=None, id=1)

    text = await client._format_notification(found_message, chat, original_message, settings)

    assert "```" in text
    assert "<pre>" not in text
    assert "<b>" not in text
    assert "<code>" not in text


@pytest.mark.asyncio
async def test_send_notification_uses_markdown():
    client = TelegramMonitorClient(db=MagicMock(), bot=MagicMock())
    client.bot.send_message = AsyncMock()

    settings = types.SimpleNamespace(
        include_channel_info=False,
        include_timestamp=False,
        include_message_link=False,
        include_original_formatting=True,
        forward_as_code=True,
        max_message_length=4000,
        include_sender_id=False,
    )
    client.db.get_user_target_chats = AsyncMock(return_value=[types.SimpleNamespace(chat_id=100)])
    client.db.get_user_settings = AsyncMock(return_value=settings)

    found_message = types.SimpleNamespace(message_text="print('hi')", matched_keywords=[])
    chat = types.SimpleNamespace(username="test", title="test")
    original_message = types.SimpleNamespace(date=None, id=1)

    await client._send_notification(1, found_message, chat, original_message)

    client.bot.send_message.assert_awaited_once()
    args, kwargs = client.bot.send_message.call_args
    assert kwargs.get("parse_mode") == "Markdown"
    sent_text = args[1] if len(args) > 1 else kwargs.get("message")
    assert "```" in sent_text

@pytest.mark.asyncio
async def test_format_notification_shows_username():
    client = TelegramMonitorClient(db=MagicMock())
    settings = types.SimpleNamespace(
        include_channel_info=False,
        include_timestamp=False,
        include_message_link=False,
        include_original_formatting=True,
        forward_as_code=False,
        max_message_length=4000,
        include_sender_id=True,
    )
    found_message = types.SimpleNamespace(
        message_text="hi", matched_keywords=[], sender_username="alice", sender_id=123
    )
    chat = types.SimpleNamespace()
    original_message = types.SimpleNamespace(date=None, id=1)

    text = await client._format_notification(found_message, chat, original_message, settings)

    assert "@alice" in text

@pytest.mark.asyncio
async def test_send_notification_logs_excerpt_on_failure():
    from monitor import client as client_module

    client = TelegramMonitorClient(db=MagicMock(), bot=MagicMock())
    client.bot.send_message = AsyncMock()
    settings = types.SimpleNamespace(
        include_channel_info=False,
        include_timestamp=False,
        include_message_link=False,
        include_original_formatting=True,
        forward_as_code=False,
        max_message_length=4000,
        include_sender_id=False,
    )

    client.db.get_user_settings = AsyncMock(return_value=settings)

    found_message = types.SimpleNamespace(
        message_text="hello world " * 20,
        matched_keywords=[],
    )
    chat = types.SimpleNamespace()
    original_message = types.SimpleNamespace(date=None, id=1)

    expected_text = await client._format_notification(found_message, chat, original_message, settings)
    expected_excerpt = expected_text[:200]

    class FailingIterable:
        def __iter__(self):
            raise Exception("boom")

    client.db.get_user_target_chats = AsyncMock(return_value=FailingIterable())

    with patch.object(client_module, "logger") as logger_mock:
        await client._send_notification(1, found_message, chat, original_message)
        logger_mock.error.assert_called_once()
        logged_msg = logger_mock.error.call_args.args[0]
        assert expected_excerpt in logged_msg


@pytest.mark.asyncio
async def test_format_notification_escapes_html():
    client = TelegramMonitorClient(db=MagicMock())
    settings = types.SimpleNamespace(
        include_channel_info=False,
        include_timestamp=False,
        include_message_link=False,
        include_original_formatting=False,
        forward_as_code=False,
        max_message_length=4000,
        include_sender_id=False,
    )
    found_message = types.SimpleNamespace(message_text="<b>test</b>", matched_keywords=[])
    chat = types.SimpleNamespace()
    original_message = types.SimpleNamespace(date=None, id=1)

    text = await client._format_notification(found_message, chat, original_message, settings)

    assert "&lt;b&gt;test&lt;/b&gt;" in text


@pytest.mark.asyncio
@pytest.mark.parametrize("forward_as_code", [True, False])
async def test_channel_name_links_to_message(forward_as_code):
    client = TelegramMonitorClient(db=MagicMock())
    settings = types.SimpleNamespace(
        include_channel_info=True,
        include_timestamp=False,
        include_message_link=True,
        include_original_formatting=True,
        forward_as_code=forward_as_code,
        max_message_length=4000,
        include_sender_id=False,
    )
    found_message = types.SimpleNamespace(message_text="hi", matched_keywords=[])
    chat = types.SimpleNamespace(username="test", title="Test")
    original_message = types.SimpleNamespace(date=None, id=5)

    text = await client._format_notification(found_message, chat, original_message, settings)

    message_link = f"https://t.me/{chat.username}/{original_message.id}"
    channel_line = f"📢 {'**Канал:**' if forward_as_code else '<b>Канал:</b>'}"
    assert message_link in text
    # ensure the link is on the channel line
    for line in text.splitlines():
        if line.startswith(channel_line):
            assert message_link in line
            break
    else:
        pytest.fail("Channel line not found")
