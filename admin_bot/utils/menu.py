import logging
from aiogram.types import Message

LAST_MENU_MESSAGE = {}


async def send_menu_message(message: Message, text: str, reply_markup=None):
    """Send menu message deleting previous one and user command."""
    chat_id = message.chat.id
    bot = message.bot

    is_start_cmd = False
    if message.text:
        text_stripped = message.text.strip().lower()
        is_start_cmd = text_stripped.startswith("/start")

    prev = LAST_MENU_MESSAGE.get(chat_id)
    if prev and not is_start_cmd:
        try:
            await bot.delete_message(chat_id, prev)
        except Exception:
            pass

    if not is_start_cmd:
        try:
            await message.delete()
        except Exception:
            pass
    try:
        sent = await bot.send_message(
            chat_id, text, reply_markup=reply_markup, parse_mode="HTML"
        )
    except Exception:
        logging.exception("Failed to send menu message with HTML parse mode")
        try:
            sent = await bot.send_message(
                chat_id, text, reply_markup=reply_markup, parse_mode=None
            )
        except Exception:
            logging.exception("Failed to send menu message without parse mode")
            sent = None

    if sent:
        LAST_MENU_MESSAGE[chat_id] = sent.message_id

    return sent
