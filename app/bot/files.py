"""Загрузка присланных Telegram-файлов в память (без записи на диск)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from telebot import TeleBot

logger = logging.getLogger(__name__)


class FileTooLargeError(RuntimeError):
    """Файл превышает допустимый размер."""


@dataclass(frozen=True)
class DownloadedFile:
    """Скачанный файл: содержимое, имя и MIME-тип."""

    data: bytes
    file_name: str
    mime_type: str | None


def _resolve_name(document: Any) -> str:
    """Определить имя файла (с расширением, если можно)."""
    name = str(getattr(document, "file_name", "") or "").strip()
    if name:
        return name
    return f"document_{getattr(document, 'file_id', 'unknown')}"


def download_document(
    bot: TeleBot, document: Any, *, max_bytes: int
) -> DownloadedFile:
    """Скачать документ из Telegram в память.

    :raises FileTooLargeError: если размер файла превышает ``max_bytes``.
    """
    size = getattr(document, "file_size", None)
    if isinstance(size, int) and size > max_bytes:
        raise FileTooLargeError(
            f"файл {size} байт превышает лимит {max_bytes} байт"
        )

    file_info = bot.get_file(document.file_id)
    data = bot.download_file(file_info.file_path)
    return DownloadedFile(
        data=data,
        file_name=_resolve_name(document),
        mime_type=getattr(document, "mime_type", None),
    )
