"""Фабрика инструментов агента, привязанных к конкретному чату.

``user_id`` (chat_id) замыкается внутрь инструментов и НЕ попадает в JSON-схему
для LLM. ``on_tool_called`` вызывается при каждом обращении к инструменту.
"""

from __future__ import annotations

from haystack.tools import Tool

from app.agent.tools.base import NO_ARGS_SCHEMA, OnToolCalled, make_tool
from app.agent.tools.dogs import get_random_dog_image
from app.agent.tools.facts import get_random_cat_fact, get_random_dog_fact
from app.agent.tools.knowledge import search_knowledge_base
from app.agent.tools.url import process_url_and_save
from app.agent.tools.user_memory import save_user_memory
from app.agent.tools.weather import get_weather

__all__ = ["create_agent_tools"]


def create_agent_tools(
    user_id: str | None, on_tool_called: OnToolCalled = None
) -> list[Tool]:
    """Создать список Haystack ``Tool`` с привязкой к чату (``user_id``, статусы)."""
    return [
        make_tool(
            name="search_knowledge_base",
            description=(
                "Семантический поиск по базе знаний, личной памяти пользователя "
                "и прошлым диалогам с ним, включая загруженные пользователем "
                "файлы (PDF, DOCX и др.). Используй, когда нужно вспомнить "
                "сохранённые статьи/документы, личные факты о собеседнике (имя, "
                "город, предпочтения) или то, что обсуждали раньше."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Поисковый запрос по смыслу (на русском или языке "
                            "пользователя)."
                        ),
                    }
                },
                "required": ["query"],
            },
            impl=lambda query: search_knowledge_base(query, user_id),
            on_tool_called=on_tool_called,
        ),
        make_tool(
            name="process_url_and_save",
            description=(
                "Загрузить веб-страницу по URL, разбить на фрагменты и сохранить "
                "в базу знаний. Используй, когда пользователь прислал ссылку и "
                "попросил изучить её содержимое или запомнить/сохранить её."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": (
                            "Полный URL страницы, начинающийся с http:// или "
                            "https://."
                        ),
                    }
                },
                "required": ["url"],
            },
            impl=lambda url: process_url_and_save(url),
            on_tool_called=on_tool_called,
        ),
        make_tool(
            name="get_random_cat_fact",
            description=(
                "Получить случайный факт о котиках из открытого API catfact.ninja. "
                "Используй, когда пользователь просит рассказать что-нибудь "
                "интересное о котиках/кошках."
            ),
            parameters=NO_ARGS_SCHEMA,
            impl=lambda: get_random_cat_fact(),
            on_tool_called=on_tool_called,
        ),
        make_tool(
            name="get_random_dog_fact",
            description=(
                "Получить случайный факт о собаках из открытого API dogapi.dog. "
                "Используй, когда пользователь просит рассказать что-нибудь "
                "интересное о собаках."
            ),
            parameters=NO_ARGS_SCHEMA,
            impl=lambda: get_random_dog_fact(),
            on_tool_called=on_tool_called,
        ),
        make_tool(
            name="get_random_dog_image",
            description=(
                "Получить случайную фотографию собаки из открытого API dog.ceo, "
                "определить по фото породу и рассказать о ней (предыстория, "
                "характер). Результат содержит URL фото — сообщи пользователю "
                "породу и сведения, фото бот отправит сам."
            ),
            parameters=NO_ARGS_SCHEMA,
            impl=lambda: get_random_dog_image(),
            on_tool_called=on_tool_called,
        ),
        make_tool(
            name="get_weather",
            description=(
                "Получить текущую погоду в конкретном городе (температура, ветер, "
                "влажность, описание). Используй, когда пользователь спрашивает о "
                "погоде в городе."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": (
                            "Название города на русском или английском "
                            "(например: Москва, Санкт-Петербург, London)."
                        ),
                    }
                },
                "required": ["city"],
            },
            impl=lambda city: get_weather(city),
            on_tool_called=on_tool_called,
        ),
        make_tool(
            name="save_user_memory",
            description=(
                "Сохранить важный личный факт о пользователе в долговременную "
                "память. Используй, когда в диалоге появляется важная информация "
                "о собеседнике: имя, город, работа, увлечения, предпочтения, "
                "важные даты, цели, планы и мечты. Не сохраняй служебные и "
                "статусные сообщения."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "fact": {
                        "type": "string",
                        "description": (
                            "Краткий факт о пользователе одним предложением, "
                            "например: «Живёт в Казани»."
                        ),
                    }
                },
                "required": ["fact"],
            },
            impl=lambda fact: save_user_memory(fact, user_id),
            on_tool_called=on_tool_called,
        ),
    ]
