"""Provider 抽象：LLM 与 Embedding 的统一接口与数据类型。

所有 Agent 通过该抽象访问模型能力，便于在 mock 与真实 provider 间切换，
保证实验可复现与无 API Key 可运行。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import numpy as np


@dataclass(frozen=True)
class LLMResponse:
    """LLM 补全结果，含 token 计数（用于通信/计算开销统计）。"""

    text: str
    prompt_tokens: int
    completion_tokens: int
    model: str
    cached: bool = False

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@runtime_checkable
class LLMProvider(Protocol):
    """LLM Provider 接口。"""

    name: str
    model: str

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """根据提示生成补全。"""
        ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Embedding Provider 接口。"""

    name: str
    dim: int

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        """返回形状为 (len(texts), dim) 的 float32 向量矩阵（已 L2 归一化）。"""
        ...


def l2_normalize(matrix: np.ndarray) -> np.ndarray:
    """对每一行做 L2 归一化，便于用内积近似余弦相似度。"""
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (matrix / norms).astype(np.float32)


__all__ = [
    "LLMResponse",
    "LLMProvider",
    "EmbeddingProvider",
    "l2_normalize",
]
