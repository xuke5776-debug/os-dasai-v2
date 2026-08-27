"""稳定性测试：≥10 轮连续执行。"""

from __future__ import annotations

import asyncio
import gc

import psutil
import pytest
from scenarios.demo import make_demo_task

from agent_runtime.config import load_config
from agent_runtime.memory.store import MemoryStore
from agent_runtime.providers.factory import build_embedding
from agent_runtime.runtime.builder import build_context, build_default_agents
from agent_runtime.runtime.orchestrator import Orchestrator


@pytest.mark.stability
def test_ten_consecutive_rounds_stable():
    cfg = load_config(load_env=False)
    shared_memory = MemoryStore(embedding=build_embedding(cfg))
    proc = psutil.Process()

    successes = 0
    rss_samples: list[float] = []
    for i in range(10):
        ctx = build_context(
            cfg,
            "structured",
            task_id=f"round-{i}",
            use_memory=True,
            use_state_exchange=True,
            use_sandbox=True,
            memory=shared_memory,
        )
        orch = Orchestrator(build_default_agents(cfg))
        result = asyncio.run(orch.run_task(make_demo_task(), ctx))
        if result.success:
            successes += 1
        gc.collect()
        rss_samples.append(proc.memory_info().rss / (1024 * 1024))

    assert successes == 10, f"仅 {successes}/10 轮成功"
    # 内存增长可控（宽松阈值，检测明显泄漏）。
    growth = rss_samples[-1] - rss_samples[0]
    assert growth < 80, f"RSS 增长过大: {growth:.1f} MB"


@pytest.mark.stability
def test_shared_memory_handles_released_after_run():
    """共享内存模式下，任务结束应释放全部状态缓冲句柄（防资源泄漏回归）。"""
    cfg = load_config(load_env=False).with_overrides(state_shared_memory=True)
    ctx = build_context(
        cfg,
        "structured",
        task_id="shm-release",
        use_state_exchange=True,
    )
    orch = Orchestrator(build_default_agents(cfg))
    result = asyncio.run(orch.run_task(make_demo_task(), ctx))

    # 确实走了非文本状态传递路径。
    assert result.metrics.state_transfers > 0
    # 任务结束后，本任务的状态缓冲应已释放（共享内存句柄 / DAG / 元数据均清空）。
    assert ctx.state_exchange is not None
    assert len(ctx.state_exchange._buffer._shm) == 0
    assert len(ctx.state_exchange._dags) == 0


@pytest.mark.stability
def test_memory_accumulates_and_reuse_grows():
    cfg = load_config(load_env=False)
    shared_memory = MemoryStore(embedding=build_embedding(cfg))
    used_counts = []
    for i in range(5):
        ctx = build_context(
            cfg,
            "structured",
            task_id=f"r{i}",
            use_memory=True,
            memory=shared_memory,
        )
        orch = Orchestrator(build_default_agents(cfg))
        result = asyncio.run(orch.run_task(make_demo_task(), ctx))
        used_counts.append(result.metrics.memory_used)
    # 第一轮无可复用记忆，之后开始命中复用
    assert used_counts[0] == 0
    assert sum(used_counts[1:]) > 0
