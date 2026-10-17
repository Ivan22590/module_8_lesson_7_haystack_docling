"""Слой доступа к векторной базе: хранение, поиск, дедупликация, запись."""

from __future__ import annotations

from app.vectorstore.dedupe import (
    DuplicateCandidate,
    MemoryWriteResult,
    cosine_similarity,
)
from app.vectorstore.search import DocumentRepository, get_repository
from app.vectorstore.store import VectorStore, get_vector_store
from app.vectorstore.writer import PineconeWriter

__all__ = [
    "DocumentRepository",
    "DuplicateCandidate",
    "MemoryWriteResult",
    "PineconeWriter",
    "VectorStore",
    "cosine_similarity",
    "get_repository",
    "get_vector_store",
]
