"""Общие константы приложения, разделяемые несколькими слоями.

Вынесены отдельно, чтобы не было циклических импортов между ``agent``,
``bot`` и инструментами.
"""

from __future__ import annotations

# Лимит одного сообщения Telegram (символов).
TELEGRAM_MESSAGE_LIMIT = 4096

# Текст, когда у пользователя вообще нет ни имени, ни юзернейма.
FALLBACK_USER_NAME = "друг"

# Маркер в результате инструмента ``get_random_dog_image``: ``bot`` вытаскивает
# из него URL фотографии, чтобы отправить её отдельным сообщением.
PHOTO_URL_MARKER_PREFIX = "URL фото:"

# Сетевые настройки для инструментов (загрузка страниц и открытые API).
HTTP_TIMEOUT_SECONDS = 20
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
