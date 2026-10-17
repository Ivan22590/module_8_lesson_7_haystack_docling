"""Высокоуровневые операции чтения/записи в векторную базу.

``DocumentRepository`` объединяет ``VectorStore`` (доступ к индексу),
эмбеддеры (``app.llm``) и правила дедупликации (``dedupe``). Это единая точка
входа для:

- записи документов (чанки файлов и статей) — :meth:`add_documents`;
- долговременной памяти о пользователе — :meth:`save_memory`;
- контекста диалога (тексты сообщений) — :meth:`save_user_message`;
- поиска по тексту/вектору — :meth:`search_by_text`, :meth:`search_by_vector`.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Sequence

from haystack import Document
from haystack.document_stores.types import DuplicatePolicy

from app.config import get_settings
from app.llm import get_document_embedder, get_text_embedder
from app.vectorstore.dedupe import (
    DedupePolicy,
    DuplicateCandidate,
    MemoryWriteResult,
    cosine_similarity,
)
from app.vectorstore.store import VectorStore, get_vector_store

logger = logging.getLogger(__name__)


def _utc_now_iso() -> str:
    """Текущее время в ISO-формате (UTC)."""
    return datetime.now(timezone.utc).isoformat()


class DocumentRepository:
    """Чтение и запись документов, памяти и контекста диалога в Pinecone."""

    def __init__(
        self, vector_store: VectorStore | None = None, policy: DedupePolicy | None = None
    ) -> None:
        self._store = vector_store or get_vector_store()
        self._policy = policy or DedupePolicy.from_settings()
        # Собственные экземпляры эмбеддеров: используются только через run()
        # (компонент Haystack можно добавить лишь в один Pipeline, поэтому
        # пайплайны создают свои экземпляры отдельно).
        self._text_embedder = None
        self._document_embedder = None

    # ------------------------------------------------------------------
    # Эмбеддинги
    # ------------------------------------------------------------------

    @property
    def text_embedder(self):
        """Ленивый эмбеддер запросов (один на репозиторий)."""
        if self._text_embedder is None:
            self._text_embedder = get_text_embedder()
        return self._text_embedder

    @property
    def document_embedder(self):
        """Ленивый эмбеддер документов (один на репозиторий)."""
        if self._document_embedder is None:
            self._document_embedder = get_document_embedder()
        return self._document_embedder

    def embed_text(self, text: str) -> list[float]:
        """Эмбеддинг запроса (одиночный текст)."""
        return list(self.text_embedder.run(text)["embedding"])

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Эмбеддинги списка текстов."""
        documents = [Document(content=t) for t in texts]
        embedded = self.document_embedder.run(documents)["documents"]
        return [list(doc.embedding) for doc in embedded]

    # ------------------------------------------------------------------
    # Запись
    # ------------------------------------------------------------------

    def add_documents(
        self,
        documents: Sequence[Document],
        namespace: str,
        *,
        dedupe: bool = False,
    ) -> int:
        """Сохранить документы в Pinecone. Вернуть число записанных чанков.

        При ``dedupe=True`` каждый документ проверяется на косинусное сходство
        с уже сохранёнными (по правилам ``DedupePolicy``).
        """
        if not documents:
            return 0
        if not dedupe:
            return self._store.store(namespace).write_documents(
                list(documents), policy=DuplicatePolicy.OVERWRITE
            )

        saved = 0
        for document in documents:
            result = self.save_document(document, namespace=namespace)
            if result.action in {"created", "updated"}:
                saved += 1
        return saved

    def save_document(
        self,
        document: Document,
        namespace: str,
        *,
        threshold: float | None = None,
        action: str | None = None,
        dedupe_filter: dict[str, Any] | None = None,
    ) -> MemoryWriteResult:
        """Сохранить один документ с проверкой на дубликат."""
        text = (document.content or "").strip()
        if not text:
            return MemoryWriteResult(action="skipped", similarity=0.0, id=None, text="")

        candidate = self.find_best_match(text, namespace=namespace, filter=dedupe_filter)
        return self._write(
            text=text,
            metadata=dict(document.meta or {}),
            namespace=namespace,
            candidate=candidate,
            threshold=threshold,
            action=action,
        )

    def save_memory(
        self,
        text: str,
        user_id: str,
        namespace: str | None = None,
        *,
        threshold: float | None = None,
        action: str | None = None,
    ) -> MemoryWriteResult:
        """Сохранить личный факт в долговременную память пользователя."""
        settings = get_settings()
        ns = namespace or settings.namespace_user_memories
        text = (text or "").strip()
        if not text:
            return MemoryWriteResult(action="skipped", similarity=0.0, id=None, text="")
        if not user_id:
            raise ValueError("user_id обязателен для сохранения личной памяти.")

        candidate = self.find_best_match(
            text,
            namespace=ns,
            filter={"field": "user_id", "operator": "==", "value": user_id},
        )
        return self._write(
            text=text,
            metadata={"user_id": user_id, "type": "memory"},
            namespace=ns,
            candidate=candidate,
            threshold=threshold,
            action=action,
        )

    def save_user_message(
        self,
        text: str,
        user_id: str,
        namespace: str | None = None,
        *,
        threshold: float | None = None,
        action: str | None = None,
    ) -> MemoryWriteResult:
        """Сохранить ТЕКСТ сообщения пользователя в контекст диалога.

        Служебные тексты и ответы бота сюда не доходят (фильтрация в боте).
        """
        settings = get_settings()
        ns = namespace or settings.namespace_dialog_context
        text = (text or "").strip()
        if not text:
            return MemoryWriteResult(action="skipped", similarity=0.0, id=None, text="")
        if not user_id:
            raise ValueError("user_id обязателен для сохранения контекста диалога.")

        candidate = self.find_best_match(
            text,
            namespace=ns,
            filter={"field": "user_id", "operator": "==", "value": user_id},
        )
        return self._write(
            text=text,
            metadata={"user_id": user_id, "type": "message"},
            namespace=ns,
            candidate=candidate,
            threshold=threshold,
            action=action,
        )

    # ------------------------------------------------------------------
    # Умная фильтрация дубликатов
    # ------------------------------------------------------------------

    def find_best_match(
        self,
        text: str,
        namespace: str,
        *,
        filter: dict[str, Any] | None = None,
        k: int = 1,
    ) -> DuplicateCandidate:
        """Найти самый похожий сохранённый фрагмент для данного текста."""
        query_vector = self.embed_text(text)
        try:
            matches = self._store.store(namespace)._embedding_retrieval(
                query_embedding=query_vector,
                filters=filter,
                top_k=k,
            )
        except Exception as exc:  # noqa: BLE001 — дедуп не должен ронять запись
            logger.warning("Не удалось выполнить поиск дубликатов: %s", exc)
            return DuplicateCandidate(id=None, similarity=0.0, text=None)

        if not matches:
            return DuplicateCandidate(id=None, similarity=0.0, text=None)

        best = matches[0]
        best_id = str(best.id or "")
        best_score = float(best.score or 0.0)
        if best.embedding:
            try:
                best_score = cosine_similarity(query_vector, list(best.embedding))
            except ValueError:
                pass
        return DuplicateCandidate(id=best_id, similarity=best_score, text=best.content)

    def _write(
        self,
        *,
        text: str,
        metadata: dict[str, Any],
        namespace: str,
        candidate: DuplicateCandidate,
        threshold: float | None,
        action: str | None,
    ) -> MemoryWriteResult:
        """Решить судьбу записи (created/updated/skipped) и выполнить её."""
        effective_threshold = (
            self._policy.threshold if threshold is None else threshold
        )
        if not self._policy.is_duplicate(candidate, threshold):
            document = Document(
                id=uuid.uuid4().hex,
                content=text,
                embedding=self.embed_text(text),
                meta={**metadata, "saved_at": _utc_now_iso()},
            )
            self._store.store(namespace).write_documents(
                [document], policy=DuplicatePolicy.OVERWRITE
            )
            logger.info(
                "action: created | similarity=%.4f (порог=%.2f) | id=%s | text=%r",
                candidate.similarity,
                effective_threshold,
                document.id,
                text,
            )
            return MemoryWriteResult(
                action="created",
                similarity=candidate.similarity,
                id=document.id,
                text=text,
            )

        effective_action = self._policy.resolve_action(action)
        if effective_action == "skip":
            logger.info(
                "action: skipped | similarity=%.4f (порог=%.2f) | id=%s | text=%r",
                candidate.similarity,
                effective_threshold,
                candidate.id,
                text,
            )
            return MemoryWriteResult(
                action="skipped",
                similarity=candidate.similarity,
                id=candidate.id,
                text=text,
            )

        document = Document(
            id=candidate.id or uuid.uuid4().hex,
            content=text,
            embedding=self.embed_text(text),
            meta={**metadata, "saved_at": _utc_now_iso()},
        )
        self._store.store(namespace).write_documents(
            [document], policy=DuplicatePolicy.OVERWRITE
        )
        logger.info(
            "action: updated | similarity=%.4f (порог=%.2f) | id=%s | text=%r",
            candidate.similarity,
            effective_threshold,
            document.id,
            text,
        )
        return MemoryWriteResult(
            action="updated",
            similarity=candidate.similarity,
            id=document.id,
            text=text,
        )

    # ------------------------------------------------------------------
    # Чтение
    # ------------------------------------------------------------------

    def search_by_text(
        self,
        query: str,
        namespace: str,
        k: int = 4,
        filter: dict[str, Any] | None = None,
    ) -> list[Document]:
        """Семантический поиск по тексту в заданном namespace."""
        return self._store.store(namespace)._embedding_retrieval(
            query_embedding=self.embed_text(query),
            filters=filter,
            top_k=k,
        )

    def search_by_text_with_score(
        self,
        query: str,
        namespace: str,
        k: int = 4,
        filter: dict[str, Any] | None = None,
    ) -> list[tuple[Document, float]]:
        """Поиск по тексту с косинусным сходством каждого результата."""
        docs = self.search_by_text(query, namespace=namespace, k=k, filter=filter)
        return [(doc, float(doc.score or 0.0)) for doc in docs]

    def search_by_vector(
        self,
        vector: Sequence[float],
        namespace: str,
        k: int = 4,
        filter: dict[str, Any] | None = None,
    ) -> list[Document]:
        """Поиск от готового эмбеддинга."""
        return self._store.store(namespace)._embedding_retrieval(
            query_embedding=list(vector),
            filters=filter,
            top_k=k,
        )

    def similarity_search(
        self,
        query: str,
        namespace: str,
        k: int = 4,
        filter: dict[str, Any] | None = None,
    ) -> list[Document]:
        """Совместимое имя для поиска по тексту."""
        return self.search_by_text(query, namespace=namespace, k=k, filter=filter)

    # ------------------------------------------------------------------
    # Обслуживание
    # ------------------------------------------------------------------

    def stats(self) -> Any:
        """Статистика индекса (прогрев подключения)."""
        return self._store.stats()


@lru_cache(maxsize=1)
def get_repository() -> DocumentRepository:
    """Единый (кэшированный) экземпляр ``DocumentRepository``."""
    return DocumentRepository()
