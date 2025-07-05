# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Основная конфигурация приложения"""

    # Telegram User API (для подключения к аккаунту)
    TELEGRAM_API_ID: int = int(os.getenv("TELEGRAM_API_ID", "0"))
    TELEGRAM_API_HASH: str = os.getenv("TELEGRAM_API_HASH", "")
    TELEGRAM_SESSION_NAME: str = os.getenv("TELEGRAM_SESSION_NAME", "telegram_monitor")

    # Telegram Bot API (для админки)
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

    # База данных
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "telegram_monitor.db")

    # Настройки безопасности
    ADMIN_USER_ID: int = int(os.getenv("ADMIN_USER_ID", "0"))
    ALLOWED_USERS: list = []  # Заполняется из базы данных

    # Настройки мониторинга
    MAX_MONITORED_CHANNELS: int = int(os.getenv("MAX_MONITORED_CHANNELS", "50"))
    MAX_FILTERS_PER_USER: int = int(os.getenv("MAX_FILTERS_PER_USER", "100"))
    MESSAGE_BATCH_SIZE: int = int(os.getenv("MESSAGE_BATCH_SIZE", "10"))

    # Настройки уведомлений
    NOTIFICATION_FORMAT: str = os.getenv("NOTIFICATION_FORMAT", "full")
    INCLUDE_TIMESTAMP: bool = os.getenv("INCLUDE_TIMESTAMP", "true").lower() == "true"
    INCLUDE_CHANNEL_INFO: bool = (
        os.getenv("INCLUDE_CHANNEL_INFO", "true").lower() == "true"
    )

    # Настройки автоматического восстановления
    SESSION_BACKUP_INTERVAL = 300  # 5 минут
    SESSION_CHECK_INTERVAL = 300   # 5 минут
    MAX_RESTART_ATTEMPTS = 5       # Максимум попыток перезапуска
    RESTART_DELAY = 30             # Задержка между перезапусками (секунды)

    @classmethod
    def validate(cls) -> bool:
        """Проверяет корректность основных настроек"""
        if not cls.TELEGRAM_API_ID or not cls.TELEGRAM_API_HASH:
            raise ValueError("TELEGRAM_API_ID и TELEGRAM_API_HASH обязательны")
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN обязателен")
        if not cls.ADMIN_USER_ID:
            raise ValueError("ADMIN_USER_ID обязателен")
        return True


# Логгинг настройки
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
    },
    "handlers": {
        "default": {
            "level": "INFO",
            "formatter": "standard",
            "class": "logging.StreamHandler",
        },
        "file": {
            "level": "DEBUG",
            "formatter": "standard",
            "class": "logging.FileHandler",
            "filename": "telegram_monitor.log",
        },
    },
    "loggers": {
        "": {"handlers": ["default", "file"], "level": "DEBUG", "propagate": False}
    },
}
