"""Точка входа: валидация конфигурации, прогрев Pinecone/Docling и запуск бота."""

from __future__ import annotations

import logging
import sys

from app.bot.app import create_bot
from app.config import ConfigError, get_settings
from app.ingestion import warm_up_docling
from app.logging_setup import configure_logging
from app.vectorstore.store import get_vector_store


def main() -> None:
    """Запустить Telegram-бота с RAG-агентом и обработкой файлов."""
    configure_logging()
    logger = logging.getLogger("main")

    try:
        get_settings()  # валидация .env до старта
        # Прогрев: подключение (и автосоздание при необходимости) индекса,
        # инициализация haystack-сторов и эмбеддеров.
        get_vector_store().stats()
    except ConfigError as exc:
        logger.error("❌ Ошибка конфигурации: %s", exc)
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        logger.error("❌ Не удалось подключиться к Pinecone: %s", exc)
        sys.exit(1)

    # Прогрев Docling (скачивание токенизатора чанкера). Не критичен для старта.
    warm_up_docling()

    bot = create_bot()
    logger.info("🚀 Бот запущен. Ожидаю сообщения…")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)


if __name__ == "__main__":
    main()
