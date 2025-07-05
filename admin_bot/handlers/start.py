# -*- coding: utf-8 -*-
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from config.config import Config
from admin_bot.keyboards.keyboards import AdminKeyboards
from admin_bot.utils import send_menu_message, send_monitoring_summary
from database.db import Database
from monitor.client import TelegramMonitorClient

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("cancel"))
@router.message(F.text.casefold() == "отмена")
async def cancel_action(message: Message, state: FSMContext):
    """Отмена текущего действия"""
    await state.clear()
    await send_menu_message(
        message,
        "🏠 <b>Главное меню</b>\n\nВыберите нужный раздел:",
        reply_markup=AdminKeyboards.main_menu(),
    )


@router.callback_query(F.data == "cancel")
async def cancel_callback(callback: CallbackQuery, state: FSMContext):
    """Отмена действия через кнопку"""
    await state.clear()
    try:
        await callback.message.edit_text(
            "🏠 <b>Главное меню</b>\n\nВыберите нужный раздел:",
            reply_markup=AdminKeyboards.main_menu(),
            parse_mode="HTML",
        )
    except Exception:
        await send_menu_message(
            callback.message,
            "🏠 <b>Главное меню</b>\n\nВыберите нужный раздел:",
            reply_markup=AdminKeyboards.main_menu(),
        )
    await callback.answer("Действие отменено")


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    await state.clear()

    # Проверяем права доступа
    if message.from_user.id not in Config.ALLOWED_USERS:
        await message.answer("❌ У вас нет доступа к этому боту.")
        return

    welcome_text = """
🤖 <b>Телеграм Мониторинг - Админка</b>

Добро пожаловать в панель управления системой мониторинга каналов!

<b>Возможности:</b>
📝 Управление фильтрами сообщений
📢 Управление отслеживаемыми каналами
🎯 Настройка целевых чатов для уведомлений
⚙️ Персональные настройки
📊 Просмотр статистики

Выберите нужный раздел из меню ниже.
    """

    await send_menu_message(
        message,
        welcome_text,
        reply_markup=AdminKeyboards.main_menu(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    if message.from_user.id not in Config.ALLOWED_USERS:
        await message.answer("❌ У вас нет доступа к этому боту.")
        return

    help_text = """
🆘 <b>Справка по использованию</b>

<b>📝 Фильтры:</b>
• Содержит - ищет любое из ключевых слов
• Точное совпадение - ищет точное слово
• Все слова - все ключевые слова должны быть в сообщении
• Фраза - ищет точную фразу
• Регулярное выражение - использует regex паттерны
• Не содержит - исключает сообщения с ключевыми словами

<b>📢 Каналы:</b>
• Добавляйте каналы по username (например: @channel_name)
  или по ID (например: -1001234567890)
• Можно отключать/включать мониторинг канала
• Поддерживается до {max_channels} каналов

<b>🎯 Целевые чаты:</b>
• Укажите ID чата или перешлите сообщение из целевого чата
• Все найденные сообщения будут отправляться в эти чаты

<b>⚙️ Настройки:</b>
• Настройте формат уведомлений
• Включите/отключите показ времени, каналов, ссылок
• Настройте максимальную длину сообщений

<b>🔧 Команды:</b>
/start - главное меню
/help - эта справка
/status - статус и статистика
Откройте «👤 User клиент» для управления сессиями и консольной авторизацией.
    """.format(
        max_channels=Config.MAX_MONITORED_CHANNELS
    )

    await send_menu_message(message, help_text, reply_markup=AdminKeyboards.back_main())


@router.message(F.text == "ℹ️ Помощь")
async def help_menu(message: Message, state: FSMContext):
    await cmd_help(message)


@router.message(Command("status"))
async def cmd_status(
    message: Message, db: Database, monitor_client: TelegramMonitorClient
):
    """Обработчик команды /status."""
    if message.from_user.id not in Config.ALLOWED_USERS:
        await message.answer("❌ У вас нет доступа к этому боту.")
        return

    user_id = message.from_user.id

    filters = await db.get_user_filters(user_id)
    channels = await db.get_user_channels(user_id)
    found_today = await db.get_today_found_messages_count(user_id)
    settings = await db.get_user_settings(user_id)

    authorized = await monitor_client.is_authorized()
    user_client_status = "✅ Авторизован" if authorized else "❌ Не авторизован"
    monitoring_active = (
        monitor_client.running and channels and settings and settings.monitoring_enabled

    )

    await message.answer(
        status_text,
        parse_mode="HTML",
        reply_markup=AdminKeyboards.back_main(),
    )


@router.message(Command("health"))
async def cmd_health(message: Message, monitor_client: TelegramMonitorClient):
    """Check accessibility of monitored channels."""
    if message.from_user.id not in Config.ALLOWED_USERS:
        await message.answer("❌ У вас нет доступа к этому боту.")
        return

    try:
        report = await monitor_client.check_health(message.from_user.id)
    except Exception as e:  # pragma: no cover - unexpected errors
        logger.exception("Health check failed", exc_info=e)
        await message.answer("Ошибка проверки состояния каналов")
        return

    if not report:
        await message.answer("Список каналов пуст.")
        return

    lines = ["🩺 <b>Проверка каналов</b>", ""]
    for name, ok in report.items():
        mark = "✅" if ok else "❌"
        lines.append(f"{mark} {name}")

    await message.answer("\n".join(lines), parse_mode="HTML")


@router.callback_query(F.data == "back_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    try:
        await callback.message.edit_text(
            "🏠 <b>Главное меню</b>\n\nВыберите нужный раздел:",
            reply_markup=AdminKeyboards.main_menu(),
            parse_mode="HTML",
        )
    except Exception:
        await send_menu_message(
            callback.message,
            "🏠 <b>Главное меню</b>\n\nВыберите нужный раздел:",
            reply_markup=AdminKeyboards.main_menu(),
        )
    await callback.answer()


@router.message(F.text == "⚙️ Настройки")
async def open_settings(message: Message, state: FSMContext, db: Database):
    await state.clear()
    settings = await db.get_user_settings(message.from_user.id)
    await send_menu_message(
        message,
        "⚙️ <b>Настройки</b>\n\nВыберите параметр для изменения:",
        reply_markup=AdminKeyboards.settings_menu(settings),
    )


@router.message(F.text == "📊 Статистика")
async def open_stats(
    message: Message,
    state: FSMContext,
    db: Database,
    monitor_client: TelegramMonitorClient,
):
    """Отображает текущий статус системы и статистику."""
    await state.clear()

    status_text = await _compose_status_text(
        message.from_user.id, db=db, monitor_client=monitor_client
    )

    await send_menu_message(
        message,
        status_text,
        reply_markup=AdminKeyboards.back_main(),
    )


async def _compose_status_text(
    user_id: int,
    db: Database,
    monitor_client: TelegramMonitorClient,
) -> str:
    """Собирает текст статуса со статистикой."""

    filters_count = await db.count_user_filters(user_id)
    channels_count = await db.count_user_channels(user_id)
    found_today = await db.count_messages_today(user_id)
    settings = await db.get_user_settings(user_id)

    authorized = await monitor_client.is_authorized()
    user_client_status = "✅ Подключен" if authorized else "❌ Отключен"
    monitoring_enabled = monitor_client.is_monitoring_enabled(user_id)
    monitoring_active = monitor_client.running and channels_count and monitoring_enabled
    monitoring_status = "✅ Включен" if monitoring_enabled else "❌ Выключен"

    status_text = (
        "📊 <b>Статус системы</b>\n\n"
        "🤖 Админ-бот: ✅ Работает\n"
        f"👤 User-клиент: {user_client_status}\n"
        "💾 База данных: ✅ Доступна\n"
        f"🔍 Мониторинг: {monitoring_status}\n"
        f"📡 Активность: {'✅ Активна' if monitoring_active else '❌ Неактивна'}\n\n"
        "📈 <b>Статистика:</b>\n"
        f"• Активных фильтров: {filters_count}\n"
        f"• Отслеживаемых каналов: {channels_count}\n"
        f"• Найдено сообщений сегодня: {found_today}"
    )

    return status_text


async def _render_settings(callback: CallbackQuery, db: Database):
    settings = await db.get_user_settings(callback.from_user.id)
    try:
        await callback.message.edit_text(
            "⚙️ <b>Настройки</b>\n\nВыберите параметр для изменения:",
            reply_markup=AdminKeyboards.settings_menu(settings),
            parse_mode="HTML",
        )
    except Exception:
        try:
            await callback.message.edit_reply_markup(
                reply_markup=AdminKeyboards.settings_menu(settings)
            )
        except TelegramBadRequest as e:
            if "message is not modified" in str(e).lower():
                return
            logger.exception("Failed to render settings", exc_info=e)
            await send_menu_message(
                callback.message,
                "⚙️ <b>Настройки</b>\n\nВыберите параметр для изменения:",
                reply_markup=AdminKeyboards.settings_menu(settings),
            )
        except Exception as e:
            logger.exception("Failed to render settings", exc_info=e)
            await send_menu_message(
                callback.message,
                "⚙️ <b>Настройки</b>\n\nВыберите параметр для изменения:",
                reply_markup=AdminKeyboards.settings_menu(settings),
            )


@router.callback_query(F.data == "settings_time")
async def toggle_setting_time(callback: CallbackQuery, db: Database):
    user_id = callback.from_user.id
    settings = await db.get_user_settings(user_id)
    await db.update_user_settings(
        user_id, include_timestamp=not settings.include_timestamp
    )
    await _render_settings(callback, db)
    await callback.answer("Настройка сохранена")


@router.callback_query(F.data == "settings_channel")
async def toggle_setting_channel(callback: CallbackQuery, db: Database):
    user_id = callback.from_user.id
    settings = await db.get_user_settings(user_id)
    await db.update_user_settings(
        user_id, include_channel_info=not settings.include_channel_info
    )
    await _render_settings(callback, db)
    await callback.answer("Настройка сохранена")


@router.callback_query(F.data == "settings_link")
async def toggle_setting_link(callback: CallbackQuery, db: Database):
    user_id = callback.from_user.id
    settings = await db.get_user_settings(user_id)
    await db.update_user_settings(
        user_id, include_message_link=not settings.include_message_link
    )
    await _render_settings(callback, db)
    await callback.answer("Настройка сохранена")


@router.callback_query(F.data == "settings_sender")
async def toggle_setting_sender(callback: CallbackQuery, db: Database):
    user_id = callback.from_user.id
    settings = await db.get_user_settings(user_id)
    await db.update_user_settings(
        user_id, include_sender_id=not settings.include_sender_id
    )
    await _render_settings(callback, db)
    await callback.answer("Настройка сохранена")


@router.callback_query(F.data == "settings_format")
async def change_notification_format(callback: CallbackQuery, db: Database):
    user_id = callback.from_user.id
    settings = await db.get_user_settings(user_id)
    formats = ["full", "compact", "minimal"]
    current = settings.notification_format if settings else "full"
    try:
        idx = formats.index(current)
    except ValueError:
        idx = 0
    next_format = formats[(idx + 1) % len(formats)]
    await db.update_user_settings(user_id, notification_format=next_format)
    await _render_settings(callback, db)
    await callback.answer("Настройка сохранена")


@router.callback_query(F.data == "settings_formatting")
async def change_formatting_mode(callback: CallbackQuery, db: Database):
    user_id = callback.from_user.id
    settings = await db.get_user_settings(user_id)
    if settings.forward_as_code:
        await db.update_user_settings(
            user_id,
            forward_as_code=False,
            include_original_formatting=True,
        )
    elif settings.include_original_formatting:
        await db.update_user_settings(
            user_id,
            include_original_formatting=False,
        )
    else:
        await db.update_user_settings(user_id, forward_as_code=True)
    await _render_settings(callback, db)
    await callback.answer("Настройка сохранена")


@router.callback_query(F.data == "settings_monitoring")
async def toggle_monitoring(
    callback: CallbackQuery, db: Database, monitor_client: TelegramMonitorClient
):
    user_id = callback.from_user.id
    settings = await db.get_user_settings(user_id)
    new_value = not settings.monitoring_enabled
    await db.set_monitoring_enabled(user_id, new_value)
    if monitor_client:
        await monitor_client.set_monitoring_enabled(user_id, new_value)

    status_msg = (
        "✅ Мониторинг включен" if new_value else "❌ Мониторинг выключен"
    )
    logger.info(
        "User %s monitoring %s",
        user_id,
        "enabled" if new_value else "disabled",
    )

    await _render_settings(callback, db)
    await callback.answer(status_msg)

    if new_value:
        await send_monitoring_summary(callback.bot, db, user_id)


@router.message(Command("monitoring"))
async def toggle_monitoring_cmd(
    message: Message, db: Database, monitor_client: TelegramMonitorClient
):
    """Переключает состояние мониторинга через команду."""
    if message.from_user.id not in Config.ALLOWED_USERS:
        await message.answer("❌ У вас нет доступа к этому боту.")
        return

    user_id = message.from_user.id
    settings = await db.get_user_settings(user_id)
    new_value = not settings.monitoring_enabled
    await db.set_monitoring_enabled(user_id, new_value)
    if monitor_client:
        await monitor_client.set_monitoring_enabled(user_id, new_value)

    if new_value:
        await send_monitoring_summary(message.bot, db, user_id)
    else:
        await message.answer("❌ Мониторинг выключен")
