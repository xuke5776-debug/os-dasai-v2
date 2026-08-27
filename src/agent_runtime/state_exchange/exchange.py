"""非文本中间状态交换。

在 Agent 间直接交换非文本中间表示，减少「内部状态—文本—内部状态」的反复编解码：

- **embedding / 语义向量**：由 embedding provider 生成，用于语义检索与路由；
- **compact state vector**：对计划/进度的紧凑数值特征，用于接收方决策；
- **plan DAG**：结构化计划图，接收方据此调度与解析。

状态以内容寻址方式存储，消息仅携带 `state://` / `vector://` 引用。大向量经
`SharedVectorBuffer`（可选共享内存）传输。接收方**真实消费**这些状态：检索 Agent
用 plan embedding 排序检索目标、用 DAG 还原 operands，而非重新解析文本。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

import numpy as np

from agent_runtime.providers.base import EmbeddingProvider
from agent_runtime.runtime.errors import ReferenceError_
from agent_runtime.state_exchange.shared_buffer import SharedVectorBuffer


@dataclass(frozen=True)
class StateRef:
    """非文本状态引用。"""

    uri: str
    kind: str  # "plan" | "embedding" | "vector"
    shape: tuple
    dtype: str
    summary: str
    content_hash: str
    nbytes: int
    transport: str  # "shm" | "inproc"


class StateExchange:
    """非文本状态的生成、存储、传输与解释。"""

    def __init__(
        self,
        embedding: EmbeddingProvider,
        task_id: str = "global",
        use_shared_memory: bool = False,
    ) -> None:
        self.embedding = embedding
        self.task_id = task_id
        self._buffer = SharedVectorBuffer(use_shared_memory)
        self._dags: dict[str, dict[str, Any]] = {}
        self._meta: dict[str, StateRef] = {}

    @property
    def transport(self) -> str:
        return "shm" if (self._buffer.use_shared_memory and not self._buffer.degraded) else "inproc"

    # ----- 生成与存储 -----
    def put_plan_state(self, plan: dict[str, Any]) -> StateRef:
        """把计划编码为 DAG + embedding + compact vector 的非文本状态。"""
        plan_text = json.dumps(plan, sort_keys=True, ensure_ascii=False, default=str)
        embedding = self.embedding.embed([plan_text])[0].astype(np.float32)
        vector = self._compact_vector(plan)

        content_hash = hashlib.sha256(plan_text.encode("utf-8") + embedding.tobytes()).hexdigest()
        sid = content_hash[:16]
        uri = f"state://{self.task_id}/{sid}"

        nbytes = self._buffer.put(f"{uri}#emb", embedding)
        nbytes += self._buffer.put(f"{uri}#vec", vector)
        self._dags[uri] = plan
        ref = StateRef(
            uri=uri,
            kind="plan",
            shape=tuple(embedding.shape),
            dtype=str(embedding.dtype),
            summary=f"plan(op={plan.get('operation')},n={len(plan.get('operands', []))})",
            content_hash=content_hash,
            nbytes=nbytes,
            transport=self.transport,
        )
        self._meta[uri] = ref
        return ref

    def embed_text(self, text: str, kind: str = "embedding") -> StateRef:
        """把文本编码为语义向量状态（vector:// 引用）。"""
        vec = self.embedding.embed([text])[0].astype(np.float32)
        content_hash = hashlib.sha256(vec.tobytes()).hexdigest()
        sid = content_hash[:16]
        uri = f"vector://{self.task_id}/{sid}"
        nbytes = self._buffer.put(f"{uri}#emb", vec)
        ref = StateRef(
            uri=uri,
            kind=kind,
            shape=tuple(vec.shape),
            dtype=str(vec.dtype),
            summary=text[:32],
            content_hash=content_hash,
            nbytes=nbytes,
            transport=self.transport,
        )
        self._meta[uri] = ref
        return ref

    # ----- 解释（接收方消费） -----
    def get_plan_state(self, uri: str) -> dict[str, Any]:
        """还原计划状态：{dag, embedding, vector}。"""
        if uri not in self._dags or not self._buffer.exists(f"{uri}#emb"):
            raise ReferenceError_(f"状态引用失效: {uri}")
        return {
            "dag": self._dags[uri],
            "embedding": self._buffer.get(f"{uri}#emb"),
            "vector": self._buffer.get(f"{uri}#vec"),
        }

    def get_vector(self, uri: str) -> np.ndarray:
        if not self._buffer.exists(f"{uri}#emb"):
            raise ReferenceError_(f"向量引用失效: {uri}")
        return self._buffer.get(f"{uri}#emb")

    def get_ref(self, uri: str) -> StateRef | None:
        return self._meta.get(uri)

    def exists(self, uri: str) -> bool:
        return uri in self._meta and (uri in self._dags or self._buffer.exists(f"{uri}#emb"))

    def invalidate(self, uri: str) -> None:
        """使状态引用失效（用于演示降级路径）。"""
        self._dags.pop(uri, None)

    def _compact_vector(self, plan: dict[str, Any]) -> np.ndarray:
        """计划的紧凑数值特征（compact state vector）。"""
        operands = plan.get("operands", [])
        op = str(plan.get("operation", ""))
        op_code = (int(hashlib.sha256(op.encode()).hexdigest(), 16) % 97) / 97.0
        return np.array(
            [float(len(operands)), op_code, 1.0 if operands else 0.0],
            dtype=np.float32,
        )

    def close(self) -> None:
        self._buffer.close()
        self._dags.clear()
        self._meta.clear()


__all__ = ["StateExchange", "StateRef"]
