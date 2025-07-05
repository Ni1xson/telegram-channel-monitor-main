# -*- coding: utf-8 -*-
import asyncio
import base64
import glob
import logging
import os
import sys
from pathlib import Path
from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from telethon.errors import PhoneCodeInvalidError, SessionPasswordNeededError
from telethon import TelegramClient

from config.config import Config
from admin_bot.utils.states import AuthStates
from admin_bot.keyboards.keyboards import AdminKeyboards
from admin_bot.utils.menu import send_menu_message
from monitor.client import TelegramMonitorClient

logger = logging.getLogger(__name__)

router = Router()


@router.message(F.text == "👤 User клиент")
async def open_user_client_menu(message: Message, monitor_client: TelegramMonitorClient, state: FSMContext):
    await state.clear()
    if message.from_user.id not in Config.ALLOWED_USERS:
        return
    authorized = await monitor_client.is_authorized()
    user_info = None
    if authorized and monitor_client.client:
        try:
            me = await monitor_client.client.get_me()
            if getattr(me, 'username', None):
                username = f"@{me.username}"
            elif getattr(me, 'first_name', None):
                username = me.first_name
            else:
                username = str(me.id)
            user_info = f"<b>Подключён как:</b> {username} (ID: {me.id})"
        except Exception:
            user_info = "<b>Подключён</b>"
    else:
        user_info = "<b>❌ Не авторизован</b>"
    await send_menu_message(
        message,
        f"👤 <b>User клиент</b>\n\n{user_info}\n\n<b>Выберите действие:</b>",
        reply_markup=AdminKeyboards.user_client_menu(authorized),
    )


@router.message(Command("login"))
async def cmd_login(
    message: Message, state: FSMContext, monitor_client: TelegramMonitorClient
):
    """Старт авторизации пользователя."""
    await _cmd_login(message, message.from_user.id, state, monitor_client)


async def _cmd_login(
    message: Message,
    user_id: int,
    state: FSMContext,
    monitor_client: TelegramMonitorClient,
):
    """Start user authorization."""
    if user_id not in Config.ALLOWED_USERS:
        await message.answer("❌ У вас нет доступа к этому боту.")
        return

    if await monitor_client.is_authorized():
        await message.answer("✅ Пользовательский клиент уже авторизован")
        return

    await state.set_state(AuthStates.waiting_phone)
    await send_menu_message(
        message,
        "📱 <b>Введите номер телефона</b> (в международном формате):",
        reply_markup=AdminKeyboards.cancel(),
    )


@router.callback_query(F.data == "user_login")
async def cb_login(callback: CallbackQuery, state: FSMContext, monitor_client: TelegramMonitorClient):
    await _cmd_login(callback.message, callback.from_user.id, state, monitor_client)
    await callback.answer()


@router.message(AuthStates.waiting_phone)
async def process_phone(message: Message, state: FSMContext, monitor_client: TelegramMonitorClient):
    phone = message.text.strip()
    try:
        await monitor_client.send_code(phone)
    except Exception as e:  # pragma: no cover - network/telethon errors
        logger.exception("Failed to send code", exc_info=e)
        await message.answer("Ошибка отправки кода. Попробуйте позже.")
        await state.clear()
        return

    await state.update_data(phone=phone)
    await state.set_state(AuthStates.waiting_code)
    await message.answer("✉️ Код отправлен. Введите его:")


@router.message(AuthStates.waiting_code)
async def process_code(message: Message, state: FSMContext, monitor_client: TelegramMonitorClient):
    data = await state.get_data()
    phone = data.get("phone")
    code = message.text.strip()
    try:
        await monitor_client.sign_in(phone, code)
    except SessionPasswordNeededError:
        await state.update_data(code=code)
        await state.set_state(AuthStates.waiting_password)
        await message.answer("🔒 Введите пароль двухфакторной аутентификации:")
        return
    except PhoneCodeInvalidError:
        await message.answer("Неверный код. Попробуйте ещё раз или /cancel")
        return
    except Exception as e:  # pragma: no cover - unexpected
        logger.exception("Failed to sign in", exc_info=e)
        await message.answer("Ошибка авторизации. Попробуйте ещё раз позже.")
        await state.clear()
        return

    await state.clear()
    await message.answer("✅ Авторизация успешна")


@router.message(AuthStates.waiting_password)
async def process_password(message: Message, state: FSMContext, monitor_client: TelegramMonitorClient):
    data = await state.get_data()
    phone = data.get("phone")
    code = data.get("code")
    password = message.text.strip()
    try:
        await monitor_client.sign_in(phone, code=None, password=password)
    except Exception as e:  # pragma: no cover - invalid password etc
        logger.exception("Failed to sign in with password", exc_info=e)
        await message.answer("Ошибка авторизации. Проверьте пароль.")
        await state.clear()
        return

    await state.clear()
    await message.answer("✅ Авторизация успешна")


@router.message(Command("logout"))
async def cmd_logout(
    message: Message, monitor_client: TelegramMonitorClient
):
    """Команда выхода из пользовательского аккаунта."""
    await _cmd_logout(message, message.from_user.id, monitor_client)


