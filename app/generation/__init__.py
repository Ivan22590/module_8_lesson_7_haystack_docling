"""RAG-генерация: поиск релевантных чанков и ответ LLM, а также резюме по документу."""

from __future__ import annotations

from app.generation.pipeline import (
    build_generation_pipeline,
    get_generation_pipeline,
)
from app.generation.service import answer, one_sentence_summary, retrieve

__all__ = [
    "answer",
    "build_generation_pipeline",
    "get_generation_pipeline",
    "one_sentence_summary",
    "retrieve",
]
