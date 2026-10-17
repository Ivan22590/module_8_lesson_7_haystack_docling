"""Инструмент загрузки веб-страницы по URL и сохранения её в базу знаний."""

from __future__ import annotations

import logging

import requests
from bs4 import BeautifulSoup

from app.constants import HTTP_TIMEOUT_SECONDS, USER_AGENT
from app.ingestion.service import get_ingestion_service

logger = logging.getLogger(__name__)


def fetch_page_text(url: str) -> str:
    """Скачать страницу и извлечь из неё основной текст."""
    response = requests.get(
        url,
        timeout=HTTP_TIMEOUT_SECONDS,
        headers={"User-Agent": USER_AGENT},
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()
    return soup.get_text(separator=" ", strip=True)


def process_url_and_save(url: str) -> str:
    """Загрузить страницу, разбить на чанки и сохранить в базу знаний."""
    if not url.lower().startswith(("http://", "https://")):
        return (
            "Ошибка: некорректный URL. Ожидается ссылка, начинающаяся с "
            "http:// или https://."
        )

    try:
        text = fetch_page_text(url)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ошибка загрузки страницы %s", url)
        return f"Не удалось загрузить страницу {url}: {exc}"

    if len(text) < 50:
        return f"Страница {url} загружена, но содержит слишком мало текста для анализа."

    try:
        saved = get_ingestion_service().ingest_text(text, source=url)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ошибка сохранения в Pinecone")
        return f"Страница {url} распарсена, но не сохранена в базу: {exc}"

    return f"Страница {url} успешно изучена и сохранена в базу знаний ({saved} чанков)."
