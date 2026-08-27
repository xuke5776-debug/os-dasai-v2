"""共享记忆存储与检索。

- 元数据存于 SQLite（可文件持久化，支持跨任务/跨会话复用）；
- 向量存于可插拔向量后端（默认 numpy）；
- 支持关键词 / 标签 / 语义混合检索；
- 去重（语义近重 + 内容签名）、版本管理、质量控制、错误记忆降权、provenance 追溯；
- 复用计数与命中度量（Retrieved / Used / Effective / Harmful 由调用方结合反馈记录）。
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass

import numpy as np

from agent_runtime.memory.models import MemoryRecord, MemoryType
from agent_runtime.memory.vector_backend import build_vector_index
from agent_runtime.providers.base import EmbeddingProvider


@dataclass
class MemoryHit:
    """一次检索命中。"""

    record: MemoryRecord
    score: float
    match_type: str  # "semantic" | "keyword" | "tag" | "hybrid"


_SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    memory_id TEXT PRIMARY KEY,
    source_agent TEXT,
    created_at REAL,
    task_topic TEXT,
    summary TEXT,
    memory_type TEXT,
    tags TEXT,
    keywords TEXT,
    embedding TEXT,
    embedding_ref TEXT,
    artifact_refs TEXT,
    evidence_refs TEXT,
    confidence REAL,
    quality_score REAL,
    reuse_count INTEGER,
    last_accessed_at REAL,
    version INTEGER,
    parent_version TEXT,
    expiration_policy TEXT,
    provenance TEXT,
    task_id TEXT,
    success_feedback INTEGER,
    payload TEXT
);
"""


