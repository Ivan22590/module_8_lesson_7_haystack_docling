"""Прикладной сервис загрузки контента в векторную базу.

``IngestionService`` — точка входа для бота:

- :meth:`ingest_bytes` — принять файл (как ``bytes``), прогнать через
  ingestion-пайплайн (Docling → эмбеддер → Pinecone) и вернуть отчёт;
- :meth:`ingest_text` — сохранить обычный текст (например, статью по URL),
  разбив его на чанки.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache

from haystack import Document, Pipeline
from haystack.components.preprocessors import DocumentSplitter
from haystack.dataclasses import ByteStream

from app.config import get_settings
from app.ingestion.metadata import build_file_meta
from app.ingestion.pipeline import CONVERTER, WRITER, get_ingestion_pipeline
from app.vectorstore.search import DocumentRepository, get_repository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IngestionReport:
    """Итог обработки файла."""

    file_name: str
    chunks: int
    pages: int | None
    full_text: str

    @property
    def ok(self) -> bool:
        """Удалось ли извлечь хотя бы один непустой чанк."""
        return self.chunks > 0


class IngestionService:
    """Загрузка файлов и текстов в Pinecone через Haystack-пайплайн."""

    def __init__(
        self,
        pipeline: Pipeline | None = None,
        repository: DocumentRepository | None = None,
    ) -> None:
        self._pipeline = pipeline or get_ingestion_pipeline()
        self._repository = repository or get_repository()

    def ingest_bytes(
        self,
        data: bytes,
        file_name: str,
        chat_id: int,
        *,
        mime_type: str | None = None,
    ) -> IngestionReport:
        """Проанализировать файл через Docling и сохранить чанки в векторную базу.

        :param data: содержимое файла;
        :param file_name: имя файла (нужно Docling для определения формата);
        :param chat_id: идентификатор чата Telegram;
        :param mime_type: MIME-тип файла, если известен.
        """
        source = ByteStream(
            data=data,
            meta={"file_name": file_name, **({"mime_type": mime_type} if mime_type else {})},
        )
        meta = build_file_meta(file_name, chat_id, mime_type=mime_type)

        result = self._pipeline.run(
            {CONVERTER: {"sources": [source], "meta": meta}}
        )
        documents = result.get(WRITER, {}).get("documents", [])
        return self._build_report(file_name, documents)

    def ingest_text(
        self,
        text: str,
        source: str,
        *,
        dedupe: bool = False,
    ) -> int:
        """Разбить текст на чанки, посчитать эмбеддинги и сохранить в базу знаний.

        Возвращает число записанных чанков.
        """
        settings = get_settings()
        raw = Document(content=text, meta={"source": source, "source_type": "text"})
        splitter = DocumentSplitter(
            split_by="word",
            split_length=max(settings.chunk_size // 4, 50),
            split_overlap=max(settings.chunk_overlap // 8, 5),
        )
        chunks = splitter.run([raw])["documents"]
        embedded = self._repository.embed_documents([c.content or "" for c in chunks])
        for chunk, vector in zip(chunks, embedded):
            chunk.embedding = vector
        return self._repository.add_documents(
            chunks, namespace=settings.namespace_knowledge, dedupe=dedupe
        )

    @staticmethod
    def _build_report(file_name: str, documents: list[Document]) -> IngestionReport:
        """Собрать отчёт: число чанков, страниц и полный текст для резюме."""
        pages: set[int] = set()
        texts: list[str] = []
        for document in documents:
            content = (document.content or "").strip()
            if content:
                texts.append(content)
            page_number = (document.meta or {}).get("page_number")
            if isinstance(page_number, int):
                pages.add(page_number)
        return IngestionReport(
            file_name=file_name,
            chunks=len(texts),
            pages=len(pages) or None,
            full_text="\n\n".join(texts),
        )


@lru_cache(maxsize=1)
def get_ingestion_service() -> IngestionService:
    """Единый (кэшированный) экземпляр ``IngestionService``."""
    return IngestionService()
