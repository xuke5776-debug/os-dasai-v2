"""共享记忆检索单元测试：关键词 / 标签 / 语义 / 质量过滤。"""

from __future__ import annotations

from agent_runtime.memory.models import MemoryRecord
from agent_runtime.memory.store import MemoryStore
from agent_runtime.providers.mock import MockEmbedding


def _store():
    store = MemoryStore(embedding=MockEmbedding(dim=128, seed=2))
    store.write(
        MemoryRecord(
            source_agent="reviewer",
            task_topic="async fix",
            summary="fix async resource leak by awaiting close",
            keywords=["async", "resource", "leak"],
            tags=["bugfix", "async"],
            success_feedback=True,
        )
    )
    store.write(
        MemoryRecord(
            source_agent="reviewer",
            task_topic="logging",
            summary="add structured logging to module",
            keywords=["logging", "module"],
            tags=["refactor"],
            success_feedback=True,
        )
    )
    return store


def test_keyword_retrieval():
    store = _store()
    hits = store.retrieve(keywords=["async", "leak"], top_k=5)
    assert hits
    assert "async" in hits[0].record.keywords


def test_tag_retrieval():
    store = _store()
    hits = store.retrieve(tags=["refactor"], top_k=5)
    assert hits
    assert "refactor" in hits[0].record.tags


def test_semantic_retrieval():
    store = _store()
    hits = store.retrieve("fix asynchronous resource leak", top_k=1)
    assert hits
    assert hits[0].record.task_topic == "async fix"


def test_low_quality_excluded_by_default():
    store = _store()
    bad, _ = store.write(
        MemoryRecord(
            source_agent="reviewer",
            task_topic="bad",
            summary="harmful wrong fix",
            keywords=["async"],
            success_feedback=False,
        )
    )
    hits = store.retrieve(keywords=["async"], top_k=10)
    ids = {h.record.memory_id for h in hits}
    assert bad.memory_id not in ids
    hits_all = store.retrieve(keywords=["async"], top_k=10, include_low_quality=True)
    ids_all = {h.record.memory_id for h in hits_all}
    assert bad.memory_id in ids_all
