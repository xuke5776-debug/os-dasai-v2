"""可插拔向量检索后端。

默认 numpy 暴力检索（O(N·d)，N 较小时足够），可替换为 hnswlib / faiss（近似最近邻）。
所有向量按 L2 归一化，内积即余弦相似度。
"""

from __future__ import annotations

from typing import Protocol

import numpy as np

from agent_runtime.providers.base import l2_normalize


class VectorIndex(Protocol):
    name: str

    def add(self, key: str, vector: np.ndarray) -> None: ...
    def remove(self, key: str) -> None: ...
    def search(self, vector: np.ndarray, top_k: int) -> list[tuple[str, float]]: ...
    def __len__(self) -> int: ...


class NumpyVectorIndex:
    """numpy 暴力向量索引。"""

    name = "numpy"

    def __init__(self) -> None:
        self._keys: list[str] = []
        self._vectors: dict[str, np.ndarray] = {}

    def add(self, key: str, vector: np.ndarray) -> None:
        vec = l2_normalize(np.asarray(vector, dtype=np.float32).reshape(1, -1))[0]
        if key not in self._vectors:
            self._keys.append(key)
        self._vectors[key] = vec

    def remove(self, key: str) -> None:
        if key in self._vectors:
            del self._vectors[key]
            self._keys.remove(key)

    def search(self, vector: np.ndarray, top_k: int) -> list[tuple[str, float]]:
        if not self._vectors:
            return []
        query = l2_normalize(np.asarray(vector, dtype=np.float32).reshape(1, -1))[0]
        keys = list(self._vectors.keys())
        matrix = np.vstack([self._vectors[k] for k in keys])
        scores = matrix @ query
        order = np.argsort(-scores)[:top_k]
        return [(keys[i], float(scores[i])) for i in order]

    def __len__(self) -> int:
        return len(self._vectors)


def build_vector_index(backend: str = "numpy", dim: int = 256) -> VectorIndex:
    """构造向量索引；重后端不可用时回退 numpy。"""
    backend = backend.lower()
    if backend == "hnswlib":
        try:
            from agent_runtime.memory.hnsw_backend import HnswVectorIndex

            return HnswVectorIndex(dim=dim)
        except Exception:  # noqa: BLE001
            return NumpyVectorIndex()
    if backend == "faiss":
        try:
            from agent_runtime.memory.faiss_backend import FaissVectorIndex

            return FaissVectorIndex(dim=dim)
        except Exception:  # noqa: BLE001
            return NumpyVectorIndex()
    return NumpyVectorIndex()


__all__ = ["VectorIndex", "NumpyVectorIndex", "build_vector_index"]
