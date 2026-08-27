"""根据配置构造 LLM / Embedding Provider。"""

from __future__ import annotations

from agent_runtime.config import Config
from agent_runtime.providers.base import EmbeddingProvider, LLMProvider
from agent_runtime.providers.mock import MockEmbedding, MockLLM


def build_llm(config: Config) -> LLMProvider:
    """按配置返回 LLM provider；未知或缺依赖时回退 mock。"""
    provider = config.llm.provider.lower()
    if provider == "openai":
        from agent_runtime.providers.openai_provider import OpenAILLM

        return OpenAILLM(
            model=config.llm.model,
            api_key=config.llm.api_key,
            base_url=config.llm.base_url,
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens,
        )
    return MockLLM(model=config.llm.model or "mock-llm", seed=config.random_seed)


def build_embedding(config: Config) -> EmbeddingProvider:
    """按配置返回 embedding provider；未知或缺依赖时回退 mock。"""
    provider = config.embedding.provider.lower()
    if provider == "openai":
        from agent_runtime.providers.openai_provider import OpenAIEmbedding

        return OpenAIEmbedding(
            model=config.embedding.model,
            api_key=config.llm.api_key,
            base_url=config.llm.base_url,
            dim=config.embedding.dim,
        )
    if provider in ("sentence-transformers", "st"):
        try:
            from agent_runtime.providers.st_provider import SentenceTransformerEmbedding

            return SentenceTransformerEmbedding(model=config.embedding.model)
        except Exception:  # noqa: BLE001 - 缺依赖回退 mock
            return MockEmbedding(dim=config.embedding.dim, seed=config.random_seed)
    return MockEmbedding(dim=config.embedding.dim, seed=config.random_seed)


__all__ = ["build_llm", "build_embedding"]
