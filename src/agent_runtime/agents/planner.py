"""Planner Agent：任务规划 / 分解。"""

from __future__ import annotations

from agent_runtime.protocol.message import ActionType, AgentMessage
from agent_runtime.runtime.agent import BaseAgent, RetryPolicy
from agent_runtime.runtime.context import RunContext


class PlannerAgent(BaseAgent):
    """将任务分解为可执行的计划（operation + operands）。

    规划逻辑是确定性的（由任务输入决定），同时调用一次 LLM 以产出规划理由，
    使 token 统计反映真实的规划开销。
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(
            name="planner",
            capabilities=["task_planning", "decompose"],
            actions=[ActionType.PLAN],
            retry=kwargs.pop("retry", RetryPolicy(max_retries=2)),
            **kwargs,
        )

    async def handle(self, message: AgentMessage, ctx: RunContext) -> AgentMessage:
        params = message.input_parameters
        description = params.get("description", "")
        payload = params.get("payload", {})

        ctx.call_llm(
            f"Decompose the following task into operation and operands: {description}",
            system="You are a meticulous task planner.",
        )

        # 支持两种入站形态：内联完整 payload（基线）或扁平的小字段（引用模式）。
        src = payload if payload else params
        operation = src.get("question")
        operands = src.get("operands")
        defect = src.get("defect")
        plan = {
            "operation": operation or "noop",
            "operands": list(operands or []),
            "defect": defect or "",
        }
        ctx.blackboard["plan"] = plan
        return self.reply(
            message,
            ctx,
            action_type=ActionType.PLAN,
            capability="task_planning",
            result={"plan": plan},
            confidence=0.95,
        )


__all__ = ["PlannerAgent"]
