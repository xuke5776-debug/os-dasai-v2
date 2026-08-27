"""运行上下文：在一次任务运行中贯穿所有模块的共享依赖与服务。"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np

from agent_runtime.config import Config
from agent_runtime.observability.metrics import MetricsCollector
from agent_runtime.providers.base import EmbeddingProvider, LLMProvider, LLMResponse
from agent_runtime.runtime.channel import Channel

if TYPE_CHECKING:  # 避免循环导入；这些服务在后续阶段注入
    from agent_runtime.artifact_store.store import ArtifactStore
    from agent_runtime.memory.store import MemoryStore
    from agent_runtime.sandbox.executor import CodeActExecutor
    from agent_runtime.state_exchange.exchange import StateExchange


@dataclass
class RunContext:
    """一次任务运行的上下文。"""

    config: Config
    llm: LLMProvider
    embedding: EmbeddingProvider
    metrics: MetricsCollector
    channel: Channel
    mode: str  # "text" | "structured"
    task_id: str
    trace_id: str = field(default_factory=lambda: f"trace_{uuid.uuid4().hex[:12]}")
    rng: np.random.Generator = field(default_factory=lambda: np.random.default_rng(42))
    logger: Any = None

    # 跨 Agent 共享的黑板（步骤结果）。
    blackboard: dict[str, Any] = field(default_factory=dict)

    # 实验开关
    use_memory: bool = False
    use_state_exchange: bool = False

    # 可选服务（后续阶段注入）
    artifact_store: ArtifactStore | None = None
    memory: MemoryStore | None = None
    state_exchange: StateExchange | None = None
    sandbox: CodeActExecutor | None = None

    def call_llm(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """调用 LLM 并自动记录 token 指标。"""
        resp = self.llm.complete(
            prompt,
            system=system,
            temperature=temperature if temperature is not None else self.config.llm.temperature,
            max_tokens=max_tokens if max_tokens is not None else self.config.llm.max_tokens,
        )
        self.metrics.record_llm(resp.prompt_tokens, resp.completion_tokens)
        return resp

    def record_tool(self, signature: str) -> None:
        """记录一次工具调用（用于重复计算统计）。"""
        self.metrics.record_tool_call(signature)


__all__ = ["RunContext"]
