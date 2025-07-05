# -*- coding: utf-8 -*-
import aiosqlite
import logging
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class AllowedUser:
    """Разрешённый пользователь"""

    user_id: int
    added_at: Optional[datetime] = None


@dataclass
class Filter:
    """Модель фильтра сообщений"""

    id: Optional[int] = None
    user_id: int = 0
    name: str = ""
    keywords: List[str] = None
    logic_type: str = "contains"  # contains, exact, regex, not_contains
    case_sensitive: bool = False
    word_order_matters: bool = False
    enabled: bool = True
    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []


@dataclass
class Channel:
    """Модель отслеживаемого канала"""

    id: Optional[int] = None
    user_id: int = 0
    channel_id: int = 0
    channel_username: str = ""
    channel_title: str = ""
    enabled: bool = True
    added_at: Optional[datetime] = None


@dataclass
class TargetChat:
    """Модель целевого чата для уведомлений"""

    id: Optional[int] = None
    user_id: int = 0
    chat_id: int = 0
    chat_title: str = ""
    enabled: bool = True
    added_at: Optional[datetime] = None


@dataclass
class FoundMessage:
    """Модель найденного сообщения"""

    id: Optional[int] = None
    user_id: int = 0
    filter_id: int = 0
    channel_id: int = 0
    message_id: int = 0
    sender_id: int = 0
    sender_username: str = ""
    message_text: str = ""
    matched_keywords: List[str] = None
    found_at: Optional[datetime] = None
    forwarded: bool = False

    def __post_init__(self):
        if self.matched_keywords is None:
            self.matched_keywords = []


@dataclass
class UserSettings:
    """Модель пользовательских настроек"""

    user_id: int = 0
    notification_format: str = "full"  # full, compact, minimal
    include_timestamp: bool = True
    include_channel_info: bool = True
    include_message_link: bool = True
    include_sender_id: bool = False
    include_original_formatting: bool = True
    forward_as_code: bool = False
    monitoring_enabled: bool = True
    max_message_length: int = 4000
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DatabaseManager:
    """Менеджер базы данных"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    async def init_db(self):
        """Инициализация базы данных"""
        async with aiosqlite.connect(self.db_path) as db:
            # Таблица фильтров
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS filters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    keywords TEXT NOT NULL,  -- JSON массив
                    logic_type TEXT DEFAULT 'contains',
                    case_sensitive BOOLEAN DEFAULT FALSE,
                    word_order_matters BOOLEAN DEFAULT FALSE,
                    enabled BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Таблица отслеживаемых каналов
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    channel_username TEXT,
                    channel_title TEXT,
                    enabled BOOLEAN DEFAULT TRUE,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, channel_id)
                )
            """
            )

            # Таблица целевых чатов
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS target_chats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    chat_title TEXT,
                    enabled BOOLEAN DEFAULT TRUE,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, chat_id)
                )
            """
            )

            # Таблица разрешённых пользователей
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS allowed_users (
                    user_id INTEGER PRIMARY KEY,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Таблица найденных сообщений
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS found_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    filter_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    sender_id INTEGER,
                    sender_username TEXT,
                    message_text TEXT,
                    matched_keywords TEXT,  -- JSON массив
                    found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    forwarded BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (filter_id) REFERENCES filters (id),
                    UNIQUE(channel_id, message_id, filter_id)
                )
            """
            )

            # Миграция таблицы найденных сообщений
            try:
                async with db.execute("PRAGMA table_info(found_messages)") as c:
                    cols = [row[1] async for row in c]
                if "sender_id" not in cols:
                    try:
                        await db.execute(
                            "ALTER TABLE found_messages ADD COLUMN sender_id INTEGER"
                        )
                    except Exception as e:
                        logger.exception(
                            "Failed to add sender_id column: %s", e
                        )
                if "sender_username" not in cols:
                    try:
                        await db.execute(
                            "ALTER TABLE found_messages ADD COLUMN sender_username TEXT"
                        )
                    except Exception as e:
                        logger.exception(
                            "Failed to add sender_username column: %s", e
                        )
            except Exception as e:
                logger.exception("Failed to migrate found_messages table: %s", e)

            # Таблица пользовательских настроек
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id INTEGER PRIMARY KEY,
                    notification_format TEXT DEFAULT 'full',
                    include_timestamp BOOLEAN DEFAULT TRUE,
                    include_channel_info BOOLEAN DEFAULT TRUE,
                    include_message_link BOOLEAN DEFAULT TRUE,
                    include_sender_id BOOLEAN DEFAULT FALSE,
                    include_original_formatting BOOLEAN DEFAULT TRUE,
                    forward_as_code BOOLEAN DEFAULT FALSE,
                    monitoring_enabled BOOLEAN DEFAULT TRUE,
                    max_message_length INTEGER DEFAULT 4000,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Обновляем схему для старых версий базы
            try:
                async with db.execute("PRAGMA table_info(user_settings)") as c:
                    cols = [row[1] async for row in c]

                if "monitoring_enabled" not in cols:
                    try:
                        await db.execute(
                            "ALTER TABLE user_settings ADD COLUMN monitoring_enabled "
                            "BOOLEAN DEFAULT 1"
                        )
                        await db.execute(
                            "UPDATE user_settings SET monitoring_enabled = 1 "
                            "WHERE monitoring_enabled IS NULL"
                        )
                    except Exception as e:
                        logger.exception(
                            "Failed to add monitoring_enabled column: %s", e
                        )

                if "updated_at" not in cols:
                    try:
                        await db.execute(
                            "ALTER TABLE user_settings ADD COLUMN updated_at "
                            "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
                        )
                    except Exception as e:
                        logger.exception(
                            "Failed to add updated_at column: %s", e
                        )

                if "include_sender_id" not in cols:
                    try:
                        await db.execute(
                            "ALTER TABLE user_settings ADD COLUMN include_sender_id BOOLEAN DEFAULT 0"
                        )
                        await db.execute(
                            "UPDATE user_settings SET include_sender_id = 0 WHERE include_sender_id IS NULL"
                        )
                    except Exception as e:
                        logger.exception(
                            "Failed to add include_sender_id column: %s", e
                        )
            except Exception as e:
                logger.exception("Failed to migrate user_settings table: %s", e)

            # Индексы для оптимизации
            await db.execute(
                (
                    "CREATE INDEX IF NOT EXISTS idx_filters_user_enabled "
                    "ON filters(user_id, enabled)"
                )
            )
            await db.execute(
                (
                    "CREATE INDEX IF NOT EXISTS idx_channels_user_enabled "
                    "ON channels(user_id, enabled)"
                )
            )
            await db.execute(
                (
                    "CREATE INDEX IF NOT EXISTS idx_found_messages_user "
                    "ON found_messages(user_id)"
                )
            )

            await db.commit()
