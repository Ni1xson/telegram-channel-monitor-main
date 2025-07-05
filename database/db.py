# -*- coding: utf-8 -*-
import aiosqlite
import json
import logging
from typing import List, Optional
from datetime import datetime

from .models import (
    Filter,
    Channel,
    TargetChat,
    FoundMessage,
    UserSettings,
    DatabaseManager,
)

logger = logging.getLogger(__name__)

USER_SETTINGS_FIELDS = {
    "notification_format",
    "include_timestamp",
    "include_channel_info",
    "include_message_link",
    "include_sender_id",
    "include_original_formatting",
    "forward_as_code",
    "monitoring_enabled",
    "max_message_length",
}


class Database(DatabaseManager):
    """Основной класс для работы с базой данных"""

    def __init__(self, db_path: str):
        super().__init__(db_path)

    async def create_user_settings(self, user_id: int) -> bool:
        """Создает настройки пользователя по умолчанию"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT OR IGNORE INTO user_settings (user_id) VALUES (?)
                """,
                    (user_id,),
                )
                await db.commit()
                return True
        except Exception as e:
            logger.exception("Ошибка создания настроек пользователя: %s", e)
            return False

    # Методы для работы с разрешёнными пользователями
    async def add_allowed_user(self, user_id: int) -> bool:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "INSERT OR IGNORE INTO allowed_users (user_id) VALUES (?)",
                    (user_id,),
                )
                await db.commit()
                return True
        except Exception as e:
            print(f"Ошибка добавления пользователя: {e}")
            return False

    async def remove_allowed_user(self, user_id: int) -> bool:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "DELETE FROM allowed_users WHERE user_id = ?", (user_id,)
                )
                await db.commit()
                return True
        except Exception as e:
            print(f"Ошибка удаления пользователя: {e}")
            return False

    async def get_allowed_users(self) -> List[int]:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT user_id FROM allowed_users") as cursor:
                    rows = await cursor.fetchall()
            return [row[0] for row in rows]
        except Exception as e:
            print(f"Ошибка получения списка пользователей: {e}")
            return []

    # Методы для работы с фильтрами
    async def add_filter(self, filter_obj: Filter) -> Optional[int]:
        """Добавляет новый фильтр"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    """
                    INSERT INTO filters (user_id, name, keywords, logic_type,
                                       case_sensitive, word_order_matters, enabled)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        filter_obj.user_id,
                        filter_obj.name,
                        json.dumps(filter_obj.keywords, ensure_ascii=False),
                        filter_obj.logic_type,
                        filter_obj.case_sensitive,
                        filter_obj.word_order_matters,
                        filter_obj.enabled,
                    ),
                )
                await db.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.exception("Ошибка добавления фильтра: %s", e)
            return None

    async def get_user_filters(
        self, user_id: int, enabled_only: bool = True
    ) -> List[Filter]:
        """Получает общий список фильтров для всех пользователей"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                query = """
                    SELECT id, user_id, name, keywords, logic_type,
                           case_sensitive, word_order_matters, enabled, created_at
                    FROM filters
                """
                params = []

                if enabled_only:
                    query += " WHERE enabled = TRUE"

                query += " ORDER BY created_at DESC"

                async with db.execute(query, params) as cursor:
                    rows = await cursor.fetchall()

                filters = []
                for row in rows:
                    filter_obj = Filter(
                        id=row[0],
                        user_id=row[1],
                        name=row[2],
                        keywords=json.loads(row[3]),
                        logic_type=row[4],
                        case_sensitive=bool(row[5]),
                        word_order_matters=bool(row[6]),
                        enabled=bool(row[7]),
                        created_at=datetime.fromisoformat(row[8]) if row[8] else None,
                    )
                    filters.append(filter_obj)

                return filters
        except Exception as e:
            logger.exception("Ошибка получения фильтров: %s", e)
            return []

    async def update_filter(self, filter_id: int, **kwargs) -> bool:
        """Обновляет фильтр"""
        try:
            if not kwargs:
                return False

            set_clauses = []
            params = []

            for key, value in kwargs.items():
                if key == "keywords":
                    set_clauses.append(f"{key} = ?")
                    params.append(json.dumps(value, ensure_ascii=False))
                else:
                    set_clauses.append(f"{key} = ?")
                    params.append(value)

            params.append(filter_id)

            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    f"""
                    UPDATE filters SET {', '.join(set_clauses)} WHERE id = ?
                """,
                    params,
                )
                await db.commit()
                return True
        except Exception as e:
            logger.exception("Ошибка обновления фильтра: %s", e)
            return False

    async def delete_filter(self, filter_id: int, user_id: int) -> bool:
        """Удаляет фильтр"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    DELETE FROM filters WHERE id = ? AND user_id = ?
                """,
                    (filter_id, user_id),
                )
                await db.commit()
                return True
        except Exception as e:
            logger.exception("Ошибка удаления фильтра: %s", e)
            return False

    # Методы для работы с каналами
    async def add_channel(self, channel_obj: Channel) -> bool:
        """Добавляет канал для мониторинга"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT OR REPLACE INTO channels
                    (user_id, channel_id, channel_username, channel_title, enabled)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        channel_obj.user_id,
                        channel_obj.channel_id,
                        channel_obj.channel_username,
                        channel_obj.channel_title,
                        channel_obj.enabled,
                    ),
                )
                await db.commit()
                return True
        except Exception as e:
            logger.exception("Ошибка добавления канала: %s", e)
            return False

    async def get_user_channels(
        self, user_id: int, enabled_only: bool = True
    ) -> List[Channel]:
        """Получает общий список каналов для всех пользователей"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                query = """
                    SELECT id, user_id, channel_id, channel_username,
                           channel_title, enabled, added_at
                    FROM channels
                """
                params = []

                if enabled_only:
                    query += " WHERE enabled = TRUE"

                query += " ORDER BY added_at DESC"

                async with db.execute(query, params) as cursor:
                    rows = await cursor.fetchall()

                channels = []
                for row in rows:
                    channel = Channel(
                        id=row[0],
                        user_id=row[1],
                        channel_id=row[2],
                        channel_username=row[3],
                        channel_title=row[4],
                        enabled=bool(row[5]),
                        added_at=datetime.fromisoformat(row[6]) if row[6] else None,
                    )
                    channels.append(channel)

                return channels
        except Exception as e:
            logger.exception("Ошибка получения каналов: %s", e)
            return []

    async def update_channel(self, channel_id: int, **kwargs) -> bool:
        """Обновляет канал"""
        if not kwargs:
            return False
        try:
            set_clauses = []
            params = []
            for key, value in kwargs.items():
                set_clauses.append(f"{key} = ?")
                params.append(value)
            params.append(channel_id)
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    f"UPDATE channels SET {', '.join(set_clauses)} WHERE id = ?", params
                )
                await db.commit()
                return True
        except Exception as e:
            logger.exception("Ошибка обновления канала: %s", e)
            return False

    # Методы для работы с целевыми чатами
    async def add_target_chat(self, chat_obj: TargetChat) -> bool:
        """Добавляет целевой чат"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT OR REPLACE INTO target_chats
                    (user_id, chat_id, chat_title, enabled)
                    VALUES (?, ?, ?, ?)
                """,
                    (
                        chat_obj.user_id,
                        chat_obj.chat_id,
                        chat_obj.chat_title,
                        chat_obj.enabled,
                    ),
                )
                await db.commit()
                return True
        except Exception as e:
            logger.exception("Ошибка добавления целевого чата: %s", e)
            return False

    async def get_user_target_chats(self, user_id: int) -> List[TargetChat]:
        """Получает список целевых чатов пользователя"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    """
                    SELECT id, user_id, chat_id, chat_title, enabled, added_at
                    FROM target_chats WHERE user_id = ? AND enabled = TRUE
                    ORDER BY added_at DESC
                """,
                    (user_id,),
                ) as cursor:
                    rows = await cursor.fetchall()

                chats = []
                for row in rows:
                    chat = TargetChat(
                        id=row[0],
                        user_id=row[1],
                        chat_id=row[2],
                        chat_title=row[3],
                        enabled=bool(row[4]),
                        added_at=datetime.fromisoformat(row[5]) if row[5] else None,
                    )
                    chats.append(chat)

                return chats
        except Exception as e:
            logger.exception("Ошибка получения целевых чатов: %s", e)
            return []

    async def delete_channel(self, channel_id: int, user_id: int) -> bool:
        """Удаляет канал"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "DELETE FROM channels WHERE id = ? AND user_id = ?",
                    (channel_id, user_id),
                )
                await db.commit()
                return True
        except Exception as e:
            logger.exception("Ошибка удаления канала: %s", e)
            return False

    async def delete_target_chat(self, chat_id: int, user_id: int) -> bool:
        """Удаляет целевой чат"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "DELETE FROM target_chats WHERE id = ? AND user_id = ?",
                    (chat_id, user_id),
                )
                await db.commit()
                return True
        except Exception as e:
            logger.exception("Ошибка удаления целевого чата: %s", e)
            return False

    async def update_user_settings(self, user_id: int, **kwargs) -> bool:
        """Обновляет настройки пользователя"""
        if not kwargs:
            return False

        # Оставляем только допустимые ключи
        valid_kwargs = {k: v for k, v in kwargs.items() if k in USER_SETTINGS_FIELDS}
        invalid_keys = set(kwargs) - USER_SETTINGS_FIELDS
        if invalid_keys:
            logger.warning("Игнорируем недопустимые поля настроек: %s", invalid_keys)

        if not valid_kwargs:
            return False

        try:
            set_clauses = []
            params = []
            for key, value in valid_kwargs.items():
                set_clauses.append(f"{key} = ?")
                params.append(value)
            params.append(user_id)
            async with aiosqlite.connect(self.db_path) as db:
                set_clause = ", ".join(set_clauses)
                update_sql = (
                    f"UPDATE user_settings SET {set_clause}, "
                    "updated_at = CURRENT_TIMESTAMP WHERE user_id = ?"
                )
                await db.execute(update_sql, params)
                await db.commit()
                return True
        except Exception as e:
            logger.exception("Ошибка обновления настроек: %s", e)
            return False

    async def is_monitoring_enabled(self, user_id: int) -> bool:
        """Возвращает состояние мониторинга пользователя"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT monitoring_enabled FROM user_settings WHERE user_id = ?",
                    (user_id,),
                ) as cursor:
                    row = await cursor.fetchone()
                    return bool(row[0]) if row else True
        except Exception as e:
            logger.exception("Ошибка получения статуса мониторинга: %s", e)
            return True

    async def set_monitoring_enabled(self, user_id: int, enabled: bool) -> bool:
        """Устанавливает состояние мониторинга пользователя"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    (
                        "UPDATE user_settings SET monitoring_enabled = ?, "
                        "updated_at = CURRENT_TIMESTAMP WHERE user_id = ?"
                    ),
                    (enabled, user_id),
                )
                await db.commit()
                return True
        except Exception as e:
            logger.exception("Ошибка обновления статуса мониторинга: %s", e)
            return False

    # Методы для работы с найденными сообщениями
    async def save_found_message(self, message_obj: FoundMessage) -> Optional[int]:
        """Сохраняет найденное сообщение"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    """
                    INSERT OR IGNORE INTO found_messages (
                        user_id,
                        filter_id,
                        channel_id,
                        message_id,
                        sender_id,
                        sender_username,
                        message_text,
                        matched_keywords
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        message_obj.user_id,
                        message_obj.filter_id,
                        message_obj.channel_id,
                        message_obj.message_id,
                        message_obj.sender_id,
                        message_obj.sender_username,
                        message_obj.message_text,
                        json.dumps(message_obj.matched_keywords, ensure_ascii=False),
                    ),
                )
                await db.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.exception("Ошибка сохранения найденного сообщения: %s", e)
            return None

    async def get_today_found_messages_count(self, user_id: int) -> int:
        """Возвращает количество найденных сообщений за сегодня"""
        try:
            start_of_day = datetime.utcnow().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    """
                    SELECT COUNT(*) FROM found_messages
                    WHERE user_id = ? AND found_at >= ?
                """,
                    (user_id, start_of_day.isoformat()),
                ) as cursor:
                    row = await cursor.fetchone()
                    return row[0] if row else 0
        except Exception as e:
            logger.exception("Ошибка получения количества найденных сообщений: %s", e)
            return 0

    async def get_user_settings(self, user_id: int) -> Optional[UserSettings]:
        """Получает настройки пользователя"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT * FROM user_settings WHERE user_id = ?",
                    (user_id,),
                ) as cursor:
                    row = await cursor.fetchone()

                if not row:
                    await self.create_user_settings(user_id)
                    return UserSettings(user_id=user_id)

                row_keys = row.keys()

                def get_value(key: str, default):
                    return row[key] if key in row_keys else default

                created_str = get_value("created_at", None)
                updated_str = get_value("updated_at", None)

                return UserSettings(
                    user_id=row["user_id"],
                    notification_format=get_value("notification_format", "full"),
                    include_timestamp=bool(get_value("include_timestamp", True)),
                    include_channel_info=bool(
                        get_value("include_channel_info", True)
                    ),
                    include_message_link=bool(
                        get_value("include_message_link", True)
                    ),
                    include_sender_id=bool(
                        get_value("include_sender_id", False)
                    ),
                    include_original_formatting=bool(
                        get_value("include_original_formatting", True)
                    ),
                    forward_as_code=bool(get_value("forward_as_code", False)),
                    monitoring_enabled=bool(
                        get_value("monitoring_enabled", True)
                    ),
                    max_message_length=get_value("max_message_length", 4000),
                    created_at=(
                        datetime.fromisoformat(created_str) if created_str else None
                    ),
                    updated_at=(
                        datetime.fromisoformat(updated_str) if updated_str else None
                    ),
                )
        except Exception as e:
            logger.exception("Ошибка получения настроек пользователя: %s", e)
            return None

    async def count_user_filters(self, enabled_only: bool = False) -> int:
        """Возвращает общее количество фильтров."""
        try:
            query = "SELECT COUNT(*) FROM filters"
            params = []
            if enabled_only:
                query += " WHERE enabled = TRUE"
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(query, params) as cursor:
                    row = await cursor.fetchone()
                    return row[0] if row else 0
        except Exception as e:
            logger.exception("Ошибка подсчёта фильтров: %s", e)
            return 0

    async def count_user_channels(self, enabled_only: bool = False) -> int:
        """Возвращает общее количество каналов."""
        try:
            query = "SELECT COUNT(*) FROM channels"
            params = []
            if enabled_only:
                query += " WHERE enabled = TRUE"
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(query, params) as cursor:
                    row = await cursor.fetchone()
                    return row[0] if row else 0
        except Exception as e:
            logger.exception("Ошибка подсчёта каналов: %s", e)
            return 0

    async def count_messages_today(self, user_id: int) -> int:
        """Возвращает количество найденных сообщений за сегодня."""
        try:
            query = (
                "SELECT COUNT(*) FROM found_messages "
                "WHERE user_id = ? AND DATE(found_at) = DATE('now')"
            )
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(query, (user_id,)) as cursor:
                    row = await cursor.fetchone()
                    return row[0] if row else 0
        except Exception as e:
            logger.exception("Ошибка подсчёта сообщений: %s", e)
            return 0
