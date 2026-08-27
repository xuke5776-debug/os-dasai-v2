"""指标采集器单元测试。"""

from __future__ import annotations

from agent_runtime.observability.metrics import MetricsCollector


def test_message_and_token_accounting():
    m = MetricsCollector()
    m.record_message(tokens=10, chars=40)
    m.record_message(tokens=5, chars=20)
    assert m.snapshot.message_count == 2
    assert m.snapshot.text_tokens == 15
    assert m.snapshot.text_chars == 60


def test_repeated_tool_calls():
    m = MetricsCollector()
    m.record_tool_call("compute:sum")
    m.record_tool_call("compute:sum")
    m.record_tool_call("compute:max")
    assert m.snapshot.tool_calls == 3
    assert m.snapshot.repeated_tool_calls == 1


def test_memory_and_derived():
    m = MetricsCollector()
    m.record_message(tokens=1)
    m.record_memory(retrieved=2, used=2, effective=1, harmful=1)
    d = m.snapshot.to_dict()
    assert d["memory_retrieved"] == 2
    assert d["derived"]["effective_hit_rate"] == 0.5


def test_latency_timing():
    m = MetricsCollector()
    m.start()
    m.stop()
    assert m.snapshot.latency_sec >= 0.0
