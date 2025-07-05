# -*- coding: utf-8 -*-
import logging
import re
from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext

from database.db import Database
from database.models import Channel, TargetChat
from monitor.client import TelegramMonitorClient
from config.config import Config
from admin_bot.keyboards.keyboards import AdminKeyboards
from admin_bot.utils.states import ChannelStates, TargetChatStates
from admin_bot.utils import send_menu_message

logger = logging.getLogger(__name__)

router = Router()


@router.message(F.text == "📢 Управление каналами")
async def channels_menu(message: Message, state: FSMContext):
    """Меню управления каналами"""
    await state.clear()

    if message.from_user.id not in Config.ALLOWED_USERS:
        return

    await send_menu_message(
        message,
        "📢 <b>Управление каналами</b>\n\nВыберите действие:",
        reply_markup=AdminKeyboards.channels_menu(),
    )


@router.callback_query(F.data == "channel_add")
async def start_add_channel(callback: CallbackQuery, state: FSMContext):
    """Начало добавления канала"""
    await state.set_state(ChannelStates.waiting_channel)

    await callback.message.edit_text(
        "📢 <b>Добавление канала</b>\n\n"
        "Введите username канала или группы (с @ или без):\n\n"
        "Примеры:\n"
        "• <code>@news_channel</code>\n"
        "• <code>news_channel</code>\n"
        "• <code>https://t.me/news_channel</code>\n\n"
        "ℹ️ Убедитесь, что ваш аккаунт подписан на канал!",
        reply_markup=AdminKeyboards.cancel(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(ChannelStates.waiting_channel)
async def process_add_channel(
    message: Message,
    state: FSMContext,
    db: Database,
    monitor_client: TelegramMonitorClient,
):
    """Обработка добавления канала"""
    channel_input = message.text.strip()

    # Очищаем ввод
    # Support t.me/c/<id> links for private channels
    tme_c_match = re.search(r"(?:https?://)?t\.me/c/(\d+)", channel_input)
    if tme_c_match:
        channel_username = tme_c_match.group(1)
    elif channel_input.startswith("https://t.me/"):
        channel_username = channel_input.replace("https://t.me/", "")
    elif channel_input.startswith("@"):
        channel_username = channel_input[1:]
    else:
        channel_username = channel_input

    if not channel_username:
        await message.answer("❌ Некорректный формат. Попробуйте еще раз.")
        return

    # Получаем информацию о канале через клиент мониторинга
    channel_info = None
    if monitor_client:
        channel_info = await monitor_client.resolve_channel(channel_username)

    if channel_info:
        user_id = message.from_user.id
        # Создаем объект канала
        channel_obj = Channel(
            user_id=user_id,
            channel_id=channel_info["id"],
            channel_username=channel_info["username"],
            channel_title=channel_info["title"],
            enabled=True,
        )

        # Сохраняем в базу
        success = await db.add_channel(channel_obj)

        if success:
            await message.answer(
                f"✅ <b>Канал добавлен!</b>\n\n"
                f"📢 <b>Название:</b> {channel_info['title']}\n"
                f"🆔 <b>ID:</b> {channel_info['id']}\n"
                f"👤 <b>Username:</b> @{channel_info['username']}\n\n"
                f"Мониторинг активирован!",
                reply_markup=AdminKeyboards.channels_menu(),
                parse_mode="HTML",
            )

            if monitor_client:
                await monitor_client.add_channel_to_monitor(user_id, channel_info["id"])

            # Send monitoring summary
            from admin_bot.utils import send_monitoring_summary
            await send_monitoring_summary(message.bot, db, user_id)

        else:
            await message.answer(
                "❌ <b>Ошибка добавления</b>\n\n"
                "Канал уже добавлен или произошла ошибка.",
                reply_markup=AdminKeyboards.channels_menu(),
                parse_mode="HTML",
            )
    else:
        await message.answer(
            "❌ <b>Канал не найден</b>\n\n"
            "Проверьте:\n"
            "• Правильность username\n"
            "• Что вы подписаны на канал\n"
            "• Что канал публичный или вы в нем состоите",
            reply_markup=AdminKeyboards.channels_menu(),
            parse_mode="HTML",
        )

    await state.clear()


@router.callback_query(F.data == "channel_list")
async def show_channels_list(callback: CallbackQuery, db: Database):
    """Показать список каналов"""
    user_id = callback.from_user.id
    channels = await db.get_user_channels(user_id, enabled_only=False)

    if not channels:
        await callback.message.edit_text(
            "📢 <b>Список каналов</b>\n\n"
            "У вас пока нет отслеживаемых каналов.\n"
            "Добавьте первый канал, нажав 'Добавить канал'.",
            reply_markup=AdminKeyboards.channels_menu(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    # Формируем список
    text_lines = ["📢 <b>Отслеживаемые каналы:</b>\n"]

    for i, channel in enumerate(channels, 1):
        status = "✅" if channel.enabled else "❌"
        text_lines.append(
            f"{i}. {status} <b>{channel.channel_title}</b>\n"
            f"   👤 @{channel.channel_username}\n"
            f"   🆔 ID: {channel.channel_id}\n"
        )

    # Создаем inline клавиатуру
    keyboard = []
    for channel in channels[:10]:  # Показываем только первые 10
        status = "✅" if channel.enabled else "❌"
        title = channel.channel_title[:25]
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"{status} {title}",
                    callback_data=f"channel_show_{channel.id}",
                )
            ]
        )

    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")])

    await callback.message.edit_text(
        "\n".join(text_lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("target_confirm_"))
async def confirm_target_chat(callback: CallbackQuery, db: Database):
    """Подтверждение добавления целевого чата"""
    try:
        _, _, user_id_str, chat_id_str = callback.data.split("_", 3)
        user_id = int(user_id_str)
        chat_id = int(chat_id_str)
    except Exception:
        await callback.answer("Некорректные данные", show_alert=True)
        return

    chat = callback.message.chat
    chat_title = chat.title or getattr(chat, "username", "") or "Приватный чат"

    success = await db.add_target_chat(
        TargetChat(
            user_id=user_id,
            chat_id=chat_id,
            chat_title=chat_title,
            enabled=True,
        )
    )

    if success:
        await callback.message.edit_text("✅ Чат подтверждён")
        try:
            text = (
                f"✅ Чат '{chat_title}' успешно добавлен в качестве целевого"
            )
            if len(text) > 4096:
                text = text[:4096]
            await callback.bot.send_message(
                user_id,
                text,
                reply_markup=AdminKeyboards.target_chats_menu(),
            )
            from admin_bot.utils import send_monitoring_summary
            await send_monitoring_summary(callback.bot, db, user_id)
        except Exception:
            pass
    else:
        await callback.message.edit_text("❌ Не удалось добавить чат")
    await callback.answer()


@router.callback_query(F.data.startswith("target_delete_"))
async def delete_target_chat_cb(
    callback: CallbackQuery,
    db: Database,
    monitor_client: TelegramMonitorClient,
):
    chat_id = int(callback.data.replace("target_delete_", ""))
    user_id = callback.from_user.id
    success = await db.delete_target_chat(chat_id, user_id)
    if success:
        if monitor_client:
            pass  # nothing to do for now
        await callback.message.edit_text(
            "✅ Чат удален", reply_markup=AdminKeyboards.target_chats_menu()
        )
    else:
        await callback.message.edit_text(
            "❌ Ошибка удаления", reply_markup=AdminKeyboards.target_chats_menu()
        )
    await callback.answer()


@router.callback_query(F.data.startswith("channel_show_"))
async def show_channel_details(callback: CallbackQuery, db: Database):
    channel_id = int(callback.data.replace("channel_show_", ""))
    user_id = callback.from_user.id
    channels = await db.get_user_channels(user_id, enabled_only=False)
    channel = next((c for c in channels if c.id == channel_id), None)
    if not channel:
        await callback.answer("❌ Канал не найден", show_alert=True)
        return
    text = (
        f"📢 <b>{channel.channel_title}</b>\n"
        f"🆔 <code>{channel.channel_id}</code>\n"
        f"👤 @{channel.channel_username}\n"
        f"Статус: {'✅ Включен' if channel.enabled else '❌ Выключен'}"
    )
    await callback.message.edit_text(
        text,
        reply_markup=AdminKeyboards.channel_actions(channel.id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("channel_toggle_"))
async def toggle_channel(
    callback: CallbackQuery,
    db: Database,
    monitor_client: TelegramMonitorClient,
):
    channel_id = int(callback.data.replace("channel_toggle_", ""))
    user_id = callback.from_user.id
    channels = await db.get_user_channels(user_id, enabled_only=False)
    channel = next((c for c in channels if c.id == channel_id), None)
    if not channel:
        await callback.answer("❌ Канал не найден", show_alert=True)
        return
    new_status = not channel.enabled
    success = await db.update_channel(channel_id, enabled=new_status)
    if success:
        if monitor_client:
            if new_status:
                await monitor_client.add_channel_to_monitor(user_id, channel.channel_id)
            else:
                await monitor_client.remove_channel_from_monitor(
                    user_id, channel.channel_id
                )

        if new_status:
            from admin_bot.utils import send_monitoring_summary
            await send_monitoring_summary(callback.bot, db, user_id)

        await show_channel_details(callback, db)
    else:
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("channel_delete_"))
async def confirm_delete_channel(callback: CallbackQuery):
    channel_id = int(callback.data.replace("channel_delete_", ""))
    await callback.message.edit_text(
        "❓ <b>Удаление канала</b>\n\nВы уверены?",
        reply_markup=AdminKeyboards.confirmation("delete_channel", channel_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_channel_"))
async def delete_channel(
    callback: CallbackQuery,
    db: Database,
    monitor_client: TelegramMonitorClient,
):
    channel_id = int(callback.data.replace("confirm_delete_channel_", ""))
    user_id = callback.from_user.id
    channels = await db.get_user_channels(user_id, enabled_only=False)
    channel = next((c for c in channels if c.id == channel_id), None)
    success = await db.delete_channel(channel_id, user_id)
    if success:
        if monitor_client and channel:
            await monitor_client.remove_channel_from_monitor(
                user_id, channel.channel_id
            )
        await callback.message.edit_text(
            "✅ Канал удален",
            reply_markup=AdminKeyboards.channels_menu(),
        )
    else:
        await callback.message.edit_text(
            "❌ Ошибка удаления",
            reply_markup=AdminKeyboards.channels_menu(),
        )
    await callback.answer()


# Целевые чаты
@router.message(F.text == "🎯 Целевые чаты")
async def target_chats_menu(message: Message, state: FSMContext):
    """Меню управления целевыми чатами"""
    await state.clear()

    if message.from_user.id not in Config.ALLOWED_USERS:
        return
    text = (
        "🎯 <b>Управление целевыми чатами</b>\n\n"
        "Целевые чаты - это чаты, куда будут отправляться найденные сообщения.\n\n"
        "Выберите действие:"
    )
    await send_menu_message(
        message,
        text,
        reply_markup=AdminKeyboards.target_chats_menu(),
    )


@router.callback_query(F.data == "target_add")
async def start_add_target_chat(callback: CallbackQuery, state: FSMContext):
    """Начало добавления целевого чата"""
    await state.set_state(TargetChatStates.waiting_chat_id)

    await callback.message.edit_text(
        "🎯 <b>Добавление целевого чата</b>\n\n"
        "Введите ID чата или перешлите любое сообщение из целевого чата:\n\n"
        "ℹ️ <b>Как узнать ID чата:</b>\n"
        "1. Добавьте @userinfobot в чат\n"
        "2. Он покажет ID чата\n"
        "3. Или просто перешлите сообщение из чата\n\n"
        "⚠️ Убедитесь, что бот добавлен в целевой чат и имеет права "
        "на отправку сообщений!",
        reply_markup=AdminKeyboards.cancel(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(TargetChatStates.waiting_chat_id)
async def process_add_target_chat(
    message: Message,
    state: FSMContext,
    db: Database,
    monitor_client: TelegramMonitorClient,
):
    """Обработка добавления целевого чата"""
    chat_id = None
    chat_title = ""

    bot = message.bot

    if message.forward_from_chat:
        chat_id = message.forward_from_chat.id
    elif message.text and (
        message.text.lstrip("-").isdigit() or message.text.startswith("@")
    ):
        try:
            if message.text.lstrip("-").isdigit():
                chat_id = int(message.text)
            else:
                chat_id = message.text
        except ValueError:
            await message.answer(
                "❌ Некорректный ID чата. Введите число или перешлите сообщение."
            )
            return
    else:
        await message.answer(
            "❌ Некорректный ввод. Введите ID чата или перешлите сообщение."
        )
        return

    try:
        chat = await bot.get_chat(chat_id)
        chat_id = chat.id
        chat_title = chat.title or getattr(chat, "username", "") or "Приватный чат"
    except Exception:
        await message.answer(
            "❌ Чат не найден или бот не имеет доступа. "
            "Убедитесь, что бот добавлен в чат."
        )
        return

    try:
        await bot.send_message(
            chat_id,
            (
                "ℹ️ Этот чат запрошен для получения уведомлений. "
                "Нажмите кнопку ниже, чтобы подтвердить."
            ),
            reply_markup=AdminKeyboards.confirm_chat(message.from_user.id, chat_id),
        )
    except Exception:
        await message.answer(
            "❌ Не удалось отправить сообщение в указанный чат. Проверьте права бота."
        )
        return

    await message.answer(
        f"📨 Запрос на добавление чата <b>{chat_title}</b> отправлен. "
        "Нажмите ‘Подтвердить чат’ в самом чате.",
        reply_markup=AdminKeyboards.target_chats_menu(),
        parse_mode="HTML",
    )

    await state.clear()


@router.callback_query(F.data == "target_list")
async def show_target_chats_list(callback: CallbackQuery, db: Database):
    """Показать список целевых чатов"""
    user_id = callback.from_user.id
    chats = await db.get_user_target_chats(user_id)

    if not chats:
        await callback.message.edit_text(
            "🎯 <b>Список целевых чатов</b>\n\n"
            "У вас пока нет целевых чатов.\n"
            "Добавьте первый чат, нажав 'Добавить чат'.",
            reply_markup=AdminKeyboards.target_chats_menu(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    # Формируем список
    text_lines = ["🎯 <b>Целевые чаты:</b>\n"]

    for i, chat in enumerate(chats, 1):
        status = "✅" if chat.enabled else "❌"
        text_lines.append(
            f"{i}. {status} <b>{chat.chat_title}</b>\n" f"   🆔 ID: {chat.chat_id}\n"
        )

    text_lines.append("\n💡 Сюда будут отправляться найденные сообщения.")

    keyboard = []
    for chat in chats:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=chat.chat_title[:25], callback_data=f"target_delete_{chat.id}"
                )
            ]
        )
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")])

    await callback.message.edit_text(
        "\n".join(text_lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML",
    )
    await callback.answer()
