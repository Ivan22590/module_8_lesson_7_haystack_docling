"""Telegram-бот-помощник на Haystack + Docling + Pinecone.

Пакет ``app`` содержит всю прикладную логику, разделённую по слоям:

- ``config``        — загрузка ``.env`` и неизменяемые настройки;
- ``llm``           — фабрики LLM и эмбеддеров (OpenAI-совместимый провайдер);
- ``vectorstore``   — доступ к Pinecone (хранение, поиск, дедуп, запись);
- ``ingestion``     — приём файлов через Docling и загрузка в Pinecone;
- ``generation``    — RAG-пайплайн генерации ответов и резюме;
- ``agent``         — Haystack Agent, инструменты, история диалога;
- ``bot``           — Telegram-слой (хендлеры, сообщения, форматирование).
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "2.0.0"
