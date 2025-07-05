# -*- coding: utf-8 -*-
import os
import shutil
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from config.config import Config
from monitor.client import TelegramMonitorClient

router = Router()

@router.message(Command("ping"))
async def cmd_ping(message: Message, monitor_client: TelegramMonitorClient):
    if message.from_user.id not in Config.ALLOWED_USERS:
        await message.answer("❌ У вас нет доступа к этой команде.")
        return
    is_auth = await monitor_client.is_authorized()
    status = "✅ Сессия активна!" if is_auth else "❌ Сессия не авторизована!"
    await message.answer(f"🏓 {status}")

@router.message(Command("backup"))
async def cmd_backup(message: Message):
    if message.from_user.id not in Config.ALLOWED_USERS:
        await message.answer("❌ У вас нет доступа к этой команде.")
        return
    session_file = f"{Config.TELEGRAM_SESSION_NAME}.session"
    backup_file = f"{Config.TELEGRAM_SESSION_NAME}.session.bak"
    if not os.path.exists(session_file):
        await message.answer("❌ Файл сессии не найден!")
        return
    try:
        shutil.copyfile(session_file, backup_file)
        await message.answer("✅ Резервная копия сессии создана!")
    except Exception as e:
        await message.answer(f"❌ Ошибка при копировании: {e}")