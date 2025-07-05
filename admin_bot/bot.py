# -*- coding: utf-8 -*-
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config.config import Config
from database.db import Database
from admin_bot.handlers import start, filters, channels, auth
from admin_bot.handlers import ping_backup_router
from admin_bot.middlewares.dependencies import DependencyMiddleware
from monitor.client import TelegramMonitorClient

logger = logging.getLogger(__name__)


class AdminBot:
    """Админ-бот для управления системой"""

    def __init__(self, db: Database, monitor_client: TelegramMonitorClient):
        self.db = db
        self.monitor_client = monitor_client
        self.bot = None
        self.dp = None

    async def start(self):
        """Запуск админ-бота"""
        try:
            # Создаем бота
            self.bot = Bot(
                token=Config.BOT_TOKEN,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML),
            )

            # Создаем диспетчер
            self.dp = Dispatcher()

            # Middleware для передачи зависимостей
            dep_middleware = DependencyMiddleware(self.db, self.monitor_client)
            self.dp.callback_query.middleware(dep_middleware)
            self.dp.message.middleware(dep_middleware)

            # Регистрируем роутеры
            self.dp.include_router(start.router)
            self.dp.include_router(filters.router)
            self.dp.include_router(channels.router)
            self.dp.include_router(auth.router)
            self.dp.include_router(ping_backup_router)

            logger.info("Админ-бот запущен")

            # Запускаем поллинг
            await self.dp.start_polling(self.bot)

        except Exception as e:
            logger.error(f"Ошибка запуска админ-бота: {e}")
            raise

    async def stop(self):
        """Остановка админ-бота"""
        if self.dp:
            await self.dp.stop_polling()
            await self.dp.emit_shutdown()
            if self.dp.storage:
                await self.dp.storage.close()

        if self.bot:
            await self.bot.session.close()

        logger.info("Админ-бот остановлен")
