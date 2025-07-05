#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Channel Monitor - Система мониторинга каналов
Интегрирует User API (Telethon) и Bot API (Aiogram) для мониторинга сообщений в каналах
"""

import asyncio
import logging
import logging.config
import signal
import sys
import os
from typing import Optional

from config.config import Config, LOGGING_CONFIG
from database.db import Database
from monitor.client import TelegramMonitorClient
from admin_bot.bot import AdminBot

# Настройка логирования
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)


class TelegramMonitorApp:
    """Главный класс приложения"""

    def __init__(self):
        self.db: Optional[Database] = None
        self.monitor_client: Optional[TelegramMonitorClient] = None
        self.admin_bot: Optional[AdminBot] = None
        self.running = False

    async def initialize(self):
        """Инициализация компонентов"""
        try:
            logger.info("🚀 Запуск Telegram Monitor...")

            # Проверяем конфигурацию
            Config.validate()
            logger.info("✅ Конфигурация проверена")

            # Инициализируем базу данных
            self.db = Database(Config.DATABASE_PATH)
            await self.db.init_db()
            logger.info("✅ База данных инициализирована")

            # Добавляем администратора в список разрешённых пользователей
            await self.db.add_allowed_user(Config.ADMIN_USER_ID)

            # Загружаем список разрешённых пользователей
            Config.ALLOWED_USERS = await self.db.get_allowed_users()

            # Создаем настройки для всех разрешённых пользователей
            for uid in Config.ALLOWED_USERS:
                await self.db.create_user_settings(uid)

            # Инициализируем клиент мониторинга
            self.monitor_client = TelegramMonitorClient(self.db)
            logger.info("✅ Клиент мониторинга создан")

            # Инициализируем админ-бота
            self.admin_bot = AdminBot(self.db, self.monitor_client)
            logger.info("✅ Админ-бот создан")

            logger.info("🎉 Все компоненты инициализированы")

        except Exception as e:
            logger.error(f"❌ Ошибка инициализации: {e}")
            raise

    async def start(self):
        """Запуск всех компонентов"""
        try:
            self.running = True

            # Запускаем клиент мониторинга
            logger.info("🔍 Запуск клиента мониторинга...")
            monitor_task = asyncio.create_task(self.monitor_client.start())

            # Даем время на подключение клиента
            await asyncio.sleep(2)

            # Запускаем админ-бота
            logger.info("🤖 Запуск админ-бота...")
            admin_task = asyncio.create_task(self.admin_bot.start())

            # Передаем экземпляр бота клиенту мониторинга
            await asyncio.sleep(0)
            self.monitor_client.bot = self.admin_bot.bot

            logger.info("✅ Все компоненты запущены")
            logger.info("📊 Система мониторинга активна!")
            logger.info(f"👤 Админ ID: {Config.ADMIN_USER_ID}")
            bot_username = f"{Config.BOT_TOKEN.split(':')[0]}bot"
            logger.info(f"📱 Используйте бота @{bot_username} для управления")

            # Ждем завершения задач
            await asyncio.gather(monitor_task, admin_task, return_exceptions=True)

        except Exception as e:
            logger.error(f"❌ Ошибка запуска: {e}")
            await self.stop()
            raise

    async def stop(self):
        """Остановка всех компонентов"""
        if self.running:
            logger.info("🛑 Остановка системы...")
            self.running = False
        else:
            logger.info("🛑 Выполняется завершение компонентов...")

        # Останавливаем компоненты
        if self.monitor_client:
            await self.monitor_client.stop()
            logger.info("✅ Клиент мониторинга остановлен")

        if self.admin_bot:
            await self.admin_bot.stop()
            logger.info("✅ Админ-бот остановлен")

        logger.info("👋 Система остановлена")

    def setup_signal_handlers(self):
        """Настройка обработчиков сигналов"""

        def signal_handler(signum, frame):
            logger.info(f"🔔 Получен сигнал {signum}")
            loop = asyncio.get_event_loop()
            loop.create_task(self.stop())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


async def health_check():
    """Отправка heartbeat сообщений раз в сутки"""
    while True:
        try:
            await asyncio.sleep(86400)  # 24 часа
            logger.info("✅ Бот активен")
            if bot and hasattr(bot, 'send_message'):
                await bot.send_message(
                    Config.ADMIN_USER_ID, 
                    "❤️ Бот работает стабильно"
                )
        except Exception as e:
            logger.error(f"Ошибка health check: {e}")


async def main():
    """Главная функция"""
    app = TelegramMonitorApp()
    restart_count = 0
    max_restarts = 5

    while restart_count < max_restarts:
        try:
            # Настраиваем обработчики сигналов
            app.setup_signal_handlers()

            # Инициализируем
            await app.initialize()

            # Запускаем health_check внутри асинхронного контекста
            asyncio.create_task(health_check())

            # Запускаем
            await app.start()

        except KeyboardInterrupt:
            logger.info("Запуск Telegram Monitor Bot...")
            break
        except Exception as e:
            restart_count += 1
            logger.error(f"Критическая ошибка (попытка {restart_count}/{max_restarts}): {e}")
            
            if restart_count >= max_restarts:
                logger.critical("Достигнут лимит перезапусков. Завершение работы.")
                sys.exit(1)
            
            logger.info(f"Перезапуск через 30 секунд...")
            await asyncio.sleep(30)
        finally:
            await app.stop()


if __name__ == "__main__":
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/bot.log'),
            logging.StreamHandler()
        ]
    )
    
    # Создаем папку для логов если её нет
    os.makedirs('logs', exist_ok=True)
    
    logger = logging.getLogger(__name__)
    logger.info("Запуск Telegram Monitor Bot...")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nДо свидания!")
