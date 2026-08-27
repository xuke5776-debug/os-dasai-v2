"""协议 schema 校验与版本兼容性。"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from agent_runtime import PROTOCOL_VERSION
from agent_runtime.protocol.message import AgentMessage
from agent_runtime.runtime.errors import ProtocolError


def message_json_schema() -> dict[str, Any]:
    """导出 AgentMessage 的 JSON Schema（供文档与外部校验使用）。"""
    return AgentMessage.model_json_schema()


def validate_message(data: dict[str, Any]) -> AgentMessage:
    """校验并构造 AgentMessage；失败抛 ProtocolError。"""
    try:
        msg = AgentMessage.model_validate(data)
    except ValidationError as exc:
        raise ProtocolError(f"消息 schema 校验失败: {exc.error_count()} 个错误") from exc
    if not is_compatible(msg.protocol_version):
        raise ProtocolError(f"协议版本不兼容: 收到 {msg.protocol_version}, 期望 {PROTOCOL_VERSION}")
    return msg


def is_compatible(version: str) -> bool:
    """主版本号一致即视为兼容。"""
    try:
        return version.split(".")[0] == PROTOCOL_VERSION.split(".")[0]
    except (AttributeError, IndexError):
        return False


__all__ = ["message_json_schema", "validate_message", "is_compatible"]
