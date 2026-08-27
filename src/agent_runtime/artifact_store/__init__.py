"""内容寻址 Artifact 存储（URI、引用计数 GC、作用域、失效降级）。"""

from __future__ import annotations

from agent_runtime.artifact_store.store import ArtifactRef, ArtifactStore

__all__ = ["ArtifactStore", "ArtifactRef"]
