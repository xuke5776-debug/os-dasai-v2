"""协议层单元测试：schema 校验、编解码往返、映射、幂等。"""

from __future__ import annotations

import pytest

from agent_runtime.protocol.idempotency import IdempotencyCache, fingerprint
from agent_runtime.protocol.mapper import from_wire, semantically_equivalent, to_wire
from agent_runtime.protocol.message import ActionType, AgentMessage, MessageStatus
from agent_runtime.protocol.schema import (
    is_compatible,
    message_json_schema,
    validate_message,
)
from agent_runtime.runtime.errors import ProtocolError


def _msg(**kw) -> AgentMessage:
    base: dict = {
        "trace_id": "tr1",
        "task_id": "tk1",
        "step_id": "s0",
        "source_agent": "planner",
        "target_agent": "retriever",
        "action_type": ActionType.PLAN,
        "capability": "task_planning",
        "status": MessageStatus.OK,
    }
    base.update(kw)
    return AgentMessage(**base)


def test_json_schema_contains_required_fields():
    schema = message_json_schema()
    props = schema["properties"]
    for field in [
        "protocol_version",
        "message_id",
        "trace_id",
        "task_id",
        "step_id",
        "source_agent",
        "target_agent",
        "action_type",
        "capability",
        "input_parameters",
        "result",
        "status",
        "dependencies",
        "artifact_references",
        "evidence_references",
        "state_reference",
        "confidence",
        "error",
        "metrics",
    ]:
        assert field in props


def test_validate_message_ok_and_version():
    msg = _msg()
    validated = validate_message(msg.model_dump())
    assert validated.action_type == ActionType.PLAN
    assert is_compatible(validated.protocol_version)


def test_validate_message_rejects_incompatible_version():
    data = _msg().model_dump()
    data["protocol_version"] = "99.0"
    with pytest.raises(ProtocolError):
        validate_message(data)


def test_validate_message_rejects_bad_schema():
    with pytest.raises(ProtocolError):
        validate_message({"action_type": "plan"})  # 缺少必填字段


def test_structured_roundtrip_core_fields():
    msg = _msg(
        artifact_references=["artifact://task/tk1/a1"],
        state_reference="state://s1",
        confidence=0.9,
        dependencies=["s0"],
    )
    wire = to_wire(msg, "structured")
    back = from_wire(wire, "structured")
    assert back.source_agent == msg.source_agent
    assert back.target_agent == msg.target_agent
    assert back.action_type == msg.action_type
    assert back.task_id == msg.task_id
    assert back.artifact_references == msg.artifact_references
    assert back.state_reference == msg.state_reference
    assert back.dependencies == msg.dependencies


def test_text_decode_is_lossy_but_keeps_core():
    msg = _msg()
    wire = to_wire(msg, "text")
    back = from_wire(wire, "text")
    # 文本模式可恢复核心字段，但语义等价性仍成立
    assert semantically_equivalent(msg, back)


def test_idempotency_cache():
    cache = IdempotencyCache()
    req = _msg(input_parameters={"x": 1})
    assert not cache.seen(req)
    result = _msg(action_type=ActionType.RESULT)
    cache.remember(req, result)
    assert cache.seen(req)
    assert cache.get(req) is result
    # 相同语义请求指纹一致
    req2 = _msg(input_parameters={"x": 1})
    assert fingerprint(req) == fingerprint(req2)
