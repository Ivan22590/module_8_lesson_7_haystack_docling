"""Метаданные чанков, извлечённых из файлов.

Каждый чанк файла обязан нести как минимум название файла и номер чанка/страницы.
Стандартный ``MetaExtractor`` из ``docling-haystack`` уже добавляет ``page_number``
и ``dl_meta``; здесь мы задаём базовый набор «прикладных» метаданных, который
передаётся в конвертер через аргумент ``meta``.
"""

from __future__ import annotations

from typing import Any

from haystack_integrations.components.converters.docling import MetaExtractor

# Значение поля ``source_type`` для контента, загруженного из файла.
FILE_SOURCE_TYPE = "file"


class CleanMetaExtractor(MetaExtractor):
    """Стандартный ``MetaExtractor`` без вложенного поля ``dl_meta``.

    Pinecone поддерживает в метаданных только ``str``, ``int``, ``bool`` и
    ``List[str]``, поэтому словарь ``dl_meta`` всё равно отбрасывается и лишь
    засоряет логи предупреждениями. Оставляем полезное: ``page_number``.
    """

    def extract_chunk_meta(self, chunk: Any) -> dict[str, Any]:
        meta = super().extract_chunk_meta(chunk)
        meta.pop("dl_meta", None)
        return meta

    def extract_dl_doc_meta(self, dl_doc: Any) -> dict[str, Any]:
        meta = super().extract_dl_doc_meta(dl_doc)
        meta.pop("dl_meta", None)
        return meta


def build_file_meta(
    file_name: str,
    chat_id: int,
    *,
    mime_type: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Собрать метаданные файла для передачи в ``DoclingConverter.run(meta=...)``.

    :param file_name: имя загруженного файла (попадает в ``file_name`` и ``source``);
    :param chat_id: идентификатор чата Telegram (``uploaded_by``);
    :param mime_type: MIME-тип файла, если известен;
    :param extra: дополнительные поля.
    """
    meta: dict[str, Any] = {
        "source_type": FILE_SOURCE_TYPE,
        "file_name": file_name,
        # ``source`` используется инструментом поиска для отображения источника.
        "source": file_name,
        "uploaded_by": str(chat_id),
    }
    if mime_type:
        meta["mime_type"] = mime_type
    if extra:
        meta.update(extra)
    return meta