async def _cmd_logout(
    message: Message, user_id: int, monitor_client: TelegramMonitorClient
):
    """Log out from the user account."""
    if user_id not in Config.ALLOWED_USERS:
        await message.answer("❌ У вас нет доступа к этому боту.")
        return

    if not monitor_client.client:
        await message.answer("Клиент не запущен.")
        return
    try:
        await monitor_client.client.log_out()
        await monitor_client.client.disconnect()
        monitor_client.client = None
        await message.answer("✅ Вы вышли из аккаунта")
    except Exception as e:  # pragma: no cover - unexpected
        logger.exception("Failed to logout", exc_info=e)
        await message.answer("Ошибка выхода из аккаунта")


@router.callback_query(F.data == "user_logout")
async def cb_logout(callback: CallbackQuery, monitor_client: TelegramMonitorClient):
    await _cmd_logout(callback.message, callback.from_user.id, monitor_client)
    await callback.answer()


@router.callback_query(F.data == "user_sessions")
async def list_sessions(callback: CallbackQuery):
    """Отобразить список доступных файлов сессий."""
    if callback.from_user.id not in Config.ALLOWED_USERS:
        await callback.answer("Нет доступа", show_alert=True)
        return

    sessions = glob.glob("*.session")
    if not sessions:
        text = "ℹ️ Сессионные файлы не найдены."
    else:
        lines = ["🗂 <b>Список сессий:</b>", ""]
        for name in sessions:
            authorized = False
            try:
                tmp = TelegramClient(
                    name.replace(".session", ""),
                    Config.TELEGRAM_API_ID,
                    Config.TELEGRAM_API_HASH,
                )
                await tmp.connect()
                authorized = await tmp.is_user_authorized()
            except Exception as e:  # pragma: no cover - network issues
                logger.exception("Failed to check session", exc_info=e)
            finally:
                try:
                    await tmp.disconnect()
                except Exception:
                    pass

            mark = "✅" if authorized else "❌"
            lines.append(f"{mark} <b>{name}</b>")

        text = "\n".join(lines)

    await callback.message.edit_text(
        text,
        reply_markup=AdminKeyboards.back_main(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "user_delete_session")
async def choose_session_to_delete(callback: CallbackQuery):
    """Выбор сессионного файла для удаления."""
    if callback.from_user.id not in Config.ALLOWED_USERS:
        await callback.answer("Нет доступа", show_alert=True)
        return

    sessions = glob.glob("*.session")
    if not sessions:
        await callback.message.edit_text(
            "❌ Сессионные файлы не найдены.",
            reply_markup=AdminKeyboards.back_main(),
        )
        await callback.answer()
        return

    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    keyboard = []
    for s in sessions[:10]:
        encoded = base64.urlsafe_b64encode(s.encode()).decode()
        keyboard.append(
            [InlineKeyboardButton(text=s, callback_data=f"delete_session_{encoded}")]
        )

    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")])

    await callback.message.edit_text(
        "❌ <b>Удалить сессию</b>\n\nВыберите файл:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("delete_session_"))
async def delete_session(callback: CallbackQuery, monitor_client: TelegramMonitorClient):
    """Удалить выбранный файл сессии."""
    if callback.from_user.id not in Config.ALLOWED_USERS:
        await callback.answer("Нет доступа", show_alert=True)
        return

    encoded = callback.data.replace("delete_session_", "")
    try:
        name = base64.urlsafe_b64decode(encoded.encode()).decode()
    except Exception:
        await callback.answer("Некорректные данные", show_alert=True)
        return

    try:
        os.remove(name)
        journal = name + "-journal"
        if os.path.exists(journal):
            os.remove(journal)
    except FileNotFoundError:
        text = "❌ Файл не найден"
    except Exception as e:  # pragma: no cover - filesystem errors
        logger.exception("Failed to delete session", exc_info=e)
        text = "❌ Ошибка удаления"
    else:
        text = f"✅ Сессия {name} удалена"

    authorized = await monitor_client.is_authorized()
    await callback.message.edit_text(
        text,
        reply_markup=AdminKeyboards.user_client_menu(authorized),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "user_cli_login")
async def run_cli_login(callback: CallbackQuery, monitor_client: TelegramMonitorClient):
    """Запустить CLI авторизацию или показать инструкцию."""
    if callback.from_user.id not in Config.ALLOWED_USERS:
        await callback.answer("Нет доступа", show_alert=True)
        return
    try:
        await callback.message.answer(
            "💻 Запускаю авторизацию в консоли. Следуйте инструкциям в терминале..."
        )
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "scripts.cli_login",
            cwd=str(Path(__file__).resolve().parents[2]),
        )
        await proc.wait()
        authorized = await monitor_client.is_authorized()
        if proc.returncode == 0 and authorized:
            result = "✅ Авторизация завершена"
        else:
            result = "❌ Авторизация не удалась"
        await callback.message.answer(result)
    except Exception:
        await callback.message.answer(
            "ℹ️ Не удалось запустить процесс авторизации на сервере.\n\n"
            "<b>Что делать?</b>\n"
            "1. Откройте терминал на сервере.\n"
            "2. Выполните команду:\n"
            "<code>python3 scripts/cli_login.py</code>\n"
            "3. Следуйте инструкциям в консоли.\n"
            "4. После успешной авторизации вернитесь в бота."
        )
    await callback.answer()
