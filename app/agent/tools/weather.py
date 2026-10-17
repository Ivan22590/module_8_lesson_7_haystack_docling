"""Инструмент получения текущей погоды по названию города (Open-Meteo, без ключа)."""

from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)

# Описания погодных кодов Open-Meteo (кратко, на русском).
WEATHER_CODES_RU: dict[int, str] = {
    0: "ясно ☀️",
    1: "преимущественно ясно 🌤",
    2: "переменная облачность ⛅",
    3: "пасмурно ☁️",
    45: "туман 🌫",
    48: "осаждающийся туман 🌫",
    51: "лёгкая морось 🌦",
    53: "морось 🌦",
    55: "сильная морось 🌦",
    56: "лёгкая гололёдная морось 🌧❄️",
    57: "гололёдная морось 🌧❄️",
    61: "небольшой дождь 🌦",
    63: "дождь 🌧",
    65: "сильный дождь 🌧",
    66: "дождь с гололёдом 🌧❄️",
    67: "сильный дождь с гололёдом 🌧❄️",
    71: "небольшой снег 🌨",
    73: "снег ❄️",
    75: "сильный снег ❄️",
    77: "снежные зёрна 🌨",
    80: "лёгкие ливни 🌦",
    81: "ливни 🌧",
    82: "сильные ливни ⛈",
    85: "снежные ливни 🌨",
    86: "сильные снежные ливни ❄️",
    95: "гроза ⛈",
    96: "гроза с градом ⛈",
    99: "сильная гроза с градом ⛈",
}


def get_weather(city: str) -> str:
    """Погода по названию города через бесплатное Open-Meteo (без ключа)."""
    try:
        geo = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "ru", "format": "json"},
            timeout=10,
        )
        geo.raise_for_status()
        results = geo.json().get("results") or []
        if not results:
            return (
                f"Не нашёл город «{city}». Проверьте название "
                "(например: Москва, Казань, London)."
            )
        place = results[0]
        lat, lon = place["latitude"], place["longitude"]
        place_name = place.get("name", city)
        country = place.get("country", "")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ошибка геокодирования %s", city)
        return f"Не удалось найти город «{city}»: {exc}"

    try:
        forecast = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": (
                    "temperature_2m,relative_humidity_2m,apparent_temperature,"
                    "wind_speed_10m,weather_code"
                ),
                "wind_speed_unit": "ms",
            },
            timeout=10,
        )
        forecast.raise_for_status()
        current = forecast.json().get("current") or {}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ошибка запроса погоды для %s", city)
        return f"Не удалось получить погоду для «{place_name}»: {exc}"

    if not current:
        return f"Сервис погоды не вернул данных для «{place_name}»."

    description = WEATHER_CODES_RU.get(int(current.get("weather_code", -1)), "нет данных")
    return (
        f"Погода в {place_name}"
        + (f", {country}" if country else "")
        + " сейчас:\n"
        f"• температура: {current.get('temperature_2m')} °C (ощущается как "
        f"{current.get('apparent_temperature')} °C)\n"
        f"• ветер: {current.get('wind_speed_10m')} м/с\n"
        f"• влажность: {current.get('relative_humidity_2m')} %\n"
        f"• описание: {description}"
    )
