"""Agent 基类：生命周期、状态机、超时、重试与失败隔离。"""

from __future__ import annotations

import abc
import asyncio
import time
from dataclasses import dataclass
from enum import Enum

from agent_runtime.protocol.message import ActionType, AgentMessage, MessageStatus
from agent_runtime.runtime.context import RunContext


class AgentState(str, Enum):
    """Agent 生命周期状态。"""

    CREATED = "created"
    READY = "ready"
    RUNNING = "running"
    WAITING = "waiting"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMEOUT = "timeout"
    TERMINATED = "terminated"


@dataclass
class RetryPolicy:
    """重试策略（确定性：默认零退避以保证可复现）。"""

    max_retries: int = 2
    backoff_sec: float = 0.0


class BaseAgent(abc.ABC):
    """所有 Agent 的抽象基类。

    子类实现 `handle`；外部统一通过 `run` 调用，由 `run` 负责状态转换、超时控制、
    重试与失败隔离（失败时返回 error 消息，而非向上抛出导致整个运行时崩溃）。
    """

    def __init__(
        self,
        name: str,
        capabilities: list[str],
        *,
        actions: list[ActionType] | None = None,
        timeout_sec: float = 10.0,
        retry: RetryPolicy | None = None,
    ) -> None:
        self.name = name
        self.capabilities = capabilities
        self.actions = actions or []
        self.timeout_sec = timeout_sec
        self.retry = retry or RetryPolicy()
        self._state = AgentState.CREATED

    @property
    def state(self) -> AgentState:
        return self._state

    def card(self):
        """生成用于注册/握手/能力发现的 Agent 名片。"""
        from agent_runtime.registry.capability import AgentCard

        return AgentCard(
            agent_name=self.name,
            capabilities=list(self.capabilities),
            actions=[a.value for a in self.actions],
            description=self.__class__.__doc__ or "",
        )

    # ----- 生命周期钩子（子类可覆盖） -----
    async def on_start(self, ctx: RunContext) -> None:
        self._state = AgentState.READY

    async def on_stop(self, ctx: RunContext) -> None:
        self._state = AgentState.TERMINATED

    # ----- 业务处理（子类实现） -----
    @abc.abstractmethod
    async def handle(self, message: AgentMessage, ctx: RunContext) -> AgentMessage:
        """处理一条入站消息并返回结果消息。"""
        raise NotImplementedError

    # ----- 统一执行包装 -----
    async def run(self, message: AgentMessage, ctx: RunContext) -> AgentMessage:
        """带超时/重试/失败隔离地执行 handle。"""
        attempt = 0
        last_error: dict[str, str] | None = None
        while True:
            self._state = AgentState.RUNNING
            start = time.perf_counter()
            try:
                result = await asyncio.wait_for(self.handle(message, ctx), timeout=self.timeout_sec)
                ctx.metrics.record_step_latency(time.perf_counter() - start)
                ctx.metrics.sample_resources()
                self._state = AgentState.SUCCEEDED
                return result
            except asyncio.TimeoutError:
                ctx.metrics.record_error()
                self._state = AgentState.TIMEOUT
                last_error = {"type": "timeout", "agent": self.name}
            except Exception as exc:  # noqa: BLE001 - 失败隔离：捕获所有异常
                ctx.metrics.record_error()
                self._state = AgentState.FAILED
                last_error = {"type": exc.__class__.__name__, "msg": str(exc)}

            attempt += 1
            if attempt > self.retry.max_retries:
                ctx.metrics.record_degradation()
                return self._error_message(message, ctx, last_error or {})
            ctx.metrics.record_degradation()
            if self.retry.backoff_sec > 0:
                await asyncio.sleep(self.retry.backoff_sec)

    def _error_message(
        self, inbound: AgentMessage, ctx: RunContext, error: dict[str, str]
    ) -> AgentMessage:
        status = MessageStatus.TIMEOUT if error.get("type") == "timeout" else MessageStatus.ERROR
        return AgentMessage(
            trace_id=ctx.trace_id,
            task_id=ctx.task_id,
            step_id=inbound.step_id,
            source_agent=self.name,
            target_agent=inbound.source_agent or "orchestrator",
            action_type=ActionType.ERROR,
            capability="",
            status=status,
            error=error,
            confidence=0.0,
        )

    def reply(
        self,
        inbound: AgentMessage,
        ctx: RunContext,
        *,
        action_type: ActionType,
        result: dict | None = None,
        status: MessageStatus = MessageStatus.OK,
        capability: str = "",
        confidence: float | None = None,
        artifact_references: list[str] | None = None,
        evidence_references: list[str] | None = None,
        state_reference: str | None = None,
    ) -> AgentMessage:
        """构造一条回复消息（填充 trace/task/step 等公共字段）。"""
        return AgentMessage(
            trace_id=ctx.trace_id,
            task_id=ctx.task_id,
            step_id=inbound.step_id,
            source_agent=self.name,
            target_agent=inbound.source_agent or "orchestrator",
            action_type=action_type,
            capability=capability or (self.capabilities[0] if self.capabilities else ""),
            result=result,
            status=status,
            confidence=confidence,
            artifact_references=artifact_references or [],
            evidence_references=evidence_references or [],
            state_reference=state_reference,
        )


__all__ = ["BaseAgent", "AgentState", "RetryPolicy"]
