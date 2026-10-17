"""Ingestion-пайплайн Haystack: Docling → эмбеддер → запись в Pinecone.

Компоненты соединены линейно:

    converter (DoclingConverter) -> embedder (OpenAIDocumentEmbedder) -> writer (PineconeWriter)

Вход пайплайна: ``{"converter": {"sources": [ByteStream|path], "meta": {...}}}``.
"""

from __future__ import annotations

from functools import lru_cache

from haystack import Pipeline

from app.config import get_settings
from app.ingestion.converter import get_docling_converter
from app.llm import get_document_embedder
from app.vectorstore.store import get_vector_store
from app.vectorstore.writer import PineconeWriter

# Имена компонентов пайплайна (используются при запуске и чтении результата).
CONVERTER = "converter"
EMBEDDER = "embedder"
WRITER = "writer"


def build_ingestion_pipeline() -> Pipeline:
    """Собрать ingestion-пайплайн для загрузки файлов в Pinecone."""
    settings = get_settings()
    pipeline = Pipeline()
    pipeline.add_component(CONVERTER, get_docling_converter())
    pipeline.add_component(EMBEDDER, get_document_embedder())
    pipeline.add_component(
        WRITER, PineconeWriter(get_vector_store().store(settings.namespace_knowledge))
    )
    pipeline.connect(f"{CONVERTER}.documents", f"{EMBEDDER}.documents")
    pipeline.connect(f"{EMBEDDER}.documents", f"{WRITER}.documents")
    return pipeline


@lru_cache(maxsize=1)
def get_ingestion_pipeline() -> Pipeline:
    """Единый (кэшированный) ingestion-пайплайн."""
    return build_ingestion_pipeline()
