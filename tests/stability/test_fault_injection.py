"""稳定性测试：故障注入与恢复。"""

from __future__ import annotations

import asyncio

import pytest
from scenarios.demo import make_demo_task

from agent_runtime.agents import CodeActExecutorAgent, RetrieverAgent
from agent_runtime.config import load_config
from agent_runtime.protocol.message import ActionType, AgentMessage
from agent_runtime.providers.base import LLMResponse
from agent_runtime.runtime.builder import build_context, build_default_agents
from agent_runtime.runtime.orchestrator import Orchestrator


@pytest.mark.stability
def test_crashing_agent_is_isolated():
    """某个 Agent 崩溃时，运行时不应崩溃，应优雅返回失败结果。"""

    class CrashingExecutor(CodeActExecutorAgent):
        async def handle(self, message, ctx):
            raise RuntimeError("simulated crash")

    cfg = load_config(load_env=False)
    agents = build_default_agents(cfg)
    agents["executor"] = CrashingExecutor()
    ctx = build_context(cfg, "structured", task_id="t")
    orch = Orchestrator(agents)
    result = asyncio.run(orch.run_task(make_demo_task(), ctx))
    assert result.success is False
    assert result.error is not None
    assert ctx.metrics.snapshot.error_count > 0
    assert ctx.metrics.snapshot.degradation_count > 0


@pytest.mark.stability
def test_llm_transient_failure_recovers():
    """LLM 暂时失败应通过重试恢复。"""

    class FlakyLLM:
        name = "flaky"
        model = "flaky"

        def __init__(self) -> None:
            self.fails = 1

        def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
            if self.fails > 0:
                self.fails -= 1
                raise RuntimeError("transient LLM error")
            return LLMResponse("ok", 1, 1, "flaky")

    cfg = load_config(load_env=False)
    ctx = build_context(cfg, "structured", task_id="t")
    ctx.llm = FlakyLLM()
    orch = Orchestrator(build_default_agents(cfg))
    result = asyncio.run(orch.run_task(make_demo_task(), ctx))
    assert result.success is True
    assert ctx.metrics.snapshot.degradation_count > 0


@pytest.mark.stability
def test_memory_unavailable_is_graceful():
    """记忆库不可用时应跳过检索/沉淀而不崩溃。"""
    cfg = load_config(load_env=False)
    ctx = build_context(cfg, "structured", task_id="t", use_memory=True)
    ctx.memory = None  # 模拟记忆库不可用
    orch = Orchestrator(build_default_agents(cfg))
    result = asyncio.run(orch.run_task(make_demo_task(), ctx))
    assert result.success is True


@pytest.mark.stability
def test_reference_invalidation_degrades_to_fallback():
    """Artifact 引用失效时应降级，不抛异常。"""
    cfg = load_config(load_env=False)
    ctx = build_context(cfg, "structured", task_id="t", use_state_exchange=True)
    msg = AgentMessage(
        trace_id="x",
        task_id="t",
        source_agent="planner",
        target_agent="retriever",
        action_type=ActionType.RETRIEVE,
        input_parameters={
            "plan": {"operation": "sum", "operands": ["a"]},
            "facts_ref": "artifact://task/t/deadbeefdeadbeef",
        },
    )
    retriever = RetrieverAgent()
    asyncio.run(retriever.handle(msg, ctx))
    assert ctx.metrics.snapshot.degradation_count > 0
