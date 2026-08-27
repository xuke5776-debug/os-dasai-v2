"""结构化通信协议消息模型。

`AgentMessage` 是 Agent 间通信的**唯一真源**：
- `structured_mode` 直接传输该结构（紧凑、引用化）；
- `text_mode` 通过映射器把同一消息渲染为自然语言文本后透传。

这样保证两种模式在「相同任务、相同逻辑」下公平对比，差异仅来自通信载体。
"""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from agent_runtime import PROTOCOL_VERSION


class ActionType(str, Enum):
    """动作类型（高密度语义单元，替代自然语言意图描述）。"""

    REGISTER = "register"
    HANDSHAKE = "handshake"
    DISCOVER = "discover"
    PLAN = "plan"
    RETRIEVE = "retrieve"
    EXECUTE = "execute"
    REVIEW = "review"
    SUMMARIZE = "summarize"
    MEMORIZE = "memorize"
    RESULT = "result"
    ERROR = "error"
    ACK = "ack"


class MessageStatus(str, Enum):
    """消息/步骤状态。"""

    PENDING = "pending"
    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"
    RETRY = "retry"
    SKIPPED = "skipped"


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class AgentMessage(BaseModel):
    """Agent 间结构化消息（全字段契约）。"""

    protocol_version: str = Field(default=PROTOCOL_VERSION)
    message_id: str = Field(default_factory=lambda: _new_id("msg"))
    trace_id: str
    task_id: str
    step_id: str = ""

    source_agent: str
    target_agent: str
    timestamp: float = Field(default_factory=time.time)

    action_type: ActionType
    capability: str = ""

    input_parameters: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] | None = None
    status: MessageStatus = MessageStatus.PENDING

    dependencies: list[str] = Field(default_factory=list)

    # 引用而非搬运：长内容以引用 + 摘要承载。
    artifact_references: list[str] = Field(default_factory=list)
    evidence_references: list[str] = Field(default_factory=list)
    state_reference: str | None = None

    confidence: float | None = None
    error: dict[str, Any] | None = None

    # 通信/计算开销度量（tokens/bytes/latency 等）。
    metrics: dict[str, Any] = Field(default_factory=dict)

    # 幂等键：相同 (task_id, step_id, action_type, idempotency_key) 视为同一请求。
    idempotency_key: str | None = None

    def short(self) -> str:
        """用于日志的简短描述。"""
        return (
            f"{self.source_agent}->{self.target_agent} "
            f"{self.action_type.value} [{self.status.value}] "
            f"task={self.task_id} step={self.step_id}"
        )


__all__ = ["AgentMessage", "ActionType", "MessageStatus"]
