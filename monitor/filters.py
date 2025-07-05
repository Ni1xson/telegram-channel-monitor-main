# -*- coding: utf-8 -*-
import re
from typing import List, Tuple, Dict
from dataclasses import dataclass
from enum import Enum

from database.models import Filter


class FilterLogicType(Enum):
    """Типы логики фильтрации"""

    CONTAINS = "contains"  # Содержит любое из слов
    EXACT = "exact"  # Точное совпадение
    REGEX = "regex"  # Регулярное выражение
    NOT_CONTAINS = "not_contains"  # Не содержит
    ALL_WORDS = "all_words"  # Содержит все слова
    PHRASE = "phrase"  # Точная фраза
    STARTS_WITH = "starts_with"  # Начинается с
    ENDS_WITH = "ends_with"  # Заканчивается на


@dataclass
class FilterMatch:
    """Результат проверки фильтра"""

    matched: bool
    filter_id: int
    matched_keywords: List[str]
    match_positions: List[Tuple[int, int]] = None  # Позиции совпадений

    def __post_init__(self):
        if self.match_positions is None:
            self.match_positions = []


class MessageFilter:
    """Класс для фильтрации сообщений"""

    def __init__(self, filter_obj: Filter):
        self.filter = filter_obj
        self._compiled_regex = None

        # Предкомпилируем регулярные выражения для оптимизации
        if self.filter.logic_type == FilterLogicType.REGEX.value:
            try:
                flags = 0 if self.filter.case_sensitive else re.IGNORECASE
                pattern = "|".join(self.filter.keywords)
                self._compiled_regex = re.compile(pattern, flags)
            except re.error as e:
                print(f"Ошибка в регулярном выражении фильтра {self.filter.id}: {e}")
                self._compiled_regex = None

    def check_message(self, message_text: str) -> FilterMatch:
        """Проверяет сообщение на соответствие фильтру"""
        if not message_text or not self.filter.keywords:
            return FilterMatch(False, self.filter.id, [])

        # Обработка регистра
        text_to_check = (
            message_text if self.filter.case_sensitive else message_text.lower()
        )
        keywords_to_check = (
            self.filter.keywords
            if self.filter.case_sensitive
            else [kw.lower() for kw in self.filter.keywords]
        )

        logic_type = self.filter.logic_type
        matched_keywords = []
        match_positions = []

        if logic_type == FilterLogicType.CONTAINS.value:
            matched_keywords, match_positions = self._check_contains(
                text_to_check, keywords_to_check
            )

        elif logic_type == FilterLogicType.EXACT.value:
            matched_keywords, match_positions = self._check_exact(
                text_to_check, keywords_to_check
            )

        elif logic_type == FilterLogicType.REGEX.value:
            matched_keywords, match_positions = self._check_regex(message_text)

        elif logic_type == FilterLogicType.NOT_CONTAINS.value:
            # Инвертированная логика
            contains_match, _ = self._check_contains(text_to_check, keywords_to_check)
            matched_keywords = keywords_to_check if not contains_match else []

        elif logic_type == FilterLogicType.ALL_WORDS.value:
            matched_keywords, match_positions = self._check_all_words(
                text_to_check, keywords_to_check
            )

        elif logic_type == FilterLogicType.PHRASE.value:
            matched_keywords, match_positions = self._check_phrase(
                text_to_check, keywords_to_check
            )

        elif logic_type == FilterLogicType.STARTS_WITH.value:
            matched_keywords, match_positions = self._check_starts_with(
                text_to_check, keywords_to_check
            )

        elif logic_type == FilterLogicType.ENDS_WITH.value:
            matched_keywords, match_positions = self._check_ends_with(
                text_to_check, keywords_to_check
            )

        else:
            # По умолчанию - contains
            matched_keywords, match_positions = self._check_contains(
                text_to_check, keywords_to_check
            )

        matched = bool(matched_keywords)

        return FilterMatch(
            matched=matched,
            filter_id=self.filter.id,
            matched_keywords=matched_keywords,
            match_positions=match_positions,
        )

    def _check_contains(
        self, text: str, keywords: List[str]
    ) -> Tuple[List[str], List[Tuple[int, int]]]:
        """Проверка на содержание любого из ключевых слов"""
        matched = []
        positions = []

        for keyword in keywords:
            if keyword in text:
                matched.append(keyword)
                # Находим все позиции
                start = 0
                while True:
                    pos = text.find(keyword, start)
                    if pos == -1:
                        break
                    positions.append((pos, pos + len(keyword)))
                    start = pos + 1

        return matched, positions

    def _check_exact(
        self, text: str, keywords: List[str]
    ) -> Tuple[List[str], List[Tuple[int, int]]]:
        """Проверка на точное совпадение"""
        # Разбиваем текст на слова
        import string

        translator = str.maketrans("", "", string.punctuation)
        words = text.translate(translator).split()

        matched = []
        positions = []

        for keyword in keywords:
            if keyword in words:
                matched.append(keyword)
                # Находим позицию в оригинальном тексте
                word_start = text.find(keyword)
                if word_start != -1:
                    positions.append((word_start, word_start + len(keyword)))

        return matched, positions

    def _check_regex(self, text: str) -> Tuple[List[str], List[Tuple[int, int]]]:
        """Проверка регулярного выражения"""
        if not self._compiled_regex:
            return [], []

        matched = []
        positions = []

        for match in self._compiled_regex.finditer(text):
            matched.append(match.group())
            positions.append((match.start(), match.end()))

        return matched, positions

    def _check_all_words(
        self, text: str, keywords: List[str]
    ) -> Tuple[List[str], List[Tuple[int, int]]]:
        """Проверка на содержание всех ключевых слов"""
        matched = []
        positions = []

        all_found = True
        for keyword in keywords:
            if keyword in text:
                matched.append(keyword)
                pos = text.find(keyword)
                positions.append((pos, pos + len(keyword)))
            else:
                all_found = False
                break

        if not all_found:
            return [], []

        return matched, positions

    def _check_phrase(
        self, text: str, keywords: List[str]
    ) -> Tuple[List[str], List[Tuple[int, int]]]:
        """Проверка точной фразы"""
        matched = []
        positions = []

        for phrase in keywords:
            if phrase in text:
                matched.append(phrase)
                pos = text.find(phrase)
                positions.append((pos, pos + len(phrase)))

        return matched, positions

    def _check_starts_with(
        self, text: str, keywords: List[str]
    ) -> Tuple[List[str], List[Tuple[int, int]]]:
        """Проверка начала текста"""
        matched = []
        positions = []

        for keyword in keywords:
            if text.startswith(keyword):
                matched.append(keyword)
                positions.append((0, len(keyword)))

        return matched, positions

    def _check_ends_with(
        self, text: str, keywords: List[str]
    ) -> Tuple[List[str], List[Tuple[int, int]]]:
        """Проверка конца текста"""
        matched = []
        positions = []

        for keyword in keywords:
            if text.endswith(keyword):
                matched.append(keyword)
                start_pos = len(text) - len(keyword)
                positions.append((start_pos, len(text)))

        return matched, positions


