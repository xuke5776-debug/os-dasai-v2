"""评测框架单元测试（benchmark smoke test）。"""

from __future__ import annotations

from agent_runtime.evaluation.runner import run_suite
from agent_runtime.evaluation.stats import summarize


def test_summarize_basic():
    s = summarize([1.0, 2.0, 3.0, 4.0])
    assert s["mean"] == 2.5
    assert s["n"] == 4
    assert s["p50"] == 2.5


def test_main_suite_smoke():
    payload = run_suite(suite="main", repeat=2, seed=1)
    results = payload["results"]
    assert set(results.keys()) == {"A", "B", "C", "D"}
    # 全部配置成功率 100%
    for r in results.values():
        assert r["derived"]["success_rate"] == 1.0
    # 结构化 + 状态相对文本基线显著节省 token
    assert results["C"]["derived"]["token_saving_vs_A"] > 0.3
    assert results["D"]["derived"]["token_saving_vs_A"] > 0.3
    # 文本基线节省为 0（基准自身）
    assert results["A"]["derived"]["token_saving_vs_A"] == 0.0


def test_full_system_memory_reuse():
    payload = run_suite(suite="main", repeat=2, seed=7)
    d = payload["results"]["D"]["summary"]
    # 全系统在两次相同任务序列中产生记忆复用
    assert d["memory_used"]["mean"] > 0
    assert d["memory_effective"]["mean"] > 0
