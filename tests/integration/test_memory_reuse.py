"""集成测试：跨任务共享记忆复用降低重复计算。"""

from __future__ import annotations

import asyncio

from scenarios.demo import make_demo_task

from agent_runtime.config import load_config
from agent_runtime.memory.store import MemoryStore
from agent_runtime.providers.factory import build_embedding
from agent_runtime.runtime.builder import build_context, build_default_agents
from agent_runtime.runtime.orchestrator import Orchestrator


def _run(memory: MemoryStore):
    config = load_config(load_env=False)
    ctx = build_context(config, "structured", task_id="t", use_memory=True, memory=memory)
    orch = Orchestrator(build_default_agents(config))
    return asyncio.run(orch.run_task(make_demo_task(), ctx))


def test_second_run_reuses_memory_and_reduces_compute():
    config = load_config(load_env=False)
    shared = MemoryStore(embedding=build_embedding(config))

    run1 = _run(shared)
    run2 = _run(shared)

    # 两次都成功
    assert run1.success is True and run2.success is True
    # 第一次没有可复用记忆；第二次检索命中并有效复用
    assert run1.metrics.memory_used == 0
    assert run2.metrics.memory_retrieved > 0
    assert run2.metrics.memory_used > 0
    assert run2.metrics.memory_effective > 0
    # 复用使第二次的工具调用（重复计算）更少
    assert run2.metrics.tool_calls < run1.metrics.tool_calls


def test_memory_persisted_after_first_run():
    config = load_config(load_env=False)
    shared = MemoryStore(embedding=build_embedding(config))
    _run(shared)
    assert shared.count() >= 1
