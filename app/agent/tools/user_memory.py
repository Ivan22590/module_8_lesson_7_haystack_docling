"""Инструмент сохранения важных личных фактов о пользователе."""

from __future__ import annotations

import logging

from app.config import get_settings
from app.messages import is_service_text
from app.vectorstore.search import get_repository

logger = logging.getLogger(__name__)


def save_user_memory(fact: str, user_id: str | None = None) -> str:
    """Сохранить важный личный факт о пользователе в долговременную память."""
    settings = get_settings()
    if not user_id:
        return "Ошибка: не удалось определить пользователя для сохранения памяти."

    # Служебные ответы бота не должны попадать в долговременную память.
    if is_service_text(fact):
        logger.info("Служебное сообщение не сохранено в память: %r", fact)
        return "Служебное сообщение не сохраняется в долговременную память."

    try:
        result = get_repository().save_memory(
            fact,
            user_id=user_id,
            namespace=settings.namespace_user_memories,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ошибка сохранения памяти пользователя")
        return f"Не удалось сохранить факт в память: {exc}"

    if result.action == "created":
        return f"Запомнил важный факт о пользователе: «{fact}»."
    if result.action == "updated":
        return (
            "Обновил существующий слот памяти — похожий факт уже был "
            f"(косинусное сходство {result.similarity:.2f}): «{fact}»."
        )
    return (
        "Похожий факт уже сохранён в памяти "
        f"(косинусное сходство {result.similarity:.2f}) — пропускаю запись."
    )
