"""Служебная CLI: проверка подключения и обслуживание Pinecone/Docling.

Примеры:

    python cli.py                  # проверка подключения + статистика индекса
    python cli.py --warm-docling   # прогреть Docling (скачать модели заранее)
    python cli.py --reset-memory   # очистить namespace личной памяти
    python cli.py --reset-dialog   # очистить namespace контекста диалогов
    python cli.py --delete-index   # удалить индекс Pinecone целиком
"""

from __future__ import annotations

import argparse
import sys
from typing import Iterable

from app.config import ConfigError, get_settings
from app.ingestion import warm_up_docling
from app.logging_setup import configure_logging
from app.vectorstore.store import get_vector_store


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Обслуживание Pinecone/Docling")
    parser.add_argument(
        "--check", action="store_true", help="Проверить подключение к Pinecone (по умолчанию)"
    )
    parser.add_argument(
        "--warm-docling", action="store_true", help="Прогреть DoclingConverter и выйти"
    )
    parser.add_argument(
        "--reset-memory", action="store_true", help="Очистить namespace личной памяти"
    )
    parser.add_argument(
        "--reset-dialog", action="store_true", help="Очистить namespace контекста диалогов"
    )
    parser.add_argument(
        "--delete-index", action="store_true", help="Удалить индекс Pinecone целиком"
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    """Точка входа CLI."""
    args = _build_parser().parse_args(list(argv) if argv is not None else None)
    configure_logging()
    logger = __import__("logging").getLogger("cli")

    if args.warm_docling:
        return 0 if warm_up_docling() else 1

    try:
        settings = get_settings()
    except ConfigError as exc:
        logger.error("❌ Ошибка конфигурации: %s", exc)
        return 1

    store = get_vector_store()
    try:
        if args.delete_index:
            removed = store.delete_index()
            logger.info("Индекс: %s", "удалён" if removed else "не найден")
            return 0
        if args.reset_memory:
            store.delete_namespace(settings.namespace_user_memories)
            return 0
        if args.reset_dialog:
            store.delete_namespace(settings.namespace_dialog_context)
            return 0

        stats = store.stats()
        logger.info(
            "✅ Подключение успешно: индекс=%r, dimension=%s, векторов=%s",
            settings.pinecone_index_name,
            stats.get("dimension"),
            stats.get("total_vector_count"),
        )
        return 0
    except Exception as exc:  # noqa: BLE001 — CLI сообщает и падает
        logger.exception("❌ Ошибка: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
