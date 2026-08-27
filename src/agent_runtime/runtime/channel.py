"""通信通道：投递消息并计量通信开销。

P1 提供进程内逻辑通道（直接计量 + 记录日志）。P2/P3 在此基础上接入 UDS 传输与
引用计量。无论模式如何，所有消息都经过通道，保证开销统计口径一致。
"""

from __future__ import annotations

from agent_runtime.observability.metrics import MetricsCollector
from agent_runtime.protocol.message import AgentMessage
from agent_runtime.protocol.serialization import measure
from agent_runtime.providers.tokenizer import Tokenizer


class Channel:
    """逻辑通信通道。"""

    def __init__(
        self,
        mode: str,
        metrics: MetricsCollector,
        tokenizer: Tokenizer,
        logger=None,
    ) -> None:
        if mode not in ("text", "structured"):
            raise ValueError(f"未知通信模式: {mode}")
        self.mode = mode
        self.metrics = metrics
        self.tokenizer = tokenizer
        self.logger = logger
        self.history: list[AgentMessage] = []

    def send(self, message: AgentMessage) -> AgentMessage:
        """投递并计量一条消息，返回原消息（逻辑投递）。"""
        wire, tokens, chars = measure(message, self.mode, self.tokenizer)
        self.metrics.record_message(tokens=tokens, chars=chars)
        if message.artifact_references:
            self.metrics.record_artifact_ref(len(message.artifact_references))
        self.history.append(message)
        if self.logger is not None:
            self.logger.debug(
                "channel.send",
                extra={
                    "mode": self.mode,
                    "tokens": tokens,
                    "chars": chars,
                    "msg": message.short(),
                },
            )
        return message


__all__ = ["Channel"]
