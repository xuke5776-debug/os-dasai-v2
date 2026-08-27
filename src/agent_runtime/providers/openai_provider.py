"""OpenAI 兼容 Provider（可选）。

仅在配置 provider=openai 且安装了 openai 包时使用。延迟导入以避免
默认 mock-first 路径产生额外依赖。
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from agent_runtime.providers.base import LLMResponse, l2_normalize
from agent_runtime.providers.tokenizer import get_tokenizer


class OpenAILLM:
    """通过 OpenAI 兼容接口访问真实 LLM。"""

    name = "openai-llm"

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: str = "",
        base_url: str = "https://api.openai.com/v1",
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> None:
        from openai import OpenAI  # 延迟导入

        if not api_key:
            raise ValueError("OpenAI provider 需要 api_key（见 .env AGENT_LLM_API_KEY）")
        self.model = model
        self._default_temperature = temperature
        self._default_max_tokens = max_tokens
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._tok = get_tokenizer(prefer_tiktoken=True, model=model)

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self._default_temperature if temperature is None else temperature,
            max_tokens=self._default_max_tokens if max_tokens is None else max_tokens,
        )
        text = resp.choices[0].message.content or ""
        usage = resp.usage
        if usage is not None:
            prompt_tokens = usage.prompt_tokens
            completion_tokens = usage.completion_tokens
        else:
            prompt_tokens = self._tok.count(f"{system or ''}\n{prompt}")
            completion_tokens = self._tok.count(text)
        return LLMResponse(
            text=text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model=self.model,
        )


class OpenAIEmbedding:
    """通过 OpenAI 兼容接口访问真实 embedding。"""

    name = "openai-embedding"

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        api_key: str = "",
        base_url: str = "https://api.openai.com/v1",
        dim: int = 1536,
    ) -> None:
        from openai import OpenAI  # 延迟导入

        if not api_key:
            raise ValueError("OpenAI embedding 需要 api_key")
        self.model = model
        self.dim = dim
        self._client = OpenAI(api_key=api_key, base_url=base_url)

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        resp = self._client.embeddings.create(model=self.model, input=list(texts))
        matrix = np.array([d.embedding for d in resp.data], dtype=np.float32)
        self.dim = matrix.shape[1]
        return l2_normalize(matrix)


__all__ = ["OpenAILLM", "OpenAIEmbedding"]
