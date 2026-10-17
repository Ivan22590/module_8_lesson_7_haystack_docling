"""Приём файлов: анализ через Docling и загрузка структурированного контента в Pinecone."""

from __future__ import annotations

from app.ingestion.converter import get_docling_converter, warm_up_docling
from app.ingestion.metadata import build_file_meta
from app.ingestion.pipeline import build_ingestion_pipeline, get_ingestion_pipeline
from app.ingestion.service import IngestionReport, IngestionService, get_ingestion_service

__all__ = [
    "IngestionReport",
    "IngestionService",
    "build_file_meta",
    "build_ingestion_pipeline",
    "get_docling_converter",
    "get_ingestion_pipeline",
    "get_ingestion_service",
    "warm_up_docling",
]
