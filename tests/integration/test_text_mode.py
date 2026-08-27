"""集成测试：端到端多 Agent 协作（双模式）。"""

from __future__ import annotations

import asyncio

from scenarios.demo import make_demo_task

from agent_runtime.config import load_config
from agent_runtime.runtime.builder import run_task


def _run(mode: str):
    config = load_config(load_env=False)
    task = make_demo_task()
    return asyncio.run(run_task(task, config=config, mode=mode))


def test_text_mode_completes_successfully():
    result = _run("text")
    assert result.success is True
    assert result.outputs["answer"] == 12
    assert result.metrics.message_count > 0
    assert result.metrics.text_tokens > 0
    assert result.metrics.llm_calls == 4  # 四个 Agent 各调用一次


def test_structured_mode_completes_successfully():
    result = _run("structured")
    assert result.success is True
    assert result.outputs["answer"] == 12


def test_structured_saves_tokens_without_losing_success():
    text_res = _run("text")
    struct_res = _run("structured")
    # 成功率不降
    assert text_res.success == struct_res.success is True
    # 结构化模式通信 token 更低
    assert struct_res.metrics.text_tokens < text_res.metrics.text_tokens


def test_metrics_snapshot_serializable():
    result = _run("structured")
    d = result.metrics.to_dict()
    assert "derived" in d
    assert d["task_success"] is True
