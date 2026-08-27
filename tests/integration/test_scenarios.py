"""集成测试：关联连续任务 A / B 的跨任务过程性记忆复用。"""

from __future__ import annotations

import asyncio

from scenarios.task_group_a import make_a1, make_a2
from scenarios.task_group_b import make_b1, make_b2

from agent_runtime.config import load_config
from agent_runtime.memory.store import MemoryStore
from agent_runtime.providers.factory import build_embedding
from agent_runtime.runtime.builder import build_context, build_default_agents
from agent_runtime.runtime.orchestrator import Orchestrator


def _run(task, memory):
    config = load_config(load_env=False)
    ctx = build_context(
        config,
        "structured",
        task_id=task.task_id,
        use_memory=True,
        use_state_exchange=True,
        use_sandbox=True,
        memory=memory,
    )
    orch = Orchestrator(build_default_agents(config))
    return asyncio.run(orch.run_task(task, ctx))


def _fresh_memory():
    return MemoryStore(embedding=build_embedding(load_config(load_env=False)))


def test_group_a_reuses_fix_strategy():
    mem = _fresh_memory()
    r1 = _run(make_a1(), mem)
    assert r1.success is True
    r2 = _run(make_a2(), mem)
    # A2 不提供策略，只有复用 A1 的过程性记忆才能成功
    assert r2.success is True
    assert r2.metrics.memory_used > 0
    assert r2.metrics.memory_effective > 0


def test_group_a_fails_without_memory_reuse():
    mem = _fresh_memory()
    # 直接运行 A2（无 A1 记忆）→ 缺少策略 → 失败，证明复用确有价值
    r = _run(make_a2(), mem)
    assert r.success is False


def test_group_b_reuses_refactor_strategy():
    mem = _fresh_memory()
    r1 = _run(make_b1(), mem)
    assert r1.success is True
    r2 = _run(make_b2(), mem)
    assert r2.success is True
    assert r2.metrics.memory_used > 0
    assert r2.metrics.memory_effective > 0
