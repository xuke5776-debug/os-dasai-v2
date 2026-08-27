"""编排器：驱动一次多 Agent 协作任务的端到端执行。

P1 实现线性流水线 Planner → Retriever → Executor → Reviewer，并在每个阶段之间
通过 `Channel` 投递携带内容的消息（用于通信开销计量）。P2 将引入基于 plan DAG 的
依赖调度与注册/能力发现。
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from typing import Any

from agent_runtime.observability.metrics import MetricsSnapshot
from agent_runtime.protocol.idempotency import IdempotencyCache
from agent_runtime.protocol.message import ActionType, AgentMessage, MessageStatus
from agent_runtime.registry.registry import AgentRegistry
from agent_runtime.runtime.agent import BaseAgent
from agent_runtime.runtime.context import RunContext
from agent_runtime.runtime.errors import ProtocolError
from agent_runtime.runtime.task import Task


@dataclass
class RunResult:
    """一次任务运行的结果汇总。"""

    task_id: str
    mode: str
    success: bool
    quality: float
    outputs: dict[str, Any]
    metrics: MetricsSnapshot
    error: dict[str, Any] | None = None
    messages: list[AgentMessage] = field(default_factory=list)


@dataclass
class StageInput:
    """某阶段入站消息所携带的内容与引用。

    - `params` 进入消息的 input_parameters；
    - `artifact_refs` / `state_ref` 进入消息的引用字段（不内联全文）。
    """

    params: dict[str, Any] = field(default_factory=dict)
    artifact_refs: list[str] = field(default_factory=list)
    state_ref: str | None = None


# 流水线阶段：(阶段名, 所需能力)。运行时通过能力发现解析到具体 Agent。
PIPELINE_STAGES: list[tuple[str, str]] = [
    ("planner", "task_planning"),
    ("retriever", "retrieval"),
    ("executor", "execute"),
    ("reviewer", "review"),
]


class Orchestrator:
    """编排多个 Agent 完成任务。

    启动时对每个 Agent 进行握手与注册，运行时通过「能力发现」把流水线阶段解析到
    具体 Agent，并对入站消息做幂等去重（重复请求复用缓存结果）。
    """

    PIPELINE = [name for name, _ in PIPELINE_STAGES]

    def __init__(self, agents: dict[str, BaseAgent]) -> None:
        self.agents = agents
        self.registry = AgentRegistry()
        # 握手 + 注册（协议版本协商）。
        for agent in agents.values():
            result = self.registry.handshake(agent.card())
            if not result.accepted:
                raise ProtocolError(f"Agent {agent.name} 握手失败: {result.reason}")
        # 能力发现：把每个阶段解析到拥有相应能力的 Agent。
        self._resolved: dict[str, str] = {}
        for stage, capability in PIPELINE_STAGES:
            candidates = self.registry.discover(capability)
            if not candidates:
                raise ValueError(f"无 Agent 提供能力 '{capability}'（阶段 {stage}）")
            self._resolved[stage] = candidates[0]

    async def run_task(self, task: Task, ctx: RunContext) -> RunResult:
        ctx.task_id = task.task_id
        ctx.blackboard["task"] = task
        idem = IdempotencyCache()
        ctx.metrics.start()

        for agent in self.agents.values():
            await agent.on_start(ctx)

        prev_source = "orchestrator"
        # 各阶段入站消息所携带的内容与引用（驱动通信开销计量）。
        stage_inputs: dict[str, StageInput] = {
            "planner": self._initial_planner_input(task, ctx),
            "retriever": StageInput(),
            "executor": StageInput(),
            "reviewer": StageInput(),
        }

        last_result: AgentMessage | None = None
        aborted = False
        for idx, (stage, _capability) in enumerate(PIPELINE_STAGES):
            name = self._resolved[stage]
            agent = self.agents[name]
            si = stage_inputs[stage]
            inbound = AgentMessage(
                trace_id=ctx.trace_id,
                task_id=ctx.task_id,
                step_id=f"s{idx}",
                source_agent=prev_source,
                target_agent=name,
                action_type=_ACTION_FOR_STAGE[stage],
                capability=agent.capabilities[0] if agent.capabilities else "",
                input_parameters=dict(si.params),
                artifact_references=list(si.artifact_refs),
                state_reference=si.state_ref,
                status=MessageStatus.PENDING,
            )
            ctx.channel.send(inbound)

            # 幂等：相同请求复用缓存结果，避免重复计算。
            if idem.seen(inbound):
                cached = idem.get(inbound)
                if cached is not None:
                    result = cached
                else:
                    result = await agent.run(inbound, ctx)
            else:
                result = await agent.run(inbound, ctx)
                idem.remember(inbound, result)

            last_result = result
            ctx.metrics.sample_resources()

            if result.status in (MessageStatus.ERROR, MessageStatus.TIMEOUT):
                aborted = True
                break

            self._propagate(stage, result, stage_inputs, ctx)
            prev_source = name

        # 最终结果消息（reviewer → orchestrator）。
        if last_result is not None:
            final = AgentMessage(
                trace_id=ctx.trace_id,
                task_id=ctx.task_id,
                step_id="final",
                source_agent=prev_source,
                target_agent="orchestrator",
                action_type=ActionType.RESULT,
                result=last_result.result,
                status=last_result.status,
            )
            ctx.channel.send(final)

        for agent in self.agents.values():
            await agent.on_stop(ctx)

        ctx.metrics.stop()

        # 释放本任务的非文本状态缓冲（共享内存句柄），避免资源泄漏 / 内存持续增长。
        # state_exchange 为 per-task 资源；共享记忆由调用方持有，不在此关闭。
        if ctx.state_exchange is not None:
            with contextlib.suppress(Exception):
                ctx.state_exchange.close()

        outputs = {"answer": ctx.blackboard.get("answer")}
        snapshot = ctx.metrics.snapshot
        error = last_result.error if (aborted and last_result) else None
        if aborted and not error:
            error = {"type": "aborted", "stage": prev_source}
        return RunResult(
            task_id=ctx.task_id,
            mode=ctx.mode,
            success=snapshot.task_success,
            quality=snapshot.task_quality,
            outputs=outputs,
            metrics=snapshot,
            error=error,
            messages=list(ctx.channel.history),
        )

    def _initial_planner_input(self, task: Task, ctx: RunContext) -> StageInput:
        """Planner 入站内容。

        - 基线（无状态交换）：直接搬运完整任务负载（含事实表），模拟「上下文全量透传」；
        - 优化（状态交换 + 引用）：仅传递规划所需的小字段，事实表不进入消息。
        """
        if ctx.use_state_exchange:
            return StageInput(
                params={
                    "description": task.description,
                    "question": task.payload.get("question"),
                    "operands": task.payload.get("operands", []),
                    "defect": task.payload.get("defect", ""),
                }
            )
        return StageInput(params={"description": task.description, "payload": task.payload})

    def _propagate(
        self,
        name: str,
        result: AgentMessage,
        stage_inputs: dict[str, StageInput],
        ctx: RunContext,
    ) -> None:
        """把当前阶段的产出填充到下一阶段的入站参数。"""
        res = result.result or {}
        task: Task = ctx.blackboard["task"]
        optimized = (
            ctx.use_state_exchange
            and ctx.state_exchange is not None
            and ctx.artifact_store is not None
        )

        if name == "planner":
            plan = res.get("plan", {})
            facts = task.payload.get("facts", {})
            if optimized:
                assert ctx.state_exchange is not None and ctx.artifact_store is not None
                # 计划以非文本状态承载，事实表以 artifact 承载，消息仅传引用。
                state_ref = ctx.state_exchange.put_plan_state(plan)
                ctx.metrics.record_state_transfer(state_ref.nbytes)
                facts_ref = ctx.artifact_store.put(facts, summary=f"facts(n={len(facts)})")
                stage_inputs["retriever"] = StageInput(
                    params={"plan_ref": state_ref.uri, "facts_ref": facts_ref.uri},
                    artifact_refs=[facts_ref.uri],
                    state_ref=state_ref.uri,
                )
            else:
                stage_inputs["retriever"] = StageInput(params={"plan": plan, "facts": facts})
        elif name == "retriever":
            plan = ctx.blackboard.get("plan", {})
            evidence = res.get("evidence", {})
            if optimized:
                assert ctx.state_exchange is not None and ctx.artifact_store is not None
                state_ref = ctx.state_exchange.put_plan_state(plan)
                ctx.metrics.record_state_transfer(state_ref.nbytes)
                ev_ref = ctx.artifact_store.put(evidence, summary=f"evidence(n={len(evidence)})")
                stage_inputs["executor"] = StageInput(
                    params={"plan_ref": state_ref.uri, "evidence_ref": ev_ref.uri},
                    artifact_refs=[ev_ref.uri],
                    state_ref=state_ref.uri,
                )
            else:
                stage_inputs["executor"] = StageInput(params={"plan": plan, "evidence": evidence})
        elif name == "executor":
            stage_inputs["reviewer"] = StageInput(
                params={"value": res.get("value"), "topic": task.topic}
            )


_ACTION_FOR_STAGE = {
    "planner": ActionType.PLAN,
    "retriever": ActionType.RETRIEVE,
    "executor": ActionType.EXECUTE,
    "reviewer": ActionType.REVIEW,
}


__all__ = ["Orchestrator", "RunResult"]
