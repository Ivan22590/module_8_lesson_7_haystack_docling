"""Конфигурация приложения: переменные окружения и настройки.

Единственное место, где читается ``.env``. Все остальные модули получают
настройки через :func:`get_settings` (кэшируется, поэтому файл читается один
раз за процесс).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# Корень проекта: /app/config.py -> /app -> корень проекта.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


class ConfigError(RuntimeError):
    """Ошибка конфигурации: отсутствует обязательная переменная окружения."""


@dataclass(frozen=True)
class Settings:
    """Неизменяемый снимок настроек приложения."""

    # --- LLM (OpenAI-совместимый провайдер, например ProxyAPI) -------------
    # Внимание: ProxyAPI требует имена моделей с префиксом ("openai/gpt-4o-mini").
    openai_api_key: str
    openai_base_url: str
    openai_model: str

    # --- Эмбеддинги (имя тоже может быть с префиксом провайдера) -----------
    embedding_model: str
    embedding_dim: int

    # --- Pinecone ----------------------------------------------------------
    pinecone_api_key: str
    pinecone_index_name: str
    pinecone_region: str
    pinecone_cloud: str

    # --- Telegram (валидируется отдельно — нужен только для бота) ----------
    telegram_token: str | None

    # --- RAG / история -----------------------------------------------------
    chunk_size: int
    chunk_overlap: int
    max_search_results: int
    max_history: int
    max_context_documents: int
    max_agent_steps: int

    # --- Namespaces в Pinecone --------------------------------------------
    namespace_knowledge: str
    namespace_user_memories: str
    namespace_dialog_context: str

    # --- Обработка файлов через Docling -----------------------------------
    max_file_size_mb: int
    summary_max_sentences: int
    docling_export_type: str

    # --- Умная память (фильтрация дубликатов) -----------------------------
    cosine_similarity_threshold: float
    duplicate_action: str
    dedupe_enabled: bool

    @property
    def max_file_size_bytes(self) -> int:
        """Максимальный размер принимаемого файла в байтах."""
        return self.max_file_size_mb * 1024 * 1024

    def require_telegram_token(self) -> str:
        """Вернуть телеграм-токен или выбросить понятную ошибку."""
        if not self.telegram_token:
            raise ConfigError(
                "Переменная окружения TELEGRAM_TOKEN не задана. "
                "Заполните её в файле .env (см. .env.example)."
            )
        return self.telegram_token


def _require(name: str) -> str:
    """Прочитать обязательную переменную окружения."""
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigError(
            f"Переменная окружения {name} не задана. "
            "Скопируйте .env.example в .env и заполните значения."
        )
    return value


def _optional(name: str, default: str) -> str:
    """Прочитать необязательную переменную окружения."""
    return os.getenv(name, "").strip() or default


def _optional_int(name: str, default: int) -> int:
    """Прочитать необязательную целочисленную переменную окружения."""
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"Переменная {name}={raw!r} должна быть целым числом.") from exc


def _optional_float(name: str, default: float) -> float:
    """Прочитать необязательную переменную окружения с плавающей точкой."""
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigError(f"Переменная {name}={raw!r} должна быть числом.") from exc


def _optional_bool(name: str, default: bool) -> bool:
    """Прочитать необязательную булеву переменную окружения."""
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on", "да"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Загрузить настройки (кэшируется; повторный вызов не читает .env заново)."""
    return Settings(
        openai_api_key=_require("OPENAI_API_KEY"),
        openai_base_url=_optional("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        openai_model=_optional("OPENAI_MODEL", "gpt-4o-mini"),
        embedding_model=_optional("EMBEDDING_MODEL", "text-embedding-3-small"),
        embedding_dim=_optional_int("EMBEDDING_DIM", 1536),
        pinecone_api_key=_require("PINECONE_API_KEY"),
        pinecone_index_name=_require("PINECONE_INDEX_NAME"),
        pinecone_region=_optional("PINECONE_REGION", "us-east-1"),
        pinecone_cloud=_optional("PINECONE_CLOUD", "aws"),
        telegram_token=os.getenv("TELEGRAM_TOKEN", "").strip() or None,
        chunk_size=_optional_int("CHUNK_SIZE", 1000),
        chunk_overlap=_optional_int("CHUNK_OVERLAP", 200),
        max_search_results=_optional_int("MAX_SEARCH_RESULTS", 4),
        max_history=_optional_int("MAX_HISTORY", 20),
        max_context_documents=_optional_int("MAX_CONTEXT_DOCUMENTS", 5),
        max_agent_steps=_optional_int("MAX_AGENT_STEPS", 8),
        namespace_knowledge=_optional("NAMESPACE_KNOWLEDGE", "knowledge"),
        namespace_user_memories=_optional("NAMESPACE_USER_MEMORIES", "user_memories"),
        namespace_dialog_context=_optional(
            "NAMESPACE_DIALOG_CONTEXT", "dialog_context"
        ),
        max_file_size_mb=_optional_int("MAX_FILE_SIZE_MB", 20),
        summary_max_sentences=_optional_int("SUMMARY_MAX_SENTENCES", 1),
        docling_export_type=_optional("DOCLING_EXPORT_TYPE", "doc_chunks").lower(),
        cosine_similarity_threshold=_optional_float(
            "COSINE_SIMILARITY_THRESHOLD", 0.75
        ),
        duplicate_action=_optional("DUPLICATE_ACTION", "update").lower(),
        dedupe_enabled=_optional_bool("DEDUPE_ENABLED", True),
    )
