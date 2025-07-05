# -*- coding: utf-8 -*-
"""Utility helpers used across the project."""

from html import escape as _escape_html
from aiogram.utils.text_decorations import markdown_decoration


def escape_html(text: str) -> str:
    """Escape HTML entities in ``text`` for safe usage in Telegram messages."""

    return _escape_html(text, quote=True)


def escape_markdown(text: str) -> str:
    """Escape special Markdown characters in ``text``."""

    return markdown_decoration.quote(text)

