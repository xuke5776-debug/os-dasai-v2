"""Artifact 存储单元测试：内容寻址、引用计数、失效。"""

from __future__ import annotations

import pytest

from agent_runtime.artifact_store.store import ArtifactStore
from agent_runtime.runtime.errors import ReferenceError_


def test_put_get_roundtrip():
    store = ArtifactStore(task_id="t1")
    ref = store.put({"a": 1, "b": 2})
    assert ref.uri.startswith("artifact://task/t1/")
    assert store.get_json(ref.uri) == {"a": 1, "b": 2}


def test_content_addressing_dedup():
    store = ArtifactStore(task_id="t1")
    r1 = store.put({"x": 1})
    r2 = store.put({"x": 1})
    # 相同内容 -> 相同哈希与 URI（去重）
    assert r1.content_hash == r2.content_hash
    assert r1.uri == r2.uri
    assert len(store) == 1


def test_refcount_and_gc():
    store = ArtifactStore()
    ref = store.put({"x": 1})  # refcount=1
    store.decref(ref.uri)  # refcount=0
    removed = store.collect()
    assert removed == 1
    assert not store.exists(ref.uri)


def test_invalidate_triggers_reference_error():
    store = ArtifactStore()
    ref = store.put({"x": 1})
    store.invalidate(ref.uri)
    with pytest.raises(ReferenceError_):
        store.get_json(ref.uri)


def test_global_scope_uri():
    store = ArtifactStore(task_id="t1")
    ref = store.put("big content", scope="global")
    assert ref.uri.startswith("artifact://global/")
