"""非文本状态交换单元测试。"""

from __future__ import annotations

import numpy as np
import pytest

from agent_runtime.providers.mock import MockEmbedding
from agent_runtime.runtime.errors import ReferenceError_
from agent_runtime.state_exchange.exchange import StateExchange
from agent_runtime.state_exchange.shared_buffer import SharedVectorBuffer


def _exchange(use_shm=False):
    return StateExchange(MockEmbedding(dim=64, seed=1), task_id="t1", use_shared_memory=use_shm)


def test_put_get_plan_state():
    ex = _exchange()
    plan = {"operation": "sum", "operands": ["a", "b", "c"]}
    ref = ex.put_plan_state(plan)
    assert ref.uri.startswith("state://t1/")
    assert ref.nbytes > 0
    state = ex.get_plan_state(ref.uri)
    assert state["dag"] == plan
    assert state["embedding"].shape == (64,)
    assert state["vector"].shape == (3,)


def test_embed_text_vector_ref():
    ex = _exchange()
    ref = ex.embed_text("fix async resource leak")
    assert ref.uri.startswith("vector://t1/")
    vec = ex.get_vector(ref.uri)
    assert vec.shape == (64,)


def test_invalidate_state_raises():
    ex = _exchange()
    ref = ex.put_plan_state({"operation": "sum", "operands": ["a"]})
    ex.invalidate(ref.uri)
    with pytest.raises(ReferenceError_):
        ex.get_plan_state(ref.uri)


def test_shared_buffer_inproc_roundtrip():
    buf = SharedVectorBuffer(use_shared_memory=False)
    arr = np.arange(10, dtype=np.float32)
    n = buf.put("k", arr)
    assert n == arr.nbytes
    assert np.array_equal(buf.get("k"), arr)
    buf.close()


def test_shared_buffer_shm_or_degrade():
    buf = SharedVectorBuffer(use_shared_memory=True)
    arr = np.arange(8, dtype=np.float32)
    buf.put("k", arr)
    # 无论使用共享内存还是降级，取回的数据都应正确。
    assert np.array_equal(buf.get("k"), arr)
    buf.close()
