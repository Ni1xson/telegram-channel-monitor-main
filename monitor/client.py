# -*- coding: utf-8 -*-
import asyncio
import logging
import re
import contextlib
import os
import shutil
import time
from typing import Dict, Optional, Set, Union

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from utils import escape_html, escape_markdown
from telethon import TelegramClient, events
from telethon.tl.types import Channel, Chat, PeerChannel, PeerChat
from telethon.utils import get_peer_id

from config.config import Config
from database.db import Database
from database.models import FoundMessage
from utils import escape_html, escape_markdown
from .filters import MessageFilterManager

logger = logging.getLogger(__name__)


class TelegramMonitorClient:
    """Клиент для мониторинга каналов через User API"""

    def __init__(self, db: Database, bot: Optional[Bot] = None):
        self.db = db
        self.client = None
        self.bot = bot
        self.filter_manager = MessageFilterManager()
        self.monitored_channels: Dict[int, Set[int]] = (
            {}
        )  # user_id -> set of channel_ids
        self.user_monitoring: Dict[int, bool] = {}
        self.running = False
        self.ensure_task: Optional[asyncio.Task] = None
        self._backup_task: Optional[asyncio.Task] = None
        self.session_name = Config.TELEGRAM_SESSION_NAME
        self.logger = logging.getLogger(__name__)
        
        # Запускаем мониторинг сессии
        asyncio.create_task(self._session_watchdog())

    async def start(self):
        """Запускает клиент"""
        try:
            # Создаем клиент Telethon
            self.client = TelegramClient(
                Config.TELEGRAM_SESSION_NAME,
                Config.TELEGRAM_API_ID,
                Config.TELEGRAM_API_HASH,
            )

            # Подключаемся к аккаунту пользователя
            await self.client.start()
            logger.info("Telegram клиент успешно запущен")

            # Запускаем фоновую задачу резервного копирования
            self._backup_task = asyncio.create_task(self._session_backup_loop())

            # Загружаем данные из базы
            await self._load_data()

            # Регистрируем обработчики событий
            self._register_handlers()

            self.running = True
            logger.info("Мониторинг каналов активирован")

            self.ensure_task = asyncio.create_task(self.ensure_connected())

            try:
                await self.client.run_until_disconnected()
            except (OSError, ConnectionError) as e:
                logger.error("Ошибка соединения: %s", e)
                raise
            finally:
                self.running = False
                if self.ensure_task:
                    self.ensure_task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await self.ensure_task
                if hasattr(self, '_backup_task'):
                    self._backup_task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await self._backup_task

        except Exception as e:
            logger.error(f"Ошибка запуска клиента: {e}")
            raise

    async def stop(self):
        """Останавливает клиент"""
        self.running = False
        if self.client:
            await self.client.disconnect()
            logger.info("Telegram клиент остановлен")

    async def is_authorized(self) -> bool:
        """Проверяет авторизацию клиента."""
        if self.client:
            try:
                return await self.client.is_user_authorized()
            except Exception as e:  # pragma: no cover - unexpected
                logger.error("Ошибка проверки авторизации: %s", e)
                return False

        tmp_client = TelegramClient(
            Config.TELEGRAM_SESSION_NAME,
            Config.TELEGRAM_API_ID,
            Config.TELEGRAM_API_HASH,
        )
        try:
            await tmp_client.connect()
            return await tmp_client.is_user_authorized()
        except Exception as e:  # pragma: no cover - unexpected
            logger.error("Ошибка подключения для проверки авторизации: %s", e)
            return False
        finally:
            await tmp_client.disconnect()

    async def ensure_connected(self, interval: int = 60) -> None:
        """Периодически проверяет авторизацию и поддерживает соединение."""
        while self.running:
            await asyncio.sleep(interval)
            try:
                if not self.client:
                    continue
                if not self.client.is_connected():
                    await self.client.connect()
                if not await self.is_authorized():
                    logger.warning("Сессия потеряна, попытка восстановления из бэкапа...")
                    # Попытка восстановить из бэкапа
                    session_file = f"{Config.TELEGRAM_SESSION_NAME}.session"
                    backup_file = f"{Config.TELEGRAM_SESSION_NAME}.session.bak"
                    if os.path.exists(backup_file):
                        shutil.copyfile(backup_file, session_file)
                        await self.client.connect()
                        if await self.is_authorized():
                            logger.info("Сессия успешно восстановлена из резервной копии!")
                            if self.bot:
                                await self.bot.send_message(
                                    Config.ADMIN_USER_ID,
                                    "✅ Сессия восстановлена автоматически"
                                )
                            continue
                    # Если не удалось — уведомляем админа
                    logger.error("Не удалось восстановить сессию из бэкапа! Требуется ручная авторизация.")
                    if self.bot:
                        try:
                            await self.bot.send_message(
                                Config.ADMIN_USER_ID, 
                                "❗️ Сессия Telethon потеряна и не удалось восстановить из бэкапа! Требуется повторная авторизация."
                            )
                        except Exception as e:
                            logger.error(f"Ошибка отправки уведомления админу: {e}")
                    await self.client.disconnect()
            except asyncio.CancelledError:
                break
            except Exception as e:  # pragma: no cover - unexpected
                logger.error("Ошибка проверки соединения: %s", e)

    async def send_code(self, phone: str, force_sms: bool = False) -> None:
        """Отправляет код подтверждения на номер.

        Parameters
        ----------
        phone: str
            Номер телефона в международном формате.
        force_sms: bool
            Принудительно отправить код через SMS.
        """
        if not self.client:
            self.client = TelegramClient(
                Config.TELEGRAM_SESSION_NAME,
                Config.TELEGRAM_API_ID,
                Config.TELEGRAM_API_HASH,
            )

        if not self.client.is_connected():
            await self.client.connect()

        await self.client.send_code_request(phone, force_sms=force_sms)

    async def sign_in(
        self, phone: str, code: str, password: Optional[str] = None
    ) -> None:
        """Завершает вход по коду и, при необходимости, паролю 2FA."""
        if not self.client:
            self.client = TelegramClient(
                Config.TELEGRAM_SESSION_NAME,
                Config.TELEGRAM_API_ID,
                Config.TELEGRAM_API_HASH,
            )

        if not self.client.is_connected():
            await self.client.connect()

        if password is None:
            await self.client.sign_in(phone=phone, code=code)
        else:
            # При включенной двухфакторной аутентификации нужно вызывать sign_in
            # только с паролем после отправки кода
            await self.client.sign_in(password=password)

    async def _load_data(self):
        """Загружает данные из базы данных"""
        try:
            # Загружаем данные для всех разрешённых пользователей
            users = Config.ALLOWED_USERS or [Config.ADMIN_USER_ID]
            for user_id in users:
                channels = await self.db.get_user_channels(user_id, enabled_only=True)
                if user_id not in self.monitored_channels:
                    self.monitored_channels[user_id] = set()

                for channel in channels:
                    self.monitored_channels[user_id].add(channel.channel_id)

                filters = await self.db.get_user_filters(user_id, enabled_only=True)
                self.filter_manager.load_user_filters(user_id, filters)
                settings = await self.db.get_user_settings(user_id)
                self.user_monitoring[user_id] = (
                    settings.monitoring_enabled if settings else True
                )

            logger.info(f"Загружены данные для {len(users)} пользователей")

        except Exception as e:
            logger.error(f"Ошибка загрузки данных: {e}")

    def _register_handlers(self):
        """Регистрирует обработчики событий"""

        @self.client.on(events.NewMessage)
        async def handle_new_message(event):
            await self._process_new_message(event)

    async def _process_new_message(self, event):
        """Обрабатывает новое сообщение"""
        try:
            if not self.running:
                return

            # Игнорируем исходящие сообщения, чтобы избежать циклов
            if event.out:
                return

            message = event.message
            if not message or not message.text:
                return

            # Получаем информацию о чате
            chat = await event.get_chat()
            if not hasattr(chat, "id"):
                return

            chat_id = get_peer_id(chat)

            # Проверяем, отслеживается ли этот канал
            user_id = None
            for uid, channel_ids in self.monitored_channels.items():
                if chat_id in channel_ids:
                    user_id = uid
                    break

            if not user_id:
                return

            if not self.user_monitoring.get(user_id, True):
                snippet = message.text.replace("\n", " ")[:50]
                logger.debug(
                    f"Пропуск сообщения из канала {chat_id}: мониторинг отключен. Фрагмент: {snippet}"
                )
                return

            # Проверяем сообщение фильтрами
            matches = self.filter_manager.check_message_all_filters(
                user_id, message.text
            )

            if not matches:
                snippet = message.text.replace("\n", " ")[:50]
                logger.debug(
                    f"Сообщение из канала {chat_id} не прошло фильтры. Фрагмент: {snippet}"
                )
                return

            for match in matches:
                sender_username = ""
                try:
                    sender = await event.get_sender()
                    sender_username = getattr(sender, "username", "") or ""
                except Exception:
                    sender_username = ""

                found_message = FoundMessage(
                    user_id=user_id,
                    filter_id=match.filter_id,
                    channel_id=chat_id,
                    message_id=message.id,
                    sender_id=getattr(message, "sender_id", None) or 0,
                    sender_username=sender_username,
                    message_text=message.text,
                    matched_keywords=match.matched_keywords,
                )

                message_id = await self.db.save_found_message(found_message)
                if message_id:
                    # Отправляем уведомление
                    await self._send_notification(user_id, found_message, chat, message)

        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}")

    async def _send_notification(
        self, user_id: int, found_message: FoundMessage, chat, original_message
    ):
        """Отправляет уведомление о найденном сообщении"""
        notification_text = ""
        try:
            # Получаем целевые чаты пользователя
            target_chats = await self.db.get_user_target_chats(user_id)
            if not target_chats:
                logger.warning(f"Нет целевых чатов для пользователя {user_id}")
                return

            # Получаем настройки пользователя
            settings = await self.db.get_user_settings(user_id)
            if not settings:
                logger.warning(f"Нет настроек для пользователя {user_id}")
                return

            # Определяем режим разметки
            parse_mode = "Markdown" if settings.forward_as_code else "HTML"

            # Формируем сообщение уведомления
            notification_text = await self._format_notification(
                found_message, chat, original_message, settings
            )

            if not self.bot:
                logger.error("Bot instance is not configured for notifications")
                return

            # Отправляем во все целевые чаты

            for target_chat in target_chats:
                text_excerpt = notification_text[:50].replace("\n", " ")
                try:
                    await self.bot.send_message(
                        target_chat.chat_id,
                        notification_text,
                        parse_mode=parse_mode,
                    )
                    logger.info(
                        f"Уведомление отправлено в чат {target_chat.chat_id}"
                    )
                except Exception as e:
                    logger.error(
                        f"Ошибка отправки в чат {target_chat.chat_id}: {e}"
                    )

        except Exception as e:
            excerpt = notification_text[:200]
            logger.error(
                f"Ошибка отправки уведомления: {e} | Notification excerpt: {excerpt}"
            )

    async def _format_notification(
        self, found_message: FoundMessage, chat, original_message, settings
    ) -> str:
        """Форматирует уведомление"""
        lines = []

        # Заголовок
        is_markdown = settings.forward_as_code
        bold = (lambda t: f"**{t}**") if is_markdown else (lambda t: f"<b>{t}</b>")
        code = (lambda t: f"`{t}`") if is_markdown else (lambda t: f"<code>{t}</code>")
        escape = escape_markdown if is_markdown else escape_html

        lines.append(f"🔍 {bold('Найдено совпадение!')}")
        lines.append("")

        # Prepare links if username is available
        channel_link = None
        message_link = None
        if getattr(chat, "username", None):
            channel_link = f"https://t.me/{chat.username}"
            if settings.include_message_link:
                message_link = f"{channel_link}/{original_message.id}"

        # Информация о канале
        if settings.include_channel_info:
            channel_name_raw = getattr(chat, "title", None) or getattr(
                chat, "username", "Неизвестный канал"
            )
            channel_name = escape(channel_name_raw)
            target_link = message_link or channel_link
            if target_link:
                if settings.forward_as_code:
                    lines.append(
                        f"📢 {bold('Канал:')} [{channel_name}]({target_link})"
                    )
                else:
                    lines.append(
                        f"📢 {bold('Канал:')} <a href='{target_link}'>{channel_name}</a>"
                    )
            else:
                lines.append(f"📢 {bold('Канал:')} {channel_name}")

                if getattr(chat, "username", None):
                    lines.append(f"🔗 @{chat.username}")

        # Время
        if settings.include_timestamp and original_message.date:
            lines.append(
                f"🕐 {bold('Время:')} {original_message.date.strftime('%d.%m.%Y %H:%M:%S')}"
            )

        # Найденные ключевые слова
        if found_message.matched_keywords:
            keywords_str = ", ".join(
                code(kw) for kw in found_message.matched_keywords
            )
            lines.append(f"🎯 {bold('Ключевые слова:')} {keywords_str}")

        if settings.include_sender_id:
            if found_message.sender_username:
                sender = escape(found_message.sender_username)
                lines.append(f"👤 {bold('Автор:')} @{sender}")
            elif found_message.sender_id:
                lines.append(
                    f"👤 {bold('Автор ID:')} {code(found_message.sender_id)}"
                )

        lines.append("")

        # Текст сообщения
        message_text = found_message.message_text
        truncated = False
        if len(message_text) > settings.max_message_length:
            message_text = message_text[: settings.max_message_length] + "..."
            truncated = True

        if settings.forward_as_code:
            message_text = escape_markdown(message_text)
            lines.append(bold("Сообщение:"))
            lines.append(f"```\n{message_text}\n```")
        else:
            if truncated or not settings.include_original_formatting:
                message_text = escape_html(message_text)
            lines.append(f"{bold('Сообщение:')}\n{message_text}")

        # Ссылка на сообщение
        if settings.include_message_link and message_link:
            lines.append("")
            if settings.forward_as_code:
                lines.append(f"🔗 [Перейти к сообщению]({message_link})")
            else:
                lines.append(f"🔗 <a href='{message_link}'>Перейти к сообщению</a>")

        return "\n".join(lines)

    async def add_channel_to_monitor(self, user_id: int, channel_id: int):
        """Добавляет канал в мониторинг"""
        if user_id not in self.monitored_channels:
            self.monitored_channels[user_id] = set()

        self.monitored_channels[user_id].add(channel_id)
        logger.info(
            f"Канал {channel_id} добавлен в мониторинг для пользователя {user_id}"
        )

    async def remove_channel_from_monitor(self, user_id: int, channel_id: int):
        """Удаляет канал из мониторинга"""
        if user_id in self.monitored_channels:
            self.monitored_channels[user_id].discard(channel_id)
            logger.info(
                f"Канал {channel_id} удален из мониторинга для пользователя {user_id}"
            )

    async def reload_filters(self, user_id: int):
        """Перезагружает фильтры пользователя"""
        filters = await self.db.get_user_filters(user_id, enabled_only=True)
        self.filter_manager.load_user_filters(user_id, filters)
        logger.info(f"Фильтры пользователя {user_id} перезагружены")

    async def set_monitoring_enabled(self, user_id: int, enabled: bool):
        """Обновляет статус мониторинга пользователя"""
        self.user_monitoring[user_id] = enabled
        state = "включен" if enabled else "выключен"
        logger.info(f"Мониторинг {state} для пользователя {user_id}")

    def is_monitoring_enabled(self, user_id: int) -> bool:
        """Возвращает текущий флаг мониторинга пользователя."""
        return self.user_monitoring.get(user_id, True)

    async def get_channel_info(self, channel_username: str) -> Optional[Dict]:
        """Получает информацию о канале"""
        try:
            entity = await self.client.get_entity(channel_username)
            if isinstance(entity, (Channel, Chat)):
                return {
                    "id": get_peer_id(entity),
                    "title": getattr(entity, "title", ""),
                    "username": getattr(entity, "username", ""),
                    "type": "channel" if isinstance(entity, Channel) else "chat",
                }
        except Exception as e:
            logger.error(
                f"Ошибка получения информации о канале {channel_username}: {e}"
            )

        return None

    async def resolve_channel(self, value: str) -> Optional[Dict[str, str]]:
        """Resolve channel or supergroup by username or link."""
        if not self.client:
            logger.error("Клиент не инициализирован")
            return None

        channel = value.strip()
        channel = channel.replace("http://", "").replace("https://", "")
        if channel.startswith("t.me/"):
            channel = channel.replace("t.me/", "")

        entity = None

        # t.me/c/<id> links contain raw channel ID
        match = re.match(r"c/(\d+)", channel)
        if match:
            cid = int(match.group(1))
            try:
                entity = await self.client.get_entity(PeerChannel(cid))
            except Exception as e:
                logger.error(f"Не удалось определить канал {value}: {e}")
                return None
        else:
            if re.fullmatch(r"-100\d+", channel):
                try:
                    real_id = int(channel[4:])
                    entity = await self.client.get_entity(PeerChannel(real_id))
                except Exception as e:
                    logger.error(f"Не удалось определить канал {value}: {e}")
                    return None
            elif re.fullmatch(r"-\d+", channel):
                try:
                    real_id = abs(int(channel))
                    entity = await self.client.get_entity(PeerChat(real_id))
                except Exception as e:
                    logger.error(f"Не удалось определить канал {value}: {e}")
                    return None
            else:
                if channel.lstrip("-").isdigit():
                    try:
                        channel = int(channel)
                    except ValueError:
                        pass
                elif channel.startswith("@"):
                    channel = channel[1:]

                try:
                    entity = await self.client.get_entity(channel)
                except Exception as e:
                    logger.error(f"Не удалось определить канал {value}: {e}")
                    return None

        if entity and hasattr(entity, "id"):
            return {
                "id": get_peer_id(entity),
                "title": getattr(entity, "title", "")
                or getattr(entity, "first_name", ""),
                "username": getattr(entity, "username", "") or "",
            }
        logger.warning(f"Неподдерживаемый идентификатор канала: {value}")
        return None

    async def resolve_chat(self, value: str) -> Optional[Dict[str, str]]:
        """Resolve chat, group or channel by id or username."""
        if not self.client:
            logger.error("Клиент не инициализирован")
            return None

        chat_value = value.strip()
        if chat_value.startswith("https://t.me/"):
            chat_value = chat_value.replace("https://t.me/", "")

        entity = None

        if re.fullmatch(r"-100\d+", chat_value):
            try:
                real_id = int(chat_value[4:])
                entity = await self.client.get_entity(PeerChannel(real_id))
            except Exception as e:
                logger.error(f"Не удалось определить чат {value}: {e}")
                return None
        elif re.fullmatch(r"-\d+", chat_value):
            try:
                real_id = abs(int(chat_value))
                entity = await self.client.get_entity(PeerChat(real_id))
            except Exception as e:
                logger.error(f"Не удалось определить чат {value}: {e}")
                return None
        else:
            if chat_value.lstrip("-").isdigit():
                try:
                    chat_value = int(chat_value)
                except ValueError:
                    pass
            elif chat_value.startswith("@"):
                chat_value = chat_value[1:]

            try:
                entity = await self.client.get_entity(chat_value)
            except Exception as e:
                logger.error(f"Не удалось определить чат {value}: {e}")
                return None

        if entity and hasattr(entity, "id"):
            title = getattr(entity, "title", "") or getattr(entity, "first_name", "")
            return {
                "id": get_peer_id(entity),
                "title": title,
                "username": getattr(entity, "username", "") or "",
            }
        logger.warning(f"Неподдерживаемый идентификатор чата: {value}")
        return None

    def get_status(self) -> Dict[str, Union[bool, Dict[int, bool]]]:
        """Return current monitoring status.

        The returned dictionary contains:
        - ``"running"``: ``bool`` — whether the client is running.
        - ``"user_monitoring"``: ``Dict[int, bool]`` — mapping of user IDs to
          their monitoring flag.
        """
        return {
            "running": self.running,
            "user_monitoring": dict(self.user_monitoring),
        }
      
    async def check_health(self) -> Dict[int, Dict[int, bool]]:
        """Check availability of monitored channels for all users."""
        if not self.client:
            logger.error("Клиент не инициализирован")
            return {}

        tasks = []
        mapping = []  # (user_id, channel_id) pairs matching tasks order
        for user_id, channels in self.monitored_channels.items():
            for channel_id in channels:
                tasks.append(self.client.get_entity(PeerChannel(abs(channel_id))))
                mapping.append((user_id, channel_id))

        results: Dict[int, Dict[int, bool]] = {}
        if not tasks:
            return results

        gathered = await asyncio.gather(*tasks, return_exceptions=True)
        for (user_id, channel_id), result in zip(mapping, gathered):
            if user_id not in results:
                results[user_id] = {}
            results[user_id][channel_id] = not isinstance(result, Exception)

        return results

    async def _session_backup_loop(self, interval: int = 300):
        """Фоновая задача для резервного копирования сессии каждые 5 минут."""
        session_file = f"{Config.TELEGRAM_SESSION_NAME}.session"
        backup_file = f"{Config.TELEGRAM_SESSION_NAME}.session.bak"
        while True:
            try:
                await asyncio.sleep(interval)
                if os.path.exists(session_file):
                    shutil.copyfile(session_file, backup_file)
                    logger.info("[SessionBackup] Резервная копия сессии обновлена.")
                else:
                    logger.warning("[SessionBackup] Файл сессии не найден для бэкапа.")
            except Exception as e:
                logger.error(f"[SessionBackup] Ошибка резервного копирования: {e}")

    async def _session_watchdog(self):
        """Мониторинг состояния сессии каждые 5 минут"""
        while True:
            try:
                if not await self.is_authorized():
                    await self._handle_session_issue()
                await asyncio.sleep(300)  # Проверка каждые 5 минут
            except Exception as e:
                logger.error(f"Ошибка в watchdog: {e}")
                await asyncio.sleep(300)

    async def _handle_session_issue(self):
        """Обработка проблем с сессией"""
        try:
            backup_name = f"{Config.TELEGRAM_SESSION_NAME}.bak"
            if os.path.exists(backup_name):
                logger.info("Пытаюсь восстановить сессию из бэкапа...")
                self.restore_session_from_backup()
                if await self.is_authorized():
                    logger.info("Сессия успешно восстановлена из бэкапа")
                    await self.bot.send_message(
                        Config.ADMIN_USER_ID,
                        "✅ Сессия восстановлена из бэкапа"
                    )
                    return
                
            logger.warning("Требуется повторная авторизация")
            await self.bot.send_message(
                Config.ADMIN_USER_ID,
                "⚠️ Требуется повторная авторизация! Запустите: python scripts/cli_login.py"
            )
        except Exception as e:
            logger.error(f"Ошибка восстановления: {str(e)}")
            await self.bot.send_message(
                Config.ADMIN_USER_ID,
                f"🔥 Критическая ошибка восстановления: {str(e)}"
            )
            raise

    def restore_session_from_backup(self):
        """Восстанавливает сессию из резервной копии"""
        try:
            session_file = f"{Config.TELEGRAM_SESSION_NAME}.session"
            backup_file = f"{Config.TELEGRAM_SESSION_NAME}.session.bak"
            
            if os.path.exists(backup_file):
                shutil.copyfile(backup_file, session_file)
                logger.info(f"Сессия восстановлена из {backup_file}")
                return True
            else:
                logger.warning(f"Файл бэкапа {backup_file} не найден")
                return False
        except Exception as e:
            logger.error(f"Ошибка восстановления сессии: {e}")
            return False
