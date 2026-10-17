"""Фабрики моделей Haystack: чат-генератор и эмбеддеры.

Провайдер — OpenAI-совместимый (``OPENAI_BASE_URL``, например ProxyAPI).

Важно: компонент Haystack можно добавить только в один ``Pipeline``. Поэтому
фабрики возвращают **новый** экземпляр на каждый вызов: пайплайны собираются
один раз (и кэшируются целиком), а ``DocumentRepository``/``Agent``/инструменты
держат собственные экземпляры и используют их напрямую через ``run()``.
"""

from __future__ import annotations

from haystack.components.embedders import OpenAIDocumentEmbedder, OpenAITextEmbedder
from haystack.components.generators.chat import OpenAIChatGenerator

from app.config import get_settings


def get_chat_generator() -> OpenAIChatGenerator:
    """Создать чат-генератор LLM (для агента, генерации, vision и резюме)."""
    settings = get_settings()
    return OpenAIChatGenerator(
        model=settings.openai_model,
        api_base_url=settings.openai_base_url,
    )


def get_text_embedder() -> OpenAITextEmbedder:
    """Создать эмбеддер текстовых запросов (поиск и дедупликация)."""
    settings = get_settings()
    return OpenAITextEmbedder(
        model=settings.embedding_model,
        api_base_url=settings.openai_base_url,
    )


def get_document_embedder() -> OpenAIDocumentEmbedder:
    """Создать эмбеддер документов (чанки файлов, статей и записей памяти)."""
    settings = get_settings()
    return OpenAIDocumentEmbedder(
        model=settings.embedding_model,
        api_base_url=settings.openai_base_url,
        progress_bar=False,
    )
