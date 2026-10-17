"""Регистрация всех хендлеров Telegram-бота."""

from __future__ import annotations

from telebot import TeleBot

from app.bot.handlers import commands, documents, text


def register_handlers(bot: TeleBot) -> None:
    """Навесить на бота команды, обработку текста и документов."""
    commands.register(bot)
    text.register(bot)
    documents.register(bot)
