"""Runner Haystack-агента: история диалога, контекст из памяти, запуск.

Haystack ``Agent`` — лёгкий объект, собирается на каждый запрос: инструменты
привязываются к чату замыканиями (``user_id``, колбэк статусов), а долгосрочный
контекст подтягивается из Pinecone перед запуском.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Callable

from haystack.components.agents import Agent
from haystack.dataclasses import ChatMessage
from haystack.tools import Tool

from app.agent.prompt import SYSTEM_PROMPT, identity_line
from app.agent.tools import create_agent_tools
from app.config import get_settings
from app.constants import PHOTO_URL_MARKER_PREFIX
from app.llm import get_chat_generator
from app.vectorstore.search import get_repository

logger = logging.getLogger(__name__)

StatusCallback = Callable[[str], None]


@dataclass
class AgentResult:
    """Результат запуска агента: текст ответа + extra-данные для бота."""

    text: str
    photo_url: str | None = None
    tools_used: list[str] = field(default_factory=list)


# Регулярка для извлечения URL фото собаки из результата get_random_dog_image.
_PHOTO_URL_RE = re.compile(re.escape(PHOTO_URL_MARKER_PREFIX) + r"\s*(\S+)")

# История переписки по чатам: chat_id → список ChatMessage (user/assistant).
# Хранится в памяти процесса; долгосрочный контекст дублируется в Pinecone.
_histories: dict[int, list[ChatMessage]] = {}


def reset_chat(chat_id: int) -> None:
    """Очистить историю переписки чата."""
    _histories.pop(chat_id, None)


def _build_context_block(chat_id: int, user_text: str) -> str | None:
    """Вытянуть из Pinecone релевантный контекст (память + прошлые диалоги).

    Возвращает строку для служебного сообщения перед сообщением пользователя
    или None, если ничего релевантного не найдено.
    """
    settings = get_settings()
    user_filter = {"field": "user_id", "operator": "==", "value": str(chat_id)}
    repository = get_repository()
    lines: list[str] = []

    try:
        memories = repository.search_by_text(
            user_text,
            namespace=settings.namespace_user_memories,
            k=settings.max_context_documents,
            filter=user_filter,
        )
        if memories:
            lines.append("Факты о пользователе:")
            lines.extend(f"- {doc.content}" for doc in memories)
    except Exception:  # noqa: BLE001 — контекст не должен ломать диалог
        logger.exception("Не удалось получить память пользователя")

    try:
        dialog = repository.search_by_text(
            user_text,
            namespace=settings.namespace_dialog_context,
            k=settings.max_context_documents,
            filter=user_filter,
        )
        if dialog:
            lines.append("Прошлые сообщения пользователя по этой теме:")
            lines.extend(f"- {doc.content}" for doc in dialog)
    except Exception:  # noqa: BLE001
        logger.exception("Не удалось получить контекст диалога")

    if not lines:
        return None
    return "\n".join(lines)


def _trim_history(messages: list[ChatMessage]) -> list[ChatMessage]:
    """Ограничить историю диалога, чтобы не раздувать контекст модели."""
    settings = get_settings()
    max_messages = settings.max_history * 2
    if len(messages) <= max_messages:
        return messages
    kept = messages[-max_messages:]
    while kept and kept[0].role.name.lower() != "user":
        kept = kept[1:]
    return kept


def run_agent(
    chat_id: int,
    user_text: str,
    user_name: str | None = None,
    on_tool_called: StatusCallback | None = None,
) -> AgentResult:
    """Прогнать сообщение пользователя через агента и вернуть ``AgentResult``.

    - История переписки хранится в памяти по ``chat_id`` (плюс долгосрочный
      контекст из Pinecone).
    - ``user_name`` попадает в системный промпт.
    - Инструменты создаются под конкретный чат: ``user_id`` замыкается внутрь,
      ``on_tool_called`` срабатывает при каждом обращении к инструменту
      (бот показывает статус «Думаю… / Читаю статью…»).
    """
    settings = get_settings()
    tools_used: list[str] = []
    captured: dict[str, str | None] = {"photo_url": None}

    def track_tool(name: str) -> None:
        if name not in tools_used:
            tools_used.append(name)
        if on_tool_called is not None:
            try:
                on_tool_called(name)
            except Exception:  # noqa: BLE001
                logger.exception("Ошибка колбэка статуса для инструмента %s", name)

    def bind_tool(tool: Tool) -> Tool:
        """Обёртка инструмента: трекинг статуса + захват URL фото собаки."""
        base_function = tool.function

        def invoke_and_capture(**kwargs):
            track_tool(tool.name)
            result = base_function(**kwargs)
            match = _PHOTO_URL_RE.search(str(result))
            if match:
                captured["photo_url"] = match.group(1)
            return result

        return Tool(
            name=tool.name,
            description=tool.description,
            parameters=tool.parameters,
            function=invoke_and_capture,
        )

    system_prompt = f"{SYSTEM_PROMPT}\n\n{identity_line(user_name)}"
    history = _trim_history(_histories.get(chat_id, []))

    messages: list[ChatMessage] = []
    context_block = _build_context_block(chat_id, user_text)
    if context_block:
        messages.append(
            ChatMessage.from_system(
                f"[Контекст из памяти]\n{context_block}\n"
                "[Конец контекста — далее текущее сообщение пользователя.]"
            )
        )

    messages.extend(history)
    user_message = ChatMessage.from_user(user_text)
    messages.append(user_message)

    agent = Agent(
        chat_generator=get_chat_generator(),
        tools=[bind_tool(tool) for tool in create_agent_tools(user_id=str(chat_id))],
        system_prompt=system_prompt,
        max_agent_steps=settings.max_agent_steps,
        exit_conditions=["text"],
    )

    try:
        result = agent.run(messages=messages)
    except Exception:
        logger.exception("Ошибка запуска агента в чате %s", chat_id)
        raise

    last_message = result.get("last_message")
    answer = (last_message.text or "").strip() if last_message else ""
    if not answer:
        answer = "Не удалось получить ответ от модели. Попробуйте переформулировать запрос."

    # Обновляем историю: только пары user→assistant (без служебных сообщений).
    history.extend([user_message, ChatMessage.from_assistant(answer)])
    _histories[chat_id] = _trim_history(history)

    return AgentResult(
        text=answer,
        photo_url=captured["photo_url"],
        tools_used=tools_used,
    )
