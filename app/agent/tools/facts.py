"""Инструменты со случайными фактами о котиках и собаках (открытые API)."""

from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)


def get_random_cat_fact() -> str:
    """Случайный факт о котиках с catfact.ninja."""
    try:
        response = requests.get("https://catfact.ninja/fact", timeout=10)
        response.raise_for_status()
        fact: str = response.json().get("fact", "")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ошибка запроса к catfact.ninja")
        return f"Не удалось получить факт о котиках: {exc}"
    return (
        f"Факт о котиках: {fact}"
        if fact
        else "Сервис с фактами о котиках не вернул данных."
    )


def get_random_dog_fact() -> str:
    """Случайный факт о собаках с dogapi.dog."""
    try:
        response = requests.get(
            "https://dogapi.dog/api/v2/facts?limit=1", timeout=10
        )
        response.raise_for_status()
        data = response.json().get("data") or []
        fact = (data[0].get("attributes") or {}).get("body", "") if data else ""
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ошибка запроса к dogapi.dog")
        return f"Не удалось получить факт о собаках: {exc}"
    return (
        f"Факт о собаках: {fact}"
        if fact
        else "Сервис с фактами о собаках не вернул данных."
    )
