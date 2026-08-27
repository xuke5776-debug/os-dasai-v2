"""运行时异常类型。"""

from __future__ import annotations


class AgentRuntimeError(Exception):
    """运行时基础异常。"""


class AgentTimeoutError(AgentRuntimeError):
    """Agent 处理超时。"""


class AgentExecutionError(AgentRuntimeError):
    """Agent 处理过程中抛出的业务异常（已被隔离）。"""


class ProtocolError(AgentRuntimeError):
    """协议校验 / 版本不兼容错误。"""


class ReferenceError_(AgentRuntimeError):
    """Artifact / state / memory 引用失效。"""


__all__ = [
    "AgentRuntimeError",
    "AgentTimeoutError",
    "AgentExecutionError",
    "ProtocolError",
    "ReferenceError_",
]
