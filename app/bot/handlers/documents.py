"""Хендлер присланных документов: Docling-анализ → Pinecone → резюме."""

from __future__ import annotations

import logging
from typing import Any

from telebot import TeleBot

from app.bot.files import FileTooLargeError, download_document
from app.bot.formatting import edit_safely, send_long_message
from app.config import get_settings
from app.generation import one_sentence_summary
from app.ingestion import get_ingestion_service
from app.messages import (
    FILE_DONE_MESSAGE,
    FILE_EMPTY_MESSAGE,
    FILE_ERROR_MESSAGE,
    FILE_RECEIVED_MESSAGE,
    FILE_TOO_LARGE_MESSAGE,
)

logger = logging.getLogger(__name__)


def register(bot: TeleBot) -> None:
    """Зарегистрировать обработчик документов (PDF, DOCX, PPTX, XLSX, ...)."""

    @bot.message_handler(content_types=["document"])
    def handle_document(message: Any) -> None:
        chat_id = message.chat.id
        document = message.document
        settings = get_settings()

        status_message = bot.send_message(chat_id, FILE_RECEIVED_MESSAGE)
        status_id = status_message.message_id

        # 1. Скачиваем файл (с проверкой размера).
        try:
            downloaded = download_document(
                bot, document, max_bytes=settings.max_file_size_bytes
            )
        except FileTooLargeError as exc:
            logger.info("Файл отклонён по размеру: %s", exc)
            edit_safely(
                bot,
                chat_id,
                status_id,
                FILE_TOO_LARGE_MESSAGE.format(limit=settings.max_file_size_mb),
            )
            return
        except Exception:  # noqa: BLE001
            logger.exception("Не удалось скачать файл из чата %s", chat_id)
            edit_safely(bot, chat_id, status_id, FILE_ERROR_MESSAGE)
            return

        # 2. Анализ через Docling и загрузка чанков в Pinecone.
        try:
            report = get_ingestion_service().ingest_bytes(
                downloaded.data,
                downloaded.file_name,
                chat_id,
                mime_type=downloaded.mime_type,
            )
        except Exception:  # noqa: BLE001
            logger.exception("Ошибка обработки файла %r", downloaded.file_name)
            edit_safely(bot, chat_id, status_id, FILE_ERROR_MESSAGE)
            return

        if not report.ok:
            logger.info("Из файла %r не извлечено текста", downloaded.file_name)
            edit_safely(bot, chat_id, status_id, FILE_EMPTY_MESSAGE)
            return

        logger.info(
            "Файл %r загружен: чанков=%d, страниц=%s",
            report.file_name,
            report.chunks,
            report.pages,
        )

        # 3. Подтверждение + краткое резюме (ровно одно предложение).
        edit_safely(bot, chat_id, status_id, FILE_DONE_MESSAGE)
        try:
            summary = one_sentence_summary(report.full_text)
        except Exception:  # noqa: BLE001 — резюме не должно ломать ответ
            logger.exception("Ошибка составления резюме по файлу %r", report.file_name)
            return
        send_long_message(bot, chat_id, summary)
