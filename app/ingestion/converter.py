"""Фабрика конвертера Docling для Haystack.

``DoclingConverter`` локально разбирает PDF, DOCX, PPTX, XLSX, HTML и др. и
возвращает либо отдельные чанки (``DOC_CHUNKS``), либо целый документ в
Markdown (``MARKDOWN``). Режим задаётся ``DOCLING_EXPORT_TYPE``.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from haystack_integrations.components.converters.docling import (
    DoclingConverter,
    ExportType,
)

from app.config import get_settings
from app.ingestion.metadata import CleanMetaExtractor

logger = logging.getLogger(__name__)


def _resolve_export_type() -> ExportType:
    """Определить режим экспорта Docling из настроек."""
    value = get_settings().docling_export_type
    try:
        return ExportType(value)
    except ValueError:
        logger.warning(
            "Неизвестный DOCLING_EXPORT_TYPE=%r — использую 'doc_chunks'.", value
        )
        return ExportType.DOC_CHUNKS


@lru_cache(maxsize=1)
def get_docling_converter() -> DoclingConverter:
    """Единый (кэшированный) конвертер Docling."""
    return DoclingConverter(
        export_type=_resolve_export_type(),
        md_export_kwargs={"image_placeholder": ""},
        meta_extractor=CleanMetaExtractor(),
    )


def warm_up_docling() -> bool:
    """Прогреть конвертер (скачивание токенизатора чанкера).

    Полноценные модели layout/table подтягиваются Hugging Face при первом
    реальном преобразовании файла. Ошибки прогрева не должны ломать старт бота.
    """
    try:
        get_docling_converter().warm_up()
        logger.info("DoclingConverter прогрет")
        return True
    except Exception:  # noqa: BLE001 — прогрев не обязателен для старта
        logger.exception("Не удалось прогреть DoclingConverter (обработается при первом файле)")
        return False