class MemoryStore:
    """共享记忆库。"""

    def __init__(
        self,
        embedding: EmbeddingProvider,
        db_path: str = ":memory:",
        vector_backend: str = "numpy",
        dedup_threshold: float = 0.97,
        quality_floor: float = 0.3,
    ) -> None:
        self.embedding = embedding
        self.dedup_threshold = dedup_threshold
        self.quality_floor = quality_floor
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)
        self.index = build_vector_index(vector_backend, getattr(embedding, "dim", 256))
        self._rebuild_index()

    # ------------------------------------------------------------------ 写入
    def write(self, record: MemoryRecord) -> tuple[MemoryRecord, bool]:
        """写入记忆。返回 (记录, 是否新建)；命中去重时返回既有记录并更新。"""
        emb = self._embed(record)

        # 语义近重检测
        hits = self.index.search(emb, top_k=1)
        if hits and hits[0][1] >= self.dedup_threshold:
            existing = self.get(hits[0][0])
            if existing is not None:
                if existing.content_signature() == record.content_signature():
                    # 完全重复：提升复用计数，融合质量，不新建。
                    self._merge_duplicate(existing, record)
                    return existing, False
                # 语义近重：作为新版本链接到既有记录。
                record.parent_version = existing.memory_id
                record.version = existing.version + 1

        # 错误记忆降权
        if record.success_feedback is False:
            record.quality_score = min(record.quality_score, 0.2)

        record.embedding_ref = f"vector://memory/{record.memory_id}"
        self._insert(record, emb)
        self.index.add(record.memory_id, emb)
        return record, True

    # ------------------------------------------------------------------ 检索
    def retrieve(
        self,
        query_text: str | None = None,
        *,
        tags: list[str] | None = None,
        keywords: list[str] | None = None,
        top_k: int = 5,
        memory_type: MemoryType | None = None,
        include_low_quality: bool = False,
    ) -> list[MemoryHit]:
        """关键词 / 标签 / 语义混合检索。"""
        rows = self._all_records()
        if not rows:
            return []

        # 语义相似度
        sem_scores: dict[str, float] = {}
        if query_text:
            qvec = self.embedding.embed([query_text])[0]
            for mid, score in self.index.search(qvec, top_k=max(top_k * 3, 10)):
                sem_scores[mid] = score

        scored: list[MemoryHit] = []
        kw_set = {k.lower() for k in (keywords or [])}
        tag_set = {t.lower() for t in (tags or [])}
        for rec in rows:
            if memory_type is not None and rec.memory_type != memory_type:
                continue
            if not include_low_quality and rec.quality_score < self.quality_floor:
                continue
            sem = sem_scores.get(rec.memory_id, 0.0)
            kw_overlap = (
                len(kw_set & {k.lower() for k in rec.keywords}) / len(kw_set) if kw_set else 0.0
            )
            tag_overlap = (
                len(tag_set & {t.lower() for t in rec.tags}) / len(tag_set) if tag_set else 0.0
            )
            # 综合分：语义 + 关键词 + 标签，并乘以质量权重。
            base = 0.6 * sem + 0.25 * kw_overlap + 0.15 * tag_overlap
            if base <= 0.0:
                continue
            score = base * (0.5 + 0.5 * rec.quality_score)
            match_type = self._match_type(sem, kw_overlap, tag_overlap)
            scored.append(MemoryHit(record=rec, score=score, match_type=match_type))

        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[:top_k]

    # ------------------------------------------------------------------ 复用反馈
    def mark_used(self, memory_id: str, effective: bool | None = None) -> None:
        """标记一次复用：更新计数/时间，并按效果调整质量（负迁移降权）。"""
        rec = self.get(memory_id)
        if rec is None:
            return
        rec.reuse_count += 1
        rec.last_accessed_at = time.time()
        if effective is True:
            rec.quality_score = min(1.0, rec.quality_score + 0.05)
        elif effective is False:
            rec.quality_score = max(0.0, rec.quality_score - 0.2)
        self._update_dynamic(rec)

    def record_feedback(self, memory_id: str, effective: bool) -> None:
        """记录复用效果反馈，仅调整质量分（不增加复用计数）。

        负迁移（effective=False）显著降权，错误记忆将逐步跌破质量阈值而被检索排除。
        """
        rec = self.get(memory_id)
        if rec is None:
            return
        if effective:
            rec.quality_score = min(1.0, rec.quality_score + 0.05)
        else:
            rec.quality_score = max(0.0, rec.quality_score - 0.2)
        self._update_dynamic(rec)

    # ------------------------------------------------------------------ 查询
    def get(self, memory_id: str) -> MemoryRecord | None:
        cur = self.conn.execute("SELECT * FROM memories WHERE memory_id=?", (memory_id,))
        row = cur.fetchone()
        return self._row_to_record(row) if row else None

    def count(self) -> int:
        return int(self.conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0])

    def all_records(self) -> list[MemoryRecord]:
        return self._all_records()

    def close(self) -> None:
        self.conn.close()

    # ------------------------------------------------------------------ 内部
    def _embed(self, record: MemoryRecord) -> np.ndarray:
        text = self._embed_text(record)
        return self.embedding.embed([text])[0].astype(np.float32)

    @staticmethod
    def _embed_text(record: MemoryRecord) -> str:
        return " ".join(
            [record.task_topic, record.summary, " ".join(record.keywords), " ".join(record.tags)]
        )

    @staticmethod
    def _match_type(sem: float, kw: float, tag: float) -> str:
        signals = [("semantic", sem), ("keyword", kw), ("tag", tag)]
        active = [name for name, v in signals if v > 0]
        if len(active) > 1:
            return "hybrid"
        return active[0] if active else "semantic"

    def _merge_duplicate(self, existing: MemoryRecord, incoming: MemoryRecord) -> None:
        existing.reuse_count += 1
        existing.last_accessed_at = time.time()
        existing.quality_score = max(existing.quality_score, incoming.quality_score)
        self._update_dynamic(existing)

    def _insert(self, rec: MemoryRecord, emb: np.ndarray) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO memories VALUES
            (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                rec.memory_id,
                rec.source_agent,
                rec.created_at,
                rec.task_topic,
                rec.summary,
                rec.memory_type.value,
                json.dumps(rec.tags, ensure_ascii=False),
                json.dumps(rec.keywords, ensure_ascii=False),
                json.dumps(emb.tolist()),
                rec.embedding_ref,
                json.dumps(rec.artifact_refs, ensure_ascii=False),
                json.dumps(rec.evidence_refs, ensure_ascii=False),
                rec.confidence,
                rec.quality_score,
                rec.reuse_count,
                rec.last_accessed_at,
                rec.version,
                rec.parent_version,
                rec.expiration_policy,
                json.dumps(rec.provenance, ensure_ascii=False, default=str),
                rec.task_id,
                None if rec.success_feedback is None else int(rec.success_feedback),
                json.dumps(rec.payload, ensure_ascii=False, default=str),
            ),
        )
        self.conn.commit()

    def _update_dynamic(self, rec: MemoryRecord) -> None:
        self.conn.execute(
            """UPDATE memories SET reuse_count=?, last_accessed_at=?, quality_score=?
            WHERE memory_id=?""",
            (rec.reuse_count, rec.last_accessed_at, rec.quality_score, rec.memory_id),
        )
        self.conn.commit()

    def _all_records(self) -> list[MemoryRecord]:
        cur = self.conn.execute("SELECT * FROM memories")
        return [self._row_to_record(r) for r in cur.fetchall()]

    def _rebuild_index(self) -> None:
        cur = self.conn.execute("SELECT memory_id, embedding FROM memories")
        for row in cur.fetchall():
            emb = np.array(json.loads(row["embedding"]), dtype=np.float32)
            self.index.add(row["memory_id"], emb)

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> MemoryRecord:
        sf = row["success_feedback"]
        return MemoryRecord(
            memory_id=row["memory_id"],
            source_agent=row["source_agent"],
            created_at=row["created_at"],
            task_topic=row["task_topic"],
            summary=row["summary"],
            memory_type=MemoryType(row["memory_type"]),
            tags=json.loads(row["tags"]),
            keywords=json.loads(row["keywords"]),
            embedding_ref=row["embedding_ref"],
            artifact_refs=json.loads(row["artifact_refs"]),
            evidence_refs=json.loads(row["evidence_refs"]),
            confidence=row["confidence"],
            quality_score=row["quality_score"],
            reuse_count=row["reuse_count"],
            last_accessed_at=row["last_accessed_at"],
            version=row["version"],
            parent_version=row["parent_version"],
            expiration_policy=row["expiration_policy"],
            provenance=json.loads(row["provenance"]),
            task_id=row["task_id"],
            success_feedback=None if sf is None else bool(sf),
            payload=json.loads(row["payload"]),
        )


__all__ = ["MemoryStore", "MemoryHit"]
