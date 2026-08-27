"""结构化通信协议（Pydantic 契约、schema 校验、版本、text↔structured 映射）。"""

from __future__ import annotations

from agent_runtime.protocol.idempotency import IdempotencyCache, fingerprint
from agent_runtime.protocol.mapper import from_wire, semantically_equivalent, to_wire
from agent_runtime.protocol.message import ActionType, AgentMessage, MessageStatus
from agent_runtime.protocol.schema import (
    is_compatible,
    message_json_schema,
    validate_message,
)
from agent_runtime.protocol.serialization import (
    decode_structured,
    encode_structured,
    measure,
    render_text,
)

__all__ = [
    "AgentMessage",
    "ActionType",
    "MessageStatus",
    "IdempotencyCache",
    "fingerprint",
    "to_wire",
    "from_wire",
    "semantically_equivalent",
    "is_compatible",
    "message_json_schema",
    "validate_message",
    "encode_structured",
    "decode_structured",
    "render_text",
    "measure",
]
