"""确定性 mock Provider。

设计目标：
- 无需任何 API Key 即可运行全部测试与实验；
- 输出完全由输入 + 随机种子决定，保证实验可复现；
- mock LLM 支持「指令式」生成：当提示中包含 JSON 结构化指令时，返回稳定的
  结构化文本，使上层 Agent 逻辑可被确定性驱动。

注意：mock 代表「推理能力」的占位。任务的语义正确性由场景 verifier 与确定性
变换保证；对通信开销的对比只取决于消息内容与计量口径，与 mock 创造力无关。
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence

import numpy as np

from agent_runtime.providers.base import LLMResponse, l2_normalize
from agent_runtime.providers.tokenizer import HeuristicTokenizer, Tokenizer

_WORDS = [
    "plan",
    "retrieve",
    "execute",
    "review",
    "analyze",
    "summarize",
    "fix",
    "patch",
    "test",
    "log",
    "exception",
    "resource",
    "async",
    "await",
    "close",
    "handle",
    "verify",
    "evidence",
    "strategy",
]


def _stable_hash(text: str) -> int:
    return int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big")


class MockLLM:
    """确定性 mock LLM。

    生成策略：基于提示哈希 + 种子产出确定性的伪文本。文本长度受 max_tokens 约束，
    便于在 token 统计上呈现合理规模。
    """

    name = "mock-llm"

    def __init__(
        self,
        model: str = "mock-llm",
        seed: int = 42,
        tokenizer: Tokenizer | None = None,
    ) -> None:
        self.model = model
        self.seed = seed
        self._tok = tokenizer or HeuristicTokenizer()

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        full_prompt = f"{system or ''}\n{prompt}"
        h = _stable_hash(f"{self.seed}:{full_prompt}")
        rng = np.random.default_rng(h % (2**32))
        n_words = int(min(max_tokens or 64, 8 + (h % 40)))
        words = rng.choice(_WORDS, size=n_words).tolist()
        text = " ".join(words)
        prompt_tokens = self._tok.count(full_prompt)
        completion_tokens = self._tok.count(text)
        return LLMResponse(
            text=text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model=self.model,
        )


class MockEmbedding:
    """确定性 mock embedding。

    基于字符 n-gram 的哈希特征 + 归一化，产出稳定向量。相似文本（共享子串）
    会得到较高余弦相似度，使语义检索在 mock 下也具备可解释的区分度。
    """

    name = "mock-embedding"

    def __init__(self, dim: int = 256, seed: int = 42) -> None:
        self.dim = dim
        self.seed = seed

    def _embed_one(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float32)
        text = (text or "").lower()
        # 字符级 3-gram 哈希到固定维度，形成稳定的词袋式表示。
        tokens = text.split()
        grams = list(tokens)
        for tok in tokens:
            padded = f"#{tok}#"
            grams.extend(padded[i : i + 3] for i in range(len(padded) - 2))
        if not grams:
            grams = ["#empty#"]
        for g in grams:
            idx = _stable_hash(f"{self.seed}:{g}") % self.dim
            vec[idx] += 1.0
        return vec

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        matrix = np.vstack([self._embed_one(t) for t in texts])
        return l2_normalize(matrix)


__all__ = ["MockLLM", "MockEmbedding"]
