"""Прикладные функции генерации: ответ по базе знаний и резюме по документу."""

from __future__ import annotations

import logging
import re

from haystack import Document
from haystack.dataclasses import ChatMessage

from app.config import get_settings
from app.generation.pipeline import (
    EMBEDDER,
    LLM,
    PROMPT,
    get_generation_pipeline,
)
from app.llm import get_chat_generator

logger = logging.getLogger(__name__)

# Сколько символов документа отдавать модели для резюме (ограничение контекста).
_SUMMARY_MAX_CHARS = 8000

_SUMMARY_SYSTEM = (
    "Ты — ассистент, который делает краткие резюме документов. "
    "Отвечай строго на языке документа."
)

_SUMMARY_TEMPLATE = (
    "Ниже содержимое загруженного документа.\n"
    "Сформулируй РОВНО {sentences} коротких предложений-резюме: о чём этот "
    "документ и что в нём главное.\n"
    "Без маркдауна, без списков, без пояснений и вступлений — только сам текст "
    "резюме.\n\n"
    "Документ:\n{text}"
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?…])\s+")


def retrieve(query: str, namespace: str | None = None, top_k: int | None = None) -> list[Document]:
    """Найти релевантные чанки в векторной базе (только retriever, без LLM)."""
    settings = get_settings()
    from app.vectorstore.search import get_repository

    return get_repository().search_by_text(
        query,
        namespace=namespace or settings.namespace_knowledge,
        k=top_k or settings.max_search_results,
    )


def answer(query: str, namespace: str | None = None) -> str:
    """Сгенерировать ответ по базе знаний через generation-пайплайн."""
    pipeline = get_generation_pipeline()
    result = pipeline.run(
        {
            EMBEDDER: {"text": query},
            PROMPT: {"query": query},
        }
    )
    replies = result.get(LLM, {}).get("replies", [])
    text = (replies[0].text or "").strip() if replies else ""
    return text or "Не удалось сформировать ответ по базе знаний."


def one_sentence_summary(text: str) -> str:
    """Краткое резюме документа: ровно ``SUMMARY_MAX_SENTENCES`` предложение(-й)."""
    settings = get_settings()
    sentences = max(1, settings.summary_max_sentences)
    document = (text or "").strip()
    if not document:
        return "Документ пуст или не содержит текста."

    prompt = _SUMMARY_TEMPLATE.format(sentences=sentences, text=document[:_SUMMARY_MAX_CHARS])
    messages = [
        ChatMessage.from_system(_SUMMARY_SYSTEM),
        ChatMessage.from_user(prompt),
    ]
    try:
        reply = get_chat_generator().run(messages)["replies"][0].text or ""
    except Exception:  # noqa: BLE001 — резюме не должно ронять обработку файла
        logger.exception("Не удалось составить резюме по документу")
        return "Не удалось составить резюме по содержимому файла."

    return _limit_sentences(reply.strip(), sentences)


def _limit_sentences(text: str, limit: int) -> str:
    """Ограничить текст числом предложений (на случай, если модель не послушалась)."""
    clean = " ".join(text.split())
    if not clean:
        return "Не удалось составить резюме по содержимому файла."
    parts = [p for p in _SENTENCE_SPLIT.split(clean) if p.strip()]
    if len(parts) <= limit:
        return clean
    return " ".join(parts[:limit]).strip()