class MessageFilterManager:
    """Менеджер фильтров сообщений"""

    def __init__(self):
        self.filters: Dict[int, List[MessageFilter]] = (
            {}
        )  # user_id -> List[MessageFilter]

    def load_user_filters(self, user_id: int, filters: List[Filter]):
        """Загружает фильтры пользователя"""
        self.filters[user_id] = [MessageFilter(f) for f in filters if f.enabled]

    def check_message_all_filters(
        self, user_id: int, message_text: str
    ) -> List[FilterMatch]:
        """Проверяет сообщение всеми фильтрами пользователя"""
        if user_id not in self.filters:
            return []

        matches = []
        for message_filter in self.filters[user_id]:
            match = message_filter.check_message(message_text)
            if match.matched:
                matches.append(match)

        return matches

    def add_filter(self, user_id: int, filter_obj: Filter):
        """Добавляет новый фильтр"""
        if user_id not in self.filters:
            self.filters[user_id] = []

        message_filter = MessageFilter(filter_obj)
        self.filters[user_id].append(message_filter)

    def remove_filter(self, user_id: int, filter_id: int):
        """Удаляет фильтр"""
        if user_id not in self.filters:
            return

        self.filters[user_id] = [
            f for f in self.filters[user_id] if f.filter.id != filter_id
        ]

    def clear_user_filters(self, user_id: int):
        """Очищает все фильтры пользователя"""
        if user_id in self.filters:
            del self.filters[user_id]
