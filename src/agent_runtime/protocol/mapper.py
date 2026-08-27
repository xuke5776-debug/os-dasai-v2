"""协议映射：text ↔ structured。

`AgentMessage` 是唯一真源：
- `to_wire(msg, mode)` 把消息渲染为对应模式的传输表示；
- `from_wire(wire, mode)` 把传输表示解析回消息。

结构化模式可无损往返核心字段；文本模式解析是**有损**的（自然语言不携带稳定的
机器可读结构），这正是结构化协议相对纯文本透传的优势之一：可校验、可路由、
可幂等。`semantically_equivalent` 用于在双模式公平性测试中断言核心语义一致。
"""

from __future__ import annotations

import re

from agent_runtime.protocol.message import ActionType, AgentMessage, MessageStatus
from agent_runtime.protocol.serialization import (
    decode_structured,
    encode_structured,
    render_text,
)

_TEXT_PATTERNS = {
    "source_agent": re.compile(r"agent '([^']*)' speaking"),
    "target_agent": re.compile(r"speaking to agent '([^']*)'"),
    "action_type": re.compile(r"action '([^']*)'"),
    "capability": re.compile(r"capability '([^']*)'"),
    "task_id": re.compile(r"task '([^']*)'"),
    "step_id": re.compile(r"step '([^']*)'"),
    "trace_id": re.compile(r"trace '([^']*)'"),
    "status": re.compile(r"status is '([^']*)'"),
}


def to_wire(message: AgentMessage, mode: str) -> str:
    if mode == "text":
        return render_text(message)
    if mode == "structured":
        return encode_structured(message)
    raise ValueError(f"未知模式: {mode}")


def from_wire(wire: str, mode: str) -> AgentMessage:
    if mode == "structured":
        return decode_structured(wire)
    if mode == "text":
        return _decode_text(wire)
    raise ValueError(f"未知模式: {mode}")


def _decode_text(wire: str) -> AgentMessage:
    """从自然语言文本中尽力解析核心字段（有损）。"""
    fields: dict[str, str] = {}
    for name, pat in _TEXT_PATTERNS.items():
        m = pat.search(wire)
        if m:
            fields[name] = m.group(1)
    return AgentMessage(
        trace_id=fields.get("trace_id", "unknown"),
        task_id=fields.get("task_id", "unknown"),
        step_id=fields.get("step_id", ""),
        source_agent=fields.get("source_agent", "unknown"),
        target_agent=fields.get("target_agent", "unknown"),
        action_type=_safe_action(fields.get("action_type")),
        capability=fields.get("capability", ""),
        status=_safe_status(fields.get("status")),
    )


def _safe_action(value: str | None) -> ActionType:
    try:
        return ActionType(value) if value else ActionType.RESULT
    except ValueError:
        return ActionType.RESULT


def _safe_status(value: str | None) -> MessageStatus:
    try:
        return MessageStatus(value) if value else MessageStatus.OK
    except ValueError:
        return MessageStatus.OK


def semantically_equivalent(a: AgentMessage, b: AgentMessage) -> bool:
    """比较两条消息的核心语义字段是否一致（用于双模式公平性断言）。"""
    keys = ("source_agent", "target_agent", "action_type", "task_id", "step_id", "status")
    return all(getattr(a, k) == getattr(b, k) for k in keys)


__all__ = ["to_wire", "from_wire", "semantically_equivalent"]
