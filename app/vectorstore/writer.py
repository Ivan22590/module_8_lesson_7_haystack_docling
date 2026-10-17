"""Компонент Haystack для записи документов в Pinecone (сток ingestion-пайплайна).

Принимает документы с уже посчитанными эмбеддингами (после ``DocumentEmbedder``)
и пишет их в конкретный ``PineconeDocumentStore`` с политикой ``OVERWRITE``.
Возвращает фактически записанные документы, чтобы вызывающая сторона могла
посчитать чанки/страницы и построить резюме.
"""

from __future__ import annotations

import logging

from haystack import Document, component
from haystack.document_stores.types import DuplicatePolicy
from haystack_integrations.document_stores.pinecone import PineconeDocumentStore

logger = logging.getLogger(__name__)


@component
class PineconeWriter:
    """Сток пайплайна: записать документы в Pinecone и вернуть их же."""

    def __init__(self, document_store: PineconeDocumentStore) -> None:
        self.document_store = document_store

    @component.output_types(documents=list[Document])
    def run(self, documents: list[Document]) -> dict[str, list[Document]]:
        """Записать документы, пропуская пустые по содержимому."""
        prepared = [doc for doc in documents if (doc.content or "").strip()]
        if not prepared:
            return {"documents": []}
        self.document_store.write_documents(prepared, policy=DuplicatePolicy.OVERWRITE)
        logger.info("PineconeWriter: записано %d чанков", len(prepared))
        return {"documents": prepared}
