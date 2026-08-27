"""运行时装配：把配置、Provider、Agent、上下文与编排器组装起来。"""

from __future__ import annotations

import numpy as np

from agent_runtime.agents import (
    CodeActExecutorAgent,
    PlannerAgent,
    RetrieverAgent,
    ReviewerSummarizerAgent,
)
from agent_runtime.artifact_store.store import ArtifactStore
from agent_runtime.config import Config, load_config
from agent_runtime.memory.store import MemoryStore
from agent_runtime.observability.logging import get_logger
from agent_runtime.observability.metrics import MetricsCollector
from agent_runtime.providers.factory import build_embedding, build_llm
from agent_runtime.providers.tokenizer import get_tokenizer
from agent_runtime.runtime.agent import BaseAgent
from agent_runtime.runtime.channel import Channel
from agent_runtime.runtime.context import RunContext
from agent_runtime.runtime.orchestrator import Orchestrator, RunResult
from agent_runtime.runtime.task import Task
from agent_runtime.sandbox.executor import CodeActExecutor
from agent_runtime.state_exchange.exchange import StateExchange


def build_default_agents(config: Config) -> dict[str, BaseAgent]:
    """构造默认四类 Agent。"""
    return {
        "planner": PlannerAgent(),
        "retriever": RetrieverAgent(),
        "executor": CodeActExecutorAgent(),
        "reviewer": ReviewerSummarizerAgent(),
    }


def build_context(
    config: Config,
    mode: str,
    *,
    task_id: str = "",
    use_memory: bool = False,
    use_state_exchange: bool = False,
    use_sandbox: bool = False,
    memory: MemoryStore | None = None,
) -> RunContext:
    """根据配置与模式构造运行上下文。

    若 `use_memory` 为真且未传入共享 `memory`，则新建一个进程内记忆库（无跨任务复用）。
    跨任务复用场景应由调用方创建一个共享 `MemoryStore` 并传入。
    """
    llm = build_llm(config)
    embedding = build_embedding(config)
    metrics = MetricsCollector()
    tokenizer = get_tokenizer(model=config.llm.model)
    logger = get_logger("runtime", mode=mode, task_id=task_id)
    channel = Channel(mode=mode, metrics=metrics, tokenizer=tokenizer, logger=logger)
    rng = np.random.default_rng(config.random_seed)
    artifact_store = ArtifactStore(task_id=task_id or "global")
    # 共享内存传输：默认进程内（跨平台稳定）；openEuler 上可通过 env 开启。
    state_exchange = StateExchange(
        embedding=embedding,
        task_id=task_id or "global",
        use_shared_memory=config.state_shared_memory,
    )
    if use_memory and memory is None:
        memory = MemoryStore(embedding=embedding, vector_backend=config.vector_backend)
    sandbox = CodeActExecutor(config.sandbox) if use_sandbox else None
    return RunContext(
        config=config,
        llm=llm,
        embedding=embedding,
        metrics=metrics,
        channel=channel,
        mode=mode,
        task_id=task_id,
        rng=rng,
        logger=logger,
        use_memory=use_memory,
        use_state_exchange=use_state_exchange,
        artifact_store=artifact_store,
        state_exchange=state_exchange,
        memory=memory,
        sandbox=sandbox,
    )


async def run_task(
    task: Task,
    *,
    config: Config | None = None,
    mode: str = "structured",
    use_memory: bool = False,
    use_state_exchange: bool = False,
    use_sandbox: bool = False,
    memory: MemoryStore | None = None,
) -> RunResult:
    """便捷入口：装配并运行一个任务。"""
    config = config or load_config()
    ctx = build_context(
        config,
        mode,
        task_id=task.task_id,
        use_memory=use_memory,
        use_state_exchange=use_state_exchange,
        use_sandbox=use_sandbox,
        memory=memory,
    )
    orchestrator = Orchestrator(build_default_agents(config))
    return await orchestrator.run_task(task, ctx)


__all__ = ["build_default_agents", "build_context", "run_task"]
