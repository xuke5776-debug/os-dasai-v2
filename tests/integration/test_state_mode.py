"""集成测试：结构化 + 非文本状态交换（实验配置 C）。"""

from __future__ import annotations

import asyncio

from scenarios.demo import make_demo_task

from agent_runtime.config import load_config
from agent_runtime.runtime.builder import build_context, build_default_agents
from agent_runtime.runtime.orchestrator import Orchestrator


def _run(mode: str, use_state_exchange: bool):
    config = load_config(load_env=False)
    ctx = build_context(config, mode, task_id="t", use_state_exchange=use_state_exchange)
    orch = Orchestrator(build_default_agents(config))
    result = asyncio.run(orch.run_task(make_demo_task(), ctx))
    return result, ctx


def test_state_mode_succeeds_and_consumes_state():
    result, ctx = _run("structured", True)
    assert result.success is True
    assert result.outputs["answer"] == 12
    # 接收方真实消费了非文本状态
    assert ctx.blackboard.get("state_consumed") is True
    # 发生了非文本状态传递
    assert result.metrics.state_transfers > 0
    assert result.metrics.state_bytes > 0
    # 消息携带了 artifact 引用
    assert result.metrics.artifact_refs > 0


def test_state_mode_saves_more_tokens_than_structured():
    struct_only, _ = _run("structured", False)
    struct_state, _ = _run("structured", True)
    # 引用化 + 非文本状态进一步降低文本 token，且成功率不降
    assert struct_state.success == struct_only.success is True
    assert struct_state.metrics.text_tokens < struct_only.metrics.text_tokens


def test_token_savings_ranking_text_struct_state():
    text_res, _ = _run("text", False)
    struct_res, _ = _run("structured", False)
    state_res, _ = _run("structured", True)
    assert (
        state_res.metrics.text_tokens
        < struct_res.metrics.text_tokens
        < text_res.metrics.text_tokens
    )
