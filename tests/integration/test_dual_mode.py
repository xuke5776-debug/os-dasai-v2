"""集成测试：注册/能力发现驱动的编排与双模式公平性。"""

from __future__ import annotations

import asyncio

from scenarios.demo import make_demo_task

from agent_runtime.config import load_config
from agent_runtime.runtime.builder import build_context, build_default_agents
from agent_runtime.runtime.orchestrator import Orchestrator


def test_orchestrator_registers_and_discovers_agents():
    config = load_config(load_env=False)
    orch = Orchestrator(build_default_agents(config))
    assert len(orch.registry.all_cards()) == 4
    assert orch._resolved["planner"] == "planner"
    assert orch._resolved["retriever"] == "retriever"
    assert orch._resolved["executor"] == "executor"
    assert orch._resolved["reviewer"] == "reviewer"


def _run(mode: str):
    config = load_config(load_env=False)
    ctx = build_context(config, mode, task_id="t")
    orch = Orchestrator(build_default_agents(config))
    return asyncio.run(orch.run_task(make_demo_task(), ctx))


def test_dual_mode_fair_comparison():
    text_res = _run("text")
    struct_res = _run("structured")
    # 公平性：同任务、同 Agent、相同成功结果
    assert text_res.success == struct_res.success is True
    assert text_res.outputs["answer"] == struct_res.outputs["answer"] == 12
    assert text_res.metrics.llm_calls == struct_res.metrics.llm_calls
    # 结构化通信更省 token
    assert struct_res.metrics.text_tokens < text_res.metrics.text_tokens
