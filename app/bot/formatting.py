"""Вспомогательное форматирование и безопасная отправка сообщений Telegram."""

from __future__ import annotations

import logging
from typing import Any

from telebot import TeleBot

from app.constants import FALLBACK_USER_NAME, TELEGRAM_MESSAGE_LIMIT
from app.messages import WELCOME_MESSAGE

logger = logging.getLogger(__name__)


def edit_safely(bot: TeleBot, chat_id: int, message_id: int, text: str) -> bool:
    """Отредактировать сообщение. Вернуть True при успехе (ошибки не пробрасываем)."""
    try:
        bot.edit_message_text(text, chat_id, message_id)
        return True
    except Exception:  # noqa: BLE001 — например, «message is not modified»
        logger.debug("Не удалось отредактировать сообщение %d", message_id, exc_info=True)
        return False


def send_long_message(bot: TeleBot, chat_id: int, text: str) -> None:
    """Отправить текст, разрезав его по лимиту Telegram (4096 символов)."""
    for start in range(0, len(text), TELEGRAM_MESSAGE_LIMIT):
        bot.send_message(chat_id, text[start : start + TELEGRAM_MESSAGE_LIMIT])


def user_display_name(message: Any) -> str:
    """Определить имя собеседника: имя+фамилия → @username → id → fallback.

    Обрабатывает случай, когда у пользователя нет ни имени/фамилии,
    ни юзернейма: тогда возвращается нейтральное обращение (не падаем).
    """
    user = getattr(message, "from_user", None)
    if user is None:
        return FALLBACK_USER_NAME

    first = str(getattr(user, "first_name", "") or "").strip()
    last = str(getattr(user, "last_name", "") or "").strip()
    full_name = " ".join(part for part in (first, last) if part)
    if full_name:
        return full_name

    username = str(getattr(user, "username", "") or "").strip()
    if username:
        return f"@{username}"

    user_id = getattr(user, "id", None)
    if user_id is not None:
        return f"пользователь {user_id}"
    return FALLBACK_USER_NAME


def welcome_message(name: str) -> str:
    """Собрать приветствие с обращением по имени (или без него)."""
    if not name or name == FALLBACK_USER_NAME:
        return WELCOME_MESSAGE
    return WELCOME_MESSAGE.replace("Привет!", f"Привет, {name}!", 1)
