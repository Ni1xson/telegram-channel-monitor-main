# -*- coding: utf-8 -*-
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from database.models import UserSettings


class AdminKeyboards:
    """Клавиатуры для админ-бота"""

    @staticmethod
    def main_menu() -> ReplyKeyboardMarkup:
        """Главное меню"""
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📝 Управление фильтрами")],
                [KeyboardButton(text="📢 Управление каналами")],
                [KeyboardButton(text="🎯 Целевые чаты")],
                [
                    KeyboardButton(text="⚙️ Настройки"),
                    KeyboardButton(text="📊 Статистика"),
                ],
                [KeyboardButton(text="👤 User клиент")],
                [KeyboardButton(text="👥 Управление группой")],
                [KeyboardButton(text="ℹ️ Помощь")],
            ],
            resize_keyboard=True,
            one_time_keyboard=False,
        )
        return kb

    @staticmethod
    def cancel(callback_data: str = "cancel") -> InlineKeyboardMarkup:
        """Кнопка отмены/выхода"""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Отмена", callback_data=callback_data)]
            ]
        )

    @staticmethod
    def back_main() -> InlineKeyboardMarkup:
        """Кнопка возврата в главное меню"""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
            ]
        )

    @staticmethod
    def filters_menu() -> InlineKeyboardMarkup:
        """Меню управления фильтрами"""
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="➕ Добавить фильтр", callback_data="filter_add"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📋 Список фильтров", callback_data="filter_list"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔄 Обновить список", callback_data="filter_refresh"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🗑 Очистить все", callback_data="filter_clear_all"
                    )
                ],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")],
            ]
        )
        return kb

    @staticmethod
    def channels_menu() -> InlineKeyboardMarkup:
        """Меню управления каналами"""
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="➕ Добавить канал", callback_data="channel_add"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📋 Список каналов", callback_data="channel_list"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔄 Обновить список", callback_data="channel_refresh"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🗑 Очистить все", callback_data="channel_clear_all"
                    )
                ],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")],
            ]
        )
        return kb

    @staticmethod
    def user_client_menu(authorized: bool) -> InlineKeyboardMarkup:
        """Меню управления пользовательским клиентом"""
        rows = []

        if authorized:
            rows.append(
                [InlineKeyboardButton(text="🚪 Выйти", callback_data="user_logout")]
            )
        else:
            rows.append(
                [InlineKeyboardButton(text="🔑 Войти", callback_data="user_login")]
            )

        rows.extend(
            [
                [
                    InlineKeyboardButton(
                        text="📂 Проверить сессии", callback_data="user_sessions"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❌ Удалить сессию", callback_data="user_delete_session"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="💻 Авторизация в консоли",
                        callback_data="user_cli_login",
                    )
                ],
            ]
        )

        rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")])

        return InlineKeyboardMarkup(inline_keyboard=rows)

    @staticmethod
    def target_chats_menu() -> InlineKeyboardMarkup:
        """Меню управления целевыми чатами"""
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="➕ Добавить чат", callback_data="target_add"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📋 Список чатов", callback_data="target_list"
                    )
                ],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")],
            ]
        )
        return kb

    @staticmethod
    def settings_menu(settings: "UserSettings | None" = None) -> InlineKeyboardMarkup:
        """Меню настроек c отображением текущих значений"""

        def mark(text: str, flag: bool) -> str:
            return f"✅ {text}" if flag else f"❌ {text}"

        if settings:
            fmt_map = {
                "full": "Полный",
                "compact": "Компактный",
                "minimal": "Минимальный",
            }
            fmt = fmt_map.get(
                settings.notification_format,
                settings.notification_format,
            )
            format_text = f"📝 Формат уведомлений: {fmt}"
            time_text = mark("Показывать время", settings.include_timestamp)
            channel_text = mark("Показывать канал", settings.include_channel_info)
            link_text = mark("Показывать ссылки", settings.include_message_link)
            sender_text = mark("Показывать автора", settings.include_sender_id)
            monitoring_text = mark("Мониторинг", settings.monitoring_enabled)

            if settings.forward_as_code:
                formatting_text = "💬 Форматирование: Код"
            elif settings.include_original_formatting:
                formatting_text = "💬 Форматирование: Оригинал"
            else:
                formatting_text = "💬 Форматирование: Текст"
        else:
            format_text = "📝 Формат уведомлений"
            time_text = "Показывать время"
            channel_text = "Показывать канал"
            link_text = "Показывать ссылки"
            sender_text = "Показывать автора"
            formatting_text = "💬 Форматирование"
            monitoring_text = "Мониторинг"

        rows = [
            [
                InlineKeyboardButton(
                    text=format_text, callback_data="settings_format"
                )
            ],
            [InlineKeyboardButton(text=time_text, callback_data="settings_time")],
            [
                InlineKeyboardButton(
                    text=channel_text, callback_data="settings_channel"
                )
            ],
            [InlineKeyboardButton(text=link_text, callback_data="settings_link")],
            [InlineKeyboardButton(text=sender_text, callback_data="settings_sender")],
            [
                InlineKeyboardButton(
                    text=formatting_text, callback_data="settings_formatting"
                )
            ],
            [
                InlineKeyboardButton(
                    text=monitoring_text, callback_data="settings_monitoring"
                )
            ],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")],
        ]

        return InlineKeyboardMarkup(inline_keyboard=rows)

    @staticmethod
    def filter_logic_types() -> InlineKeyboardMarkup:
        """Типы логики фильтров"""
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Содержит", callback_data="logic_contains")],
                [
                    InlineKeyboardButton(
                        text="Точное совпадение", callback_data="logic_exact"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="Все слова", callback_data="logic_all_words"
                    )
                ],
                [InlineKeyboardButton(text="Фраза", callback_data="logic_phrase")],
                [
                    InlineKeyboardButton(
                        text="Регулярное выражение", callback_data="logic_regex"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="Не содержит", callback_data="logic_not_contains"
                    )
                ],
                [InlineKeyboardButton(text="🔙 Отмена", callback_data="filter_cancel")],
            ]
        )
        return kb

    @staticmethod
    def boolean_choice(
        true_text: str = "Да",
        false_text: str = "Нет",
        true_callback: str = "choice_true",
        false_callback: str = "choice_false",
    ) -> InlineKeyboardMarkup:
        """Выбор да/нет"""
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text=true_text, callback_data=true_callback),
                    InlineKeyboardButton(text=false_text, callback_data=false_callback),
                ]
            ]
        )
        return kb

    @staticmethod
    def filter_actions(filter_id: int) -> InlineKeyboardMarkup:
        """Действия с фильтром"""
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✏️ Редактировать",
                        callback_data=f"filter_edit_{filter_id}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔄 Вкл/Выкл",
                        callback_data=f"filter_toggle_{filter_id}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❌ Удалить",
                        callback_data=f"filter_delete_{filter_id}",
                    )
                ],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="filter_list")],
            ]
        )
        return kb

    @staticmethod
    def channel_actions(channel_id: int) -> InlineKeyboardMarkup:
        """Действия с каналом"""
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔄 Вкл/Выкл", callback_data=f"channel_toggle_{channel_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❌ Удалить", callback_data=f"channel_delete_{channel_id}"
                    )
                ],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="channel_list")],
            ]
        )
        return kb

    @staticmethod
    def confirmation(action: str, item_id: int) -> InlineKeyboardMarkup:
        """Подтверждение действия"""
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Да", callback_data=f"confirm_{action}_{item_id}"
                    ),
                    InlineKeyboardButton(
                        text="❌ Нет", callback_data=f"cancel_{action}"
                    ),
                ]
            ]
        )
        return kb

    @staticmethod
    def confirm_chat(user_id: int, chat_id: int) -> InlineKeyboardMarkup:
        """Кнопка подтверждения добавления чата"""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Подтвердить чат",
                        callback_data=f"target_confirm_{user_id}_{chat_id}",
                    )
                ]
            ]
        )
