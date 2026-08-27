"""Reviewer / Summarizer Agent：审查结果、判定成败、沉淀共享记忆。"""

from __future__ import annotations

from typing import Any

from agent_runtime.protocol.message import ActionType, AgentMessage, MessageStatus
from agent_runtime.runtime.agent import BaseAgent
from agent_runtime.runtime.context import RunContext


class ReviewerSummarizerAgent(BaseAgent):
    """对执行结果进行审查与总结，并将经验沉淀为共享记忆。

    任务的自动验收（task.verify）由运行上下文持有的任务对象提供，不通过 Agent 间
    消息传输（它属于评测/真值，而非协作内容）。记忆沉淀在 P4 接入。
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(
            name="reviewer",
            capabilities=["review", "summarize", "memorize"],
            actions=[ActionType.REVIEW, ActionType.SUMMARIZE, ActionType.MEMORIZE],
            **kwargs,
        )

    async def handle(self, message: AgentMessage, ctx: RunContext) -> AgentMessage:
        value = message.input_parameters.get("value")
        task = ctx.blackboard.get("task")

        outputs: dict[str, Any] = {"answer": value}
        if task is not None:
            verdict = task.verify(outputs)
        else:  # 无任务对象时的保守判定
            from agent_runtime.runtime.task import VerdictResult

            verdict = VerdictResult(success=value is not None, quality=1.0 if value else 0.0)

        ctx.metrics.set_result(verdict.success, verdict.quality)
        ctx.blackboard["answer"] = value
        ctx.blackboard["verdict"] = verdict

        ctx.call_llm(
            f"Summarize the task outcome (success={verdict.success}).",
            system="You are a reviewer that writes concise, reusable summaries.",
        )

        # 记忆沉淀接入点（P4 实现）。
        if ctx.use_memory and ctx.memory is not None:
            self._memorize(task, value, verdict, ctx)

        return self.reply(
            message,
            ctx,
            action_type=ActionType.REVIEW,
            capability="review",
            result={"answer": value, "success": verdict.success, "quality": verdict.quality},
            status=MessageStatus.OK if verdict.success else MessageStatus.ERROR,
            confidence=0.9 if verdict.success else 0.3,
        )

    def _memorize(self, task, value, verdict, ctx: RunContext) -> None:
        """将结论沉淀为共享记忆，并对复用过的记忆写回效果反馈。"""
        from agent_runtime.memory.models import MemoryRecord, MemoryType

        if ctx.memory is None:
            return

        # 复用效果反馈（Effective / Harmful Hit）。
        for mid in ctx.blackboard.get("reused_memory_ids", []):
            ctx.memory.record_feedback(mid, effective=verdict.success)
            if verdict.success:
                ctx.metrics.record_memory(effective=1)
            else:
                ctx.metrics.record_memory(harmful=1)

        plan = ctx.blackboard.get("plan", {})
        operands = plan.get("operands", [])
        defect = plan.get("defect") or ""
        record = MemoryRecord(
            source_agent=self.name,
            task_topic=task.topic if task else "unknown",
            summary=f"operation {plan.get('operation')} over {operands} -> {value}",
            memory_type=MemoryType.PROCEDURAL,
            tags=list(task.tags) if task else [],
            keywords=[
                str(plan.get("operation")),
                *([str(defect)] if defect else []),
                *[str(o) for o in operands],
            ],
            confidence=0.9 if verdict.success else 0.3,
            quality_score=0.9 if verdict.success else 0.2,
            provenance={
                "trace_id": ctx.trace_id,
                "agents": ["planner", "retriever", "executor", "reviewer"],
            },
            task_id=ctx.task_id,
            success_feedback=verdict.success,
            payload={
                "operation": plan.get("operation"),
                "operands": operands,
                "answer": value,
                "solution": ctx.blackboard.get("solution_used"),
                "signature": ctx.blackboard.get("signature"),
                "defect": defect,
            },
        )
        ctx.memory.write(record)


__all__ = ["ReviewerSummarizerAgent"]
