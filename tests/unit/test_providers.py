"""Provider 单元测试：确定性与 embedding 性质。"""

from __future__ import annotations

import numpy as np

from agent_runtime.providers.mock import MockEmbedding, MockLLM
from agent_runtime.providers.tokenizer import HeuristicTokenizer


def test_mock_llm_is_deterministic():
    llm = MockLLM(seed=42)
    r1 = llm.complete("hello world", system="sys")
    r2 = llm.complete("hello world", system="sys")
    assert r1.text == r2.text
    assert r1.total_tokens == r2.total_tokens > 0


def test_mock_llm_respects_max_tokens():
    llm = MockLLM(seed=1)
    r_small = llm.complete("a prompt", max_tokens=4)
    r_big = llm.complete("a prompt", max_tokens=64)
    # 更小的 max_tokens 应产出不多于更大配置的补全长度（确定性）。
    assert 0 < r_small.completion_tokens <= r_big.completion_tokens


def test_mock_embedding_shape_and_norm():
    emb = MockEmbedding(dim=64, seed=7)
    m = emb.embed(["fix async resource leak", "another text"])
    assert m.shape == (2, 64)
    norms = np.linalg.norm(m, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-5)


def test_mock_embedding_similarity_ordering():
    emb = MockEmbedding(dim=256, seed=7)
    m = emb.embed(
        [
            "fix async resource leak in test",
            "fix async resource leak in module",
            "completely unrelated cooking recipe",
        ]
    )
    sim_related = float(m[0] @ m[1])
    sim_unrelated = float(m[0] @ m[2])
    assert sim_related > sim_unrelated


def test_heuristic_tokenizer_counts():
    tok = HeuristicTokenizer()
    assert tok.count("") == 0
    assert tok.count("hello, world") >= 2
    # CJK 单字计数
    assert tok.count("你好") == 2
