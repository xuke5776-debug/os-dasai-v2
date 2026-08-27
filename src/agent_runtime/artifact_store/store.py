"""内容寻址 Artifact 存储。

长内容（事实表、日志、代码、文档、工具结果）只保存一次，消息仅携带引用：
- 稳定 ID = 内容哈希（内容寻址，天然去重）；
- URI 形如 `artifact://task/{task_id}/{artifact_id}` 或 `artifact://global/{artifact_id}`；
- 引用计数 + 垃圾回收；
- 作用域（task / global）；
- 引用失效检测（get 不存在抛 ReferenceError_，调用方可降级为文本）。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from agent_runtime.runtime.errors import ReferenceError_


@dataclass(frozen=True)
class ArtifactRef:
    """Artifact 引用（消息中传输的就是它，而非内容本身）。"""

    uri: str
    content_hash: str
    summary: str
    size: int
    media_type: str
    scope: str


def _to_bytes(content: Any, media_type: str) -> tuple[bytes, str]:
    if isinstance(content, bytes):
        return content, media_type
    if isinstance(content, str):
        return content.encode("utf-8"), media_type
    return json.dumps(content, ensure_ascii=False, sort_keys=True, default=str).encode(
        "utf-8"
    ), "application/json"


def _summarize(content: Any) -> str:
    text = (
        content
        if isinstance(content, str)
        else json.dumps(content, ensure_ascii=False, default=str)
    )
    return text[:48] + "…" if len(text) > 48 else text


class ArtifactStore:
    """内容寻址的 Artifact 存储（进程内，支持引用计数与 GC）。"""

    def __init__(self, task_id: str = "global") -> None:
        self.task_id = task_id
        self._blobs: dict[str, bytes] = {}  # content_hash -> bytes
        self._meta: dict[str, ArtifactRef] = {}  # uri -> ref
        self._refcount: dict[str, int] = {}  # content_hash -> count

    def put(
        self,
        content: Any,
        *,
        media_type: str = "application/json",
        scope: str = "task",
        summary: str | None = None,
    ) -> ArtifactRef:
        data, media_type = _to_bytes(content, media_type)
        content_hash = hashlib.sha256(data).hexdigest()
        artifact_id = content_hash[:16]
        prefix = f"task/{self.task_id}" if scope == "task" else "global"
        uri = f"artifact://{prefix}/{artifact_id}"

        self._blobs[content_hash] = data
        self._refcount[content_hash] = self._refcount.get(content_hash, 0) + 1
        ref = ArtifactRef(
            uri=uri,
            content_hash=content_hash,
            summary=summary or _summarize(content),
            size=len(data),
            media_type=media_type,
            scope=scope,
        )
        self._meta[uri] = ref
        return ref

    def get_bytes(self, uri: str) -> bytes:
        ref = self._meta.get(uri)
        if ref is None or ref.content_hash not in self._blobs:
            raise ReferenceError_(f"Artifact 引用失效: {uri}")
        return self._blobs[ref.content_hash]

    def get_json(self, uri: str) -> Any:
        return json.loads(self.get_bytes(uri).decode("utf-8"))

    def get_ref(self, uri: str) -> ArtifactRef | None:
        return self._meta.get(uri)

    def exists(self, uri: str) -> bool:
        ref = self._meta.get(uri)
        return ref is not None and ref.content_hash in self._blobs

    # ----- 引用计数 / GC -----
    def incref(self, uri: str) -> None:
        ref = self._meta.get(uri)
        if ref:
            self._refcount[ref.content_hash] = self._refcount.get(ref.content_hash, 0) + 1

    def decref(self, uri: str) -> None:
        ref = self._meta.get(uri)
        if ref:
            self._refcount[ref.content_hash] = max(0, self._refcount.get(ref.content_hash, 0) - 1)

    def collect(self) -> int:
        """回收引用计数为 0 的内容，返回回收数量。"""
        removed = 0
        for h, count in list(self._refcount.items()):
            if count <= 0:
                self._blobs.pop(h, None)
                self._refcount.pop(h, None)
                removed += 1
        # 清理悬空 URI 元数据
        for uri, ref in list(self._meta.items()):
            if ref.content_hash not in self._blobs:
                self._meta.pop(uri, None)
        return removed

    def invalidate(self, uri: str) -> None:
        """使一个引用失效（用于演示/测试降级路径）。"""
        ref = self._meta.get(uri)
        if ref:
            self._blobs.pop(ref.content_hash, None)

    def __len__(self) -> int:
        return len(self._blobs)


__all__ = ["ArtifactStore", "ArtifactRef"]
