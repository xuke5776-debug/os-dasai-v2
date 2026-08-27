"""消息「上线」表示、编解码与开销计量。

同一条 `AgentMessage` 在两种模式下有不同的传输表示：

- **text_mode**：渲染为冗长自然语言，并把 `input_parameters` / `result` 中的
  完整内容内联进文本（模拟「把全文塞进消息」的传统做法）。
- **structured_mode**：序列化为紧凑结构（短键 + 引用），长内容以
  `artifact://` / `state://` 等引用 + 摘要承载，不内联全文。

两者携带等价语义，差异仅在于「是否搬运全文」与「键的冗余度」，因此 token 对比
公平地反映通信机制本身的开销。结构化模式支持无损往返核心字段（编解码）。
"""

from __future__ import annotations

import json
from typing import Any

from agent_runtime.protocol.message import ActionType, AgentMessage, MessageStatus
from agent_runtime.providers.tokenizer import Tokenizer, count_chars

# 结构化模式：字段 -> 紧凑短键。用于编码与解码（往返）。
FIELD_TO_COMPACT: dict[str, str] = {
    "protocol_version": "v",
    "message_id": "id",
    "trace_id": "tr",
    "task_id": "tk",
    "step_id": "st",
    "source_agent": "s",
    "target_agent": "t",
    "action_type": "a",
    "capability": "c",
    "status": "sta",
    "artifact_references": "ar",
    "evidence_references": "er",
    "state_reference": "sr",
    "dependencies": "dep",
    "confidence": "cf",
    "input_parameters": "ip",
    "result": "rs",
    "error": "e",
    "idempotency_key": "ik",
}
COMPACT_TO_FIELD: dict[str, str] = {v: k for k, v in FIELD_TO_COMPACT.items()}


def _humanize(value: Any) -> str:
    """把任意值渲染为自然语言友好的字符串（text_mode 用，倾向于冗长完整）。"""
    if isinstance(value, dict):
        return "; ".join(f"{k} is {_humanize(v)}" for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return ", ".join(_humanize(v) for v in value)
    return str(value)


def render_text(message: AgentMessage) -> str:
    """text_mode：渲染为冗长自然语言文本（内联完整内容）。"""
    lines = [
        f"Hello, this is agent '{message.source_agent}' speaking to "
        f"agent '{message.target_agent}'.",
        f"I am performing the action '{message.action_type.value}' "
        f"with capability '{message.capability}'.",
        f"This message belongs to task '{message.task_id}', step "
        f"'{message.step_id}', and trace '{message.trace_id}'.",
    ]
    if message.input_parameters:
        lines.append(
            "Here are the full input parameters you will need: "
            + _humanize(message.input_parameters)
            + "."
        )
    if message.result is not None:
        lines.append("Here is the complete result of my work: " + _humanize(message.result) + ".")
    if message.dependencies:
        lines.append(
            "This step depends on the following previous steps: "
            + ", ".join(message.dependencies)
            + "."
        )
    lines.append(
        f"My current status is '{message.status.value}'"
        + (f" with confidence {message.confidence}." if message.confidence is not None else ".")
    )
    if message.error:
        lines.append("Unfortunately an error occurred: " + _humanize(message.error) + ".")
    return " ".join(lines)


def _compact_params(params: dict[str, Any]) -> dict[str, Any]:
    """结构化模式下对参数做收敛：长字符串截断为摘要并标注引用提示。"""
    out: dict[str, Any] = {}
    for key, value in params.items():
        if isinstance(value, str) and len(value) > 64:
            out[key] = {"summary": value[:48] + "…", "len": len(value), "ref": True}
        elif isinstance(value, (list, tuple)) and len(value) > 8:
            out[key] = {"n": len(value), "head": list(value[:3]), "ref": True}
        else:
            out[key] = value
    return out


def encode_structured(message: AgentMessage) -> str:
    """structured_mode：紧凑 JSON（短键 + 引用，不内联全文）。"""
    c = FIELD_TO_COMPACT
    compact: dict[str, Any] = {
        c["protocol_version"]: message.protocol_version,
        c["message_id"]: message.message_id,
        c["trace_id"]: message.trace_id,
        c["task_id"]: message.task_id,
        c["step_id"]: message.step_id,
        c["source_agent"]: message.source_agent,
        c["target_agent"]: message.target_agent,
        c["action_type"]: message.action_type.value,
        c["capability"]: message.capability,
        c["status"]: message.status.value,
    }
    if message.artifact_references:
        compact[c["artifact_references"]] = message.artifact_references
    if message.evidence_references:
        compact[c["evidence_references"]] = message.evidence_references
    if message.state_reference:
        compact[c["state_reference"]] = message.state_reference
    if message.dependencies:
        compact[c["dependencies"]] = message.dependencies
    if message.confidence is not None:
        compact[c["confidence"]] = round(message.confidence, 3)
    if message.input_parameters:
        compact[c["input_parameters"]] = _compact_params(message.input_parameters)
    if message.result is not None:
        compact[c["result"]] = _compact_params(message.result)
    if message.error:
        compact[c["error"]] = message.error
    if message.idempotency_key:
        compact[c["idempotency_key"]] = message.idempotency_key
    return json.dumps(compact, ensure_ascii=False, separators=(",", ":"))


def decode_structured(wire: str) -> AgentMessage:
    """从紧凑 JSON 还原 AgentMessage（核心字段无损往返）。"""
    raw = json.loads(wire)
    data: dict[str, Any] = {}
    for ck, value in raw.items():
        field = COMPACT_TO_FIELD.get(ck)
        if field is None:
            continue
        if field == "action_type":
            data[field] = ActionType(value)
        elif field == "status":
            data[field] = MessageStatus(value)
        else:
            data[field] = value
    return AgentMessage(**data)


def render_structured(message: AgentMessage) -> str:
    """向后兼容别名。"""
    return encode_structured(message)


def measure(message: AgentMessage, mode: str, tokenizer: Tokenizer) -> tuple[str, int, int]:
    """返回 (wire 文本, token 数, 字符数)。"""
    wire = render_text(message) if mode == "text" else encode_structured(message)
    return wire, tokenizer.count(wire), count_chars(wire)


__all__ = [
    "render_text",
    "render_structured",
    "encode_structured",
    "decode_structured",
    "measure",
    "FIELD_TO_COMPACT",
    "COMPACT_TO_FIELD",
]
