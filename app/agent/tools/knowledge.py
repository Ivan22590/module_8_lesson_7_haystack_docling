"""Инструмент поиска по базе знаний, памяти пользователя и контексту диалога."""

from __future__ import annotations

import logging

from app.config import get_settings
from app.vectorstore.search import get_repository

logger = logging.getLogger(__name__)


def search_knowledge_base(query: str, user_id: str | None = None) -> str:
    """Семантический поиск по базе знаний, памяти и контексту диалога."""
    settings = get_settings()
    repository = get_repository()
    parts: list[str] = []

    try:
        docs = repository.search_by_text(
            query,
            namespace=settings.namespace_knowledge,
            k=settings.max_search_results,
        )
    except Exception as exc:  # noqa: BLE001 — инструмент не должен ронять агента
        logger.exception("Ошибка поиска по базе знаний")
        docs = []
        parts.append(f"Ошибка при поиске по базе знаний: {exc}")
    if docs:
        parts.append("Результаты поиска по базе знаний:")
        for doc in docs:
            source = doc.meta.get("source", "источник неизвестен")
            parts.append(f"[Источник: {source}]\n{doc.content}")

    if user_id:
        user_filter = {"field": "user_id", "operator": "==", "value": user_id}

        try:
            memories = repository.search_by_text(
                query,
                namespace=settings.namespace_user_memories,
                k=settings.max_search_results,
                filter=user_filter,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Ошибка поиска по памяти пользователя")
            memories = []
            parts.append(f"Ошибка при поиске по памяти пользователя: {exc}")
        if memories:
            parts.append("Личные факты о пользователе:")
            for doc in memories:
                parts.append(f"- {doc.content}")

        try:
            dialog = repository.search_by_text(
                query,
                namespace=settings.namespace_dialog_context,
                k=settings.max_search_results,
                filter=user_filter,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Ошибка поиска по контексту диалога")
            dialog = []
        if dialog:
            parts.append("Что вы говорили раньше по этой теме:")
            for doc in dialog:
                parts.append(f"- {doc.content}")

    if not parts:
        return "В базе знаний и памяти пользователя ничего не найдено по этому запросу."
    return "\n\n".join(parts)
