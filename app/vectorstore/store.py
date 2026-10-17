"""Низкоуровневый доступ к Pinecone: клиент и document store по namespace.

``VectorStore`` отвечает только за соединение и обслуживание индекса. Вся
прикладная логика (эмбеддинги, дедуп, поиск) живёт в ``search`` / ``dedupe``.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from haystack.utils.auth import Secret
from haystack_integrations.document_stores.pinecone import PineconeDocumentStore
from pinecone import Pinecone

from app.config import get_settings

logger = logging.getLogger(__name__)


class VectorStore:
    """Ленивое подключение к Pinecone и хранилища документов по namespace.

    Индекс создаётся автоматически при первом обращении (serverless, метрика
    ``cosine``, размерность ``EMBEDDING_DIM``). ``PineconeDocumentStore``
    создаётся отдельно на каждый namespace и кэшируется.
    """

    def __init__(
        self,
        api_key: str | None = None,
        index_name: str | None = None,
        *,
        embedding_dim: int | None = None,
        auto_create_index: bool = True,
    ) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.pinecone_api_key
        self.index_name = index_name or settings.pinecone_index_name
        self.embedding_dim = embedding_dim or settings.embedding_dim
        self.region = settings.pinecone_region
        self.cloud = settings.pinecone_cloud
        self.auto_create_index = auto_create_index

        self._client: Pinecone | None = None
        self._stores: dict[str, PineconeDocumentStore] = {}

    @property
    def client(self) -> Pinecone:
        """Raw-клиент Pinecone (служебные операции: статистика, удаление)."""
        if self._client is None:
            self._client = Pinecone(api_key=self.api_key)
        return self._client

    def store(self, namespace: str) -> PineconeDocumentStore:
        """Вернуть ``PineconeDocumentStore`` для namespace (создаётся по требованию)."""
        store = self._stores.get(namespace)
        if store is None:
            if not self.auto_create_index:
                raise RuntimeError(
                    f"Автосоздание индекса отключено (namespace={namespace!r})."
                )
            store = PineconeDocumentStore(
                index=self.index_name,
                namespace=namespace,
                dimension=self.embedding_dim,
                metric="cosine",
                spec={"serverless": {"region": self.region, "cloud": self.cloud}},
                show_progress=False,
                api_key=Secret.from_token(self.api_key),
            )
            self._stores[namespace] = store
        return store

    def stats(self) -> Any:
        """Статистика индекса (подключение + размерность/namespace'ы)."""
        answer = self.client.Index(self.index_name).describe_index_stats()
        # Прогрев haystack-стора (создаст индекс, если его ещё нет).
        _ = self.store(get_settings().namespace_knowledge)
        return answer

    def delete_namespace(self, namespace: str) -> None:
        """Удалить все записи в namespace (без ошибок, если он пуст)."""
        self.store(namespace).delete_all_documents()
        logger.info("Namespace %r очищен (или уже был пуст).", namespace)

    def delete_index(self, name: str | None = None) -> bool:
        """Удалить индекс Pinecone целиком (например, тестовый)."""
        target = name or self.index_name
        if not self.client.has_index(target):
            logger.warning("Индекс %r не найден — удалять нечего.", target)
            return False
        logger.info("Удаляю индекс %r...", target)
        self.client.delete_index(target)
        if target == self.index_name:
            self._client = None
            self._stores.clear()
        return True


@lru_cache(maxsize=1)
def get_vector_store() -> VectorStore:
    """Единый (кэшированный) экземпляр ``VectorStore``."""
    return VectorStore()
