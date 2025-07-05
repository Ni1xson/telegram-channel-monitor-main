from aiogram import Bot
from database.db import Database
from typing import List


LOGIC_NAMES = {
    "contains": "Содержит",
    "exact": "Точное совпадение",
    "all_words": "Все слова",
    "phrase": "Фраза",
    "regex": "Регулярное выражение",
    "not_contains": "Не содержит",
}


async def compose_monitoring_summary(db: Database, user_id: int) -> str:
    channels = await db.get_user_channels(user_id, enabled_only=True)
    chats = await db.get_user_target_chats(user_id)
    filters = await db.get_user_filters(user_id, enabled_only=True)

    lines: List[str] = ["✅ <b>Мониторинг включен!</b>", ""]

    if channels:
        lines.append("<b>Каналы:</b>")
        for ch in channels:
            username = (
                f"@{ch.channel_username}" if ch.channel_username else str(ch.channel_id)
            )
            lines.append(f"• {ch.channel_title} ({username})")
        lines.append("")

    if chats:
        lines.append("<b>Целевые чаты:</b>")
        for chat in chats:
            lines.append(f"• {chat.chat_title} (ID: {chat.chat_id})")
        lines.append("")

    if filters:
        lines.append("<b>Фильтры:</b>")
        for f in filters:
            logic = LOGIC_NAMES.get(f.logic_type, f.logic_type)
            lines.append(f"• {f.name} — {logic} ({len(f.keywords)})")
        first = filters[0]
        if first.keywords:
            example_kw = first.keywords[0]
            lines.append("")
            lines.append(
                f"Пример: ищем '<b>{example_kw}</b>' по фильтру '{first.name}'."
            )

    return "\n".join(lines)


async def send_monitoring_summary(bot: Bot, db: Database, user_id: int) -> None:
    text = await compose_monitoring_summary(db, user_id)
    try:
        await bot.send_message(user_id, text, parse_mode="HTML")
    except Exception:
        # Try without parse mode if HTML fails
        await bot.send_message(user_id, text)
