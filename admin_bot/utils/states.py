# -*- coding: utf-8 -*-
from aiogram.fsm.state import State, StatesGroup


class FilterStates(StatesGroup):
    """Состояния для создания фильтра"""

    waiting_name = State()
    waiting_keywords = State()
    waiting_logic_type = State()
    waiting_case_sensitive = State()
    waiting_word_order = State()


class ChannelStates(StatesGroup):
    """Состояния для работы с каналами"""

    waiting_channel = State()
    waiting_removal_confirmation = State()


class TargetChatStates(StatesGroup):
    """Состояния для работы с целевыми чатами"""

    waiting_chat_id = State()
    waiting_forward = State()


class SettingsStates(StatesGroup):
    """Состояния для настроек"""

    waiting_max_length = State()


class AuthStates(StatesGroup):
    """Состояния для авторизации пользователя"""

    waiting_phone = State()
    waiting_code = State()
    waiting_password = State()
