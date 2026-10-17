"""Хендлер текстовых сообщений: память диалога → агент → ответ."""

from __future__ import annotations

import logging
from typing import Any

from telebot import TeleBot

from app.agent import AgentResult, run_agent
from app.bot.formatting import edit_safely, send_long_message, user_display_name
from app.constants import TELEGRAM_MESSAGE_LIMIT
from app.messages import (
    SERVICE_ECHO_REPLY,
    THINKING_STATUS,
    TOOL_STATUS,
    is_service_text,
)
from app.vectorstore.search import get_repository

logger = logging.getLogger(__name__)


def save_user_message_to_memory(chat_id: int, user_text: str) -> None:
    """Сохранить ТЕКСТ сообщения пользователя в Pinecone (контекст диалога).

    Служебные тексты бота сюда не доходят (фильтруются в хендлере); менеджер
    дополнительно пропускает служебный текст и дубликаты (косинусное сходство
    выше порога → update/skip).
    """
    try:
        result = get_repository().save_user_message(user_text, user_id=str(chat_id))
        logger.info(
            "Контекст диалога: action=%s, similarity=%.4f, text=%r",
            result.action,
            result.similarity,
            user_text,
        )
    except Exception:  # noqa: BLE001 — сбой памяти не должен ломать ответ
        logger.exception("Не удалось сохранить сообщение в Pinecone")


def register(bot: TeleBot) -> None:
    """Зарегистрировать обработчик текстовых сообщений."""

    @bot.message_handler(func=lambda m: True, content_types=["text"])
    def handle_text(message: Any) -> None:
        chat_id = message.chat.id
        user_text = (message.text or "").strip()
        if not user_text:
            return

        # Служебные ответы бота не обрабатываются и не сохраняются в память.
        if is_service_text(user_text):
            logger.info("Служебное сообщение из чата %s пропущено: %r", chat_id, user_text)
            bot.reply_to(message, SERVICE_ECHO_REPLY)
            return

        # Тексты пользователя сохраняются в Pinecone (контекст диалога с
        # косинусным дедупом); ответы бота — только в историю чата.
        save_user_message_to_memory(chat_id, user_text)

        user_name = user_display_name(message)
        status_message = bot.send_message(chat_id, THINKING_STATUS)

        def on_tool_called(tool_name: str) -> None:
            edit_safely(
                bot,
                chat_id,
                status_message.message_id,
                TOOL_STATUS.get(tool_name, "⚙️ Работаю…"),
            )

        try:
            result: AgentResult = run_agent(
                chat_id,
                user_text,
                user_name=user_name,
                on_tool_called=on_tool_called,
            )
        except Exception:  # noqa: BLE001
            logger.exception("Ошибка при обработке сообщения из чата %s", chat_id)
            edit_safely(
                bot,
                chat_id,
                status_message.message_id,
                "⚠️ Произошла ошибка при обработке запроса. Попробуйте позже.",
            )
            return

        answer = result.text

        # Заменяем статусное сообщение финальным ответом (разрезая по лимиту
        # Telegram); если редактирование не удалось — отправляем отдельно.
        if len(answer) > TELEGRAM_MESSAGE_LIMIT:
            edit_safely(
                bot, chat_id, status_message.message_id, "✅ Готово, отправляю ответ…"
            )
            send_long_message(bot, chat_id, answer)
        elif not edit_safely(bot, chat_id, status_message.message_id, answer):
            send_long_message(bot, chat_id, answer)

        # Если агент достал фото собаки — отправляем его отдельным сообщением.
        if result.photo_url:
            try:
                bot.send_photo(chat_id, result.photo_url, caption="🐶 Фото собаки")
            except Exception:  # noqa: BLE001
                logger.exception("Не удалось отправить фото собаки")
