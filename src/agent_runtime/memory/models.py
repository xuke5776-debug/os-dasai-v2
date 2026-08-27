"""共享记忆数据模型。"""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    """记忆类型。"""

    WORKING = "working"  # 当前任务的临时上下文
    EPISODIC = "episodic"  # 具体任务经历（轨迹、证据）
    SEMANTIC = "semantic"  # 抽象事实/知识
    PROCEDURAL = "procedural"  # 可复用的策略/补丁模板/流程


def _new_memory_id() -> str:
    return f"mem_{uuid.uuid4().hex[:12]}"


class MemoryRecord(BaseModel):
    """统一记忆单元。"""

    # ----- 必选基本元数据（赛题要求） -----
    memory_id: str = Field(default_factory=_new_memory_id)
    source_agent: str
    created_at: float = Field(default_factory=time.time)
    task_topic: str
    summary: str

    # ----- 建议元数据 -----
    memory_type: MemoryType = MemoryType.EPISODIC
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    embedding_ref: str | None = None
    artifact_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: float = 0.8
    quality_score: float = 0.8
    reuse_count: int = 0
    last_accessed_at: float | None = None
    version: int = 1
    parent_version: str | None = None
    expiration_policy: str = "none"  # none | ttl | task
    provenance: dict[str, Any] = Field(default_factory=dict)
    task_id: str = ""
    success_feedback: bool | None = None

    # ----- 载荷（结构化结论/策略，便于复用时直接取用） -----
    payload: dict[str, Any] = Field(default_factory=dict)

    def content_signature(self) -> str:
        """用于去重的内容签名（规范化 topic + summary）。"""
        return f"{self.task_topic.strip().lower()}|{self.summary.strip().lower()}"


__all__ = ["MemoryRecord", "MemoryType"]
