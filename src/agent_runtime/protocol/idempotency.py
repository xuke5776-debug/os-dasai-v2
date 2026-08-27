"""幂等控制。

相同 (task_id, step_id, action_type, idempotency_key) 的请求被视为同一请求；
重复请求直接返回缓存结果，避免重复计算（也是「重复计算降低率」的机制之一）。
若消息未显式提供 idempotency_key，则基于关键字段生成稳定指纹。
"""

from __future__ import annotations

import hashlib
import json

from agent_runtime.protocol.message import AgentMessage


def fingerprint(message: AgentMessage) -> str:
    """为消息生成幂等指纹。"""
    if message.idempotency_key:
        base = f"{message.task_id}|{message.step_id}|{message.action_type.value}|{message.idempotency_key}"
    else:
        payload = json.dumps(
            message.input_parameters, sort_keys=True, ensure_ascii=False, default=str
        )
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
        base = f"{message.task_id}|{message.step_id}|{message.action_type.value}|{digest}"
    return base


class IdempotencyCache:
    """记录已处理请求及其结果。"""

    def __init__(self) -> None:
        self._store: dict[str, AgentMessage] = {}

    def seen(self, message: AgentMessage) -> bool:
        return fingerprint(message) in self._store

    def get(self, message: AgentMessage) -> AgentMessage | None:
        return self._store.get(fingerprint(message))

    def remember(self, request: AgentMessage, result: AgentMessage) -> None:
        self._store[fingerprint(request)] = result

    def clear(self) -> None:
        self._store.clear()

    def __len__(self) -> int:
        return len(self._store)


__all__ = ["IdempotencyCache", "fingerprint"]
