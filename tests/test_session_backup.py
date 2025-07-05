import asyncio
import os
import shutil
import pytest
from unittest import mock
from monitor.client import TelegramMonitorClient
from config.config import Config

class DummyBot:
    def __init__(self):
        self.messages = []
    async def send_message(self, user_id, text):
        self.messages.append((user_id, text))

@pytest.mark.asyncio
async def test_session_backup_and_restore(tmp_path):
    Config.ADMIN_USER_ID = 123
    Config.TELEGRAM_SESSION_NAME = "testsession"
    session_file = tmp_path / "testsession.session"
    backup_file = tmp_path / "testsession.session.bak"
    session_file.write_bytes(b"sessiondata")
    client = TelegramMonitorClient(db=None, bot=DummyBot())
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        with mock.patch("os.path.exists", side_effect=lambda p: p in ["testsession.session", "testsession.session.bak"]), \
             mock.patch("shutil.copyfile") as m_copyfile:
            task = asyncio.create_task(client._session_backup_loop(interval=0.01))
            await asyncio.sleep(0.02)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            m_copyfile.assert_called_with("testsession.session", "testsession.session.bak")
    finally:
        os.chdir(old_cwd)

@pytest.mark.asyncio
async def test_restore_from_backup(tmp_path):
    Config.ADMIN_USER_ID = 123
    Config.TELEGRAM_SESSION_NAME = "testsession"
    session_file = tmp_path / "testsession.session"
    backup_file = tmp_path / "testsession.session.bak"
    backup_file.write_bytes(b"backupdata")
    client = TelegramMonitorClient(db=None, bot=DummyBot())
    client.client = mock.AsyncMock()
    client.is_authorized = mock.AsyncMock(side_effect=[False, True])
    client.client.connect = mock.AsyncMock()
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        with mock.patch("os.path.exists", return_value=True), \
             mock.patch("shutil.copyfile") as m_copyfile:
            await client.ensure_connected(interval=0.01)
            m_copyfile.assert_called_with("testsession.session.bak", "testsession.session")
    finally:
        os.chdir(old_cwd)

@pytest.mark.asyncio
async def test_notify_admin_on_restore_fail(tmp_path):
    Config.ADMIN_USER_ID = 123
    Config.TELEGRAM_SESSION_NAME = "testsession"
    backup_file = tmp_path / "testsession.session.bak"
    bot = DummyBot()
    client = TelegramMonitorClient(db=None, bot=bot)
    client.client = mock.AsyncMock()
    client.is_authorized = mock.AsyncMock(return_value=False)
    client.client.connect = mock.AsyncMock()
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        with mock.patch("os.path.exists", return_value=True), \
             mock.patch("shutil.copyfile"):
            await client.ensure_connected(interval=0.01)
        assert any("Требуется повторная авторизация" in msg for _, msg in bot.messages)
    finally:
        os.chdir(old_cwd) 