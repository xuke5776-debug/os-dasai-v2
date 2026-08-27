"""共享记忆存储单元测试：写入、去重、质量、反馈。"""

from __future__ import annotations

from agent_runtime.memory.models import MemoryRecord, MemoryType
from agent_runtime.memory.store import MemoryStore
from agent_runtime.providers.mock import MockEmbedding


def _store():
    return MemoryStore(embedding=MockEmbedding(dim=64, seed=1))


def _rec(**kw) -> MemoryRecord:
    base = {
        "source_agent": "reviewer",
        "task_topic": "sum-task",
        "summary": "operation sum over a,b,c -> 12",
        "keywords": ["sum", "a", "b", "c"],
        "success_feedback": True,
    }
    base.update(kw)
    return MemoryRecord(**base)


def test_write_creates_record():
    store = _store()
    rec, created = store.write(_rec())
    assert created is True
    assert store.count() == 1
    assert store.get(rec.memory_id) is not None


def test_exact_duplicate_is_deduped():
    store = _store()
    store.write(_rec())
    rec2, created2 = store.write(_rec())
    assert created2 is False
    assert store.count() == 1
    assert rec2.reuse_count >= 1


def test_error_memory_downweighted():
    store = _store()
    rec, _ = store.write(_rec(summary="bad fix", success_feedback=False))
    assert rec.quality_score <= 0.2


def test_record_feedback_adjusts_quality():
    store = _store()
    rec, _ = store.write(_rec())
    before = store.get(rec.memory_id).quality_score
    store.record_feedback(rec.memory_id, effective=False)
    after = store.get(rec.memory_id).quality_score
    assert after < before


def test_mark_used_increments_reuse():
    store = _store()
    rec, _ = store.write(_rec())
    store.mark_used(rec.memory_id)
    assert store.get(rec.memory_id).reuse_count == 1


def test_memory_type_persisted():
    store = _store()
    rec, _ = store.write(_rec(memory_type=MemoryType.PROCEDURAL))
    assert store.get(rec.memory_id).memory_type == MemoryType.PROCEDURAL
