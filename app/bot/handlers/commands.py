"""Хендлеры команд: /start, /help, /reset."""

from __future__ import annotations

import logging
from typing import Any

from telebot import TeleBot

from app.agent import reset_chat
from app.bot.formatting import user_display_name, welcome_message
from app.messages import HELP_MESSAGE

logger = logging.getLogger(__name__)


def register(bot: TeleBot) -> None:
    """Зарегистрировать обработчики команд."""

    @bot.message_handler(commands=["start"])
    def handle_start(message: Any) -> None:
        # Имя может отсутствовать (нет имени/фамилии/username) — есть fallback.
        name = user_display_name(message)
        bot.reply_to(message, welcome_message(name))

    @bot.message_handler(commands=["help"])
    def handle_help(message: Any) -> None:
        bot.reply_to(message, HELP_MESSAGE)

    @bot.message_handler(commands=["reset"])
    def handle_reset(message: Any) -> None:
        chat_id = message.chat.id
        reset_chat(chat_id)
        bot.reply_to(message, "✅ История диалога очищена.")
