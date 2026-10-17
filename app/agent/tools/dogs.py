"""Инструмент случайного фото собаки с vision-описанием породы через LLM."""

from __future__ import annotations

import logging

import requests
from haystack.dataclasses import ChatMessage, ImageContent

from app.constants import PHOTO_URL_MARKER_PREFIX
from app.llm import get_chat_generator

logger = logging.getLogger(__name__)

_VISION_PROMPT = (
    "На картинке — фотография собаки. 1) Определи породу (или ближайшую "
    "визуально похожую). 2) Кратко расскажи предысторию породы: как и для чего "
    "она была выведена. 3) Дай короткую характеристику: характер, "
    "особенности содержания. Отвечай на русском, 5–8 предложений."
)


def get_random_dog_image() -> str:
    """Случайное фото собаки с dog.ceo + vision-описание породы через LLM."""
    try:
        response = requests.get(
            "https://dog.ceo/api/breeds/image/random", timeout=10
        )
        response.raise_for_status()
        payload = response.json()
        photo_url: str = payload.get("message", "")
        if payload.get("status") != "success" or not photo_url:
            return "Сервис с фотографиями собак не вернул изображение."
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ошибка запроса к dog.ceo")
        return f"Не удалось получить фото собаки: {exc}"

    try:
        image_content = ImageContent.from_url(photo_url, detail="auto")
        message = ChatMessage.from_user(content_parts=[_VISION_PROMPT, image_content])
        description = (
            get_chat_generator().run([message])["replies"][0].text or ""
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ошибка vision-анализа фото %s", photo_url)
        return (
            f"Фото собаки получено ({PHOTO_URL_MARKER_PREFIX} {photo_url}), "
            f"но описать породу не удалось: {exc}"
        )

    return (
        f"Фотография собаки: {photo_url}\n"
        f"{PHOTO_URL_MARKER_PREFIX} {photo_url}\n\n"
        f"Описание:\n{description.strip()}"
    )
