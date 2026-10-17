"""Сборка Telegram-бота (PyTelegramBotAPI) с зарегистрированными хендлерами."""

from __future__ import annotations

import logging

import telebot
from telebot import TeleBot

from app.bot.handlers import register_handlers
from app.config import get_settings

logger = logging.getLogger(__name__)


def create_bot() -> TeleBot:
    """Создать ``TeleBot`` с настроенной обработкой сообщений и документов."""
    token = get_settings().require_telegram_token()
    bot = telebot.TeleBot(token)
    register_handlers(bot)
    logger.info("Telegram-бот собран, хендлеры зарегистрированы")
    return bot
