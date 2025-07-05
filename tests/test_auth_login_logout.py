import types
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

from config.config import Config
from admin_bot.handlers import auth
from admin_bot.utils.states import AuthStates


@pytest.mark.asyncio
async def test_cmd_login_allowed_user():
    Config.ALLOWED_USERS = [123]
    message = types.SimpleNamespace(
        from_user=types.SimpleNamespace(id=123),
        answer=AsyncMock(),
    )
    state = types.SimpleNamespace(set_state=AsyncMock())
    monitor_client = MagicMock()
    monitor_client.is_authorized = AsyncMock(return_value=False)

    with patch.object(auth, "send_menu_message", new=AsyncMock()) as send_msg:
        await auth.cmd_login(message, state=state, monitor_client=monitor_client)
        send_msg.assert_awaited_once()

    assert not any(
        call.args[0] == "❌ У вас нет доступа к этому боту." for call in message.answer.await_args_list
    )
    state.set_state.assert_called_once_with(AuthStates.waiting_phone)


@pytest.mark.asyncio
async def test_cb_login_allowed_user():
    Config.ALLOWED_USERS = [123]
    callback = types.SimpleNamespace(
        from_user=types.SimpleNamespace(id=123),
        message=types.SimpleNamespace(answer=AsyncMock()),
        answer=AsyncMock(),
    )
    state = types.SimpleNamespace(set_state=AsyncMock())
    monitor_client = MagicMock()
    monitor_client.is_authorized = AsyncMock(return_value=False)

    with patch.object(auth, "send_menu_message", new=AsyncMock()):
        await auth.cb_login(callback, state=state, monitor_client=monitor_client)

    callback.answer.assert_awaited()


@pytest.mark.asyncio
async def test_cmd_logout_allowed_user():
    Config.ALLOWED_USERS = [123]
    message = types.SimpleNamespace(
        from_user=types.SimpleNamespace(id=123),
        answer=AsyncMock(),
    )
    monitor_client = MagicMock()
    client = monitor_client.client = MagicMock()
    client.log_out = AsyncMock()
    client.disconnect = AsyncMock()

    await auth.cmd_logout(message, monitor_client=monitor_client)

    client.log_out.assert_awaited_once()
    client.disconnect.assert_awaited_once()
    message.answer.assert_any_await("✅ Вы вышли из аккаунта")
    assert not any(
        call.args[0] == "❌ У вас нет доступа к этому боту." for call in message.answer.await_args_list
    )


@pytest.mark.asyncio
async def test_cb_logout_allowed_user():
    Config.ALLOWED_USERS = [123]
    callback = types.SimpleNamespace(
        from_user=types.SimpleNamespace(id=123),
        message=types.SimpleNamespace(answer=AsyncMock()),
        answer=AsyncMock(),
    )
    monitor_client = MagicMock()
    client = monitor_client.client = MagicMock()
    client.log_out = AsyncMock()
    client.disconnect = AsyncMock()

    await auth.cb_logout(callback, monitor_client=monitor_client)

    client.log_out.assert_awaited_once()
    callback.answer.assert_awaited_once()
