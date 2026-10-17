"""Умная фильтрация дубликатов по косинусному сходству.

Модуль содержит чистую математику и правила принятия решения, без обращений к
сети/Pinecone — это упрощает тестирование и переиспользование.

Правила:

- ``similarity <  порога`` — новая информация → ``created``;
- ``similarity >= порога`` — дубликат/вариация → ``DUPLICATE_ACTION``
  (``update`` перезаписывает слот, ``skip`` пропускает запись).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

from app.config import get_settings


@dataclass(frozen=True)
class MemoryWriteResult:
    """Результат записи в векторную базу."""

    action: str      # "created" | "updated" | "skipped"
    similarity: float
    id: str | None
    text: str


@dataclass(frozen=True)
class DuplicateCandidate:
    """Лучший кандидат на дубликат в векторном хранилище."""

    id: str | None
    similarity: float
    text: str | None

    @property
    def found(self) -> bool:
        """Найден ли хотя бы один похожий фрагмент."""
        return self.id is not None


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """Косинусное сходство двух векторов (0..1 для неотрицательных)."""
    if len(a) != len(b):
        raise ValueError(f"Размерности векторов различаются: {len(a)} != {len(b)}")
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


@dataclass(frozen=True)
class DedupePolicy:
    """Правила дедупликации: порог, действие и общий выключатель."""

    threshold: float
    action: str
    enabled: bool

    @classmethod
    def from_settings(cls) -> "DedupePolicy":
        """Собрать политику из настроек приложения."""
        settings = get_settings()
        return cls(
            threshold=settings.cosine_similarity_threshold,
            action=settings.duplicate_action,
            enabled=settings.dedupe_enabled,
        )

    def is_duplicate(self, candidate: DuplicateCandidate, threshold: float | None = None) -> bool:
        """Считать ли кандидата дубликатом по текущим правилам."""
        effective = self.threshold if threshold is None else threshold
        return self.enabled and candidate.found and candidate.similarity >= effective

    def resolve_action(self, action: str | None = None) -> str:
        """Определить действие для найденного дубликата (``update``/``skip``)."""
        effective = (action or self.action).lower()
        return effective if effective in {"update", "skip"} else "skip"
