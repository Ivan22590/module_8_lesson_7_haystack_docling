"""Базовая утилита сборки инструментов.

Каждый инструмент — обычная функция, обёрнутая в ``haystack.tools.Tool`` с
ручной JSON-схемой. Так мы контролируем, что пользовательские данные вроде
``user_id`` НЕ попадают в схему для LLM — они подставляются замыканием.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from haystack.tools import Tool

logger = logging.getLogger(__name__)

# Пустая JSON-схема для инструментов без аргументов.
NO_ARGS_SCHEMA: dict[str, Any] = {"type": "object", "properties": {}, "required": []}

OnToolCalled = Callable[[str], None] | None


def make_tool(
    name: str,
    description: str,
    parameters: dict[str, Any],
    impl: Callable[..., str],
    on_tool_called: OnToolCalled = None,
) -> Tool:
    """Собрать ``Tool``: при вызове сначала сообщает статус, затем выполняет impl."""

    def wrapped_function(**kwargs: Any) -> str:
        if on_tool_called is not None:
            try:
                on_tool_called(name)
            except Exception:  # noqa: BLE001 — статус не должен ронять инструмент
                logger.exception("Ошибка колбэка статуса для инструмента %s", name)
        return impl(**kwargs)

    return Tool(
        name=name,
        description=description,
        parameters=parameters,
        function=wrapped_function,
    )
