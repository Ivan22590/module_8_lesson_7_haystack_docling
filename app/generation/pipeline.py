"""Generation-пайплайн Haystack: retriever → prompt → LLM.

    embedder (OpenAITextEmbedder) -> retriever (PineconeEmbeddingRetriever)
        -> prompt (PromptBuilder) -> llm (OpenAIChatGenerator)

Вход пайплайна: ``{"embedder": {"text": query}, "prompt": {"query": query}}``.
"""

from __future__ import annotations

from functools import lru_cache

from haystack import Pipeline
from haystack.components.builders import PromptBuilder
from haystack_integrations.components.retrievers.pinecone import PineconeEmbeddingRetriever

from app.config import get_settings
from app.llm import get_chat_generator, get_text_embedder
from app.vectorstore.store import get_vector_store

EMBEDDER = "embedder"
RETRIEVER = "retriever"
PROMPT = "prompt"
LLM = "llm"

# Шаблон ответа: LLM отвечает только по найденному контексту.
PROMPT_TEMPLATE = """\
Ответь на вопрос пользователя, опираясь ТОЛЬКО на приведённый ниже контекст.
Если в контексте нет ответа — честно скажи, что данных не нашлось, и не выдумывай.
Отвечай на языке пользователя, кратко и по делу.

Контекст:
{% for document in documents %}
- {{ document.content }}
{% endfor %}

Вопрос: {{ query }}
"""


def build_generation_pipeline(namespace: str | None = None) -> Pipeline:
    """Собрать RAG-пайплайн генерации ответов по заданному namespace."""
    settings = get_settings()
    ns = namespace or settings.namespace_knowledge

    pipeline = Pipeline()
    pipeline.add_component(EMBEDDER, get_text_embedder())
    pipeline.add_component(
        RETRIEVER,
        PineconeEmbeddingRetriever(
            document_store=get_vector_store().store(ns),
            top_k=settings.max_search_results,
        ),
    )
    pipeline.add_component(PROMPT, PromptBuilder(template=PROMPT_TEMPLATE))
    pipeline.add_component(LLM, get_chat_generator())
    pipeline.connect(f"{EMBEDDER}.embedding", f"{RETRIEVER}.query_embedding")
    pipeline.connect(f"{RETRIEVER}.documents", f"{PROMPT}.documents")
    pipeline.connect(f"{PROMPT}.prompt", f"{LLM}.messages")
    return pipeline


@lru_cache(maxsize=1)
def get_generation_pipeline() -> Pipeline:
    """Единый (кэшированный) generation-пайплайн по базе знаний."""
    return build_generation_pipeline()
