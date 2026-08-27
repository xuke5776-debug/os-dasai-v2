"""LLM / embedding Provider 抽象与实现（mock-first + OpenAI 兼容）。"""

from __future__ import annotations

from agent_runtime.providers.base import (
    EmbeddingProvider,
    LLMProvider,
    LLMResponse,
    l2_normalize,
)
from agent_runtime.providers.factory import build_embedding, build_llm
from agent_runtime.providers.mock import MockEmbedding, MockLLM
from agent_runtime.providers.tokenizer import (
    HeuristicTokenizer,
    count_chars,
    get_tokenizer,
)

__all__ = [
    "EmbeddingProvider",
    "LLMProvider",
    "LLMResponse",
    "l2_normalize",
    "build_embedding",
    "build_llm",
    "MockEmbedding",
    "MockLLM",
    "HeuristicTokenizer",
    "count_chars",
    "get_tokenizer",
]
