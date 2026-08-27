"""Retriever Agent：信息检索（事实 / 共享记忆 / 非文本状态消费）。"""

from __future__ import annotations

from typing import Any

import numpy as np

from agent_runtime.protocol.message import ActionType, AgentMessage
from agent_runtime.runtime.agent import BaseAgent
from agent_runtime.runtime.context import RunContext
from agent_runtime.runtime.errors import ReferenceError_


class RetrieverAgent(BaseAgent):
    """根据计划检索 operands 的取值。

    支持两种输入承载：
    - 内联：直接从 input_parameters 读取 plan / facts（基线）；
    - 引用：从 `state://`（plan 非文本状态）与 `artifact://`（facts）解析，
      并**真实消费**计划 embedding 对检索目标做语义排序（状态参与路由/决策）。
    引用失效时自动降级。记忆复用在 P4 接入。
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(
            name="retriever",
            capabilities=["retrieval", "memory_lookup", "semantic_search"],
            actions=[ActionType.RETRIEVE],
            **kwargs,
        )

    async def handle(self, message: AgentMessage, ctx: RunContext) -> AgentMessage:
        plan = message.input_parameters.get("plan")
        if plan is None:
            plan = self._resolve_plan(message, ctx)
        facts = message.input_parameters.get("facts")
        if facts is None:
            facts = self._resolve_facts(message, ctx)
        plan = plan or {}
        facts = facts or {}
        operands = plan.get("operands", [])

        evidence: dict[str, Any] = {}
        evidence_refs: list[str] = []
        for op in operands:
            ctx.record_tool(f"lookup:{op}")
            evidence[op] = facts.get(op)

        if ctx.use_memory and ctx.memory is not None:
            evidence_refs = self._augment_from_memory(plan, evidence, ctx)

        ctx.blackboard["evidence"] = evidence
        ctx.call_llm(
            f"Summarize retrieved evidence keys: {list(evidence.keys())}",
            system="You are an information retriever.",
        )
        return self.reply(
            message,
            ctx,
            action_type=ActionType.RETRIEVE,
            capability="retrieval",
            result={"evidence": evidence},
            evidence_references=evidence_refs,
            confidence=0.9,
        )

    def _resolve_plan(self, message: AgentMessage, ctx: RunContext) -> dict[str, Any]:
        """从非文本状态解析计划，并消费 embedding 进行语义排序。"""
        ref = message.input_parameters.get("plan_ref") or message.state_reference
        if not ref or ctx.state_exchange is None:
            return {}
        try:
            state = ctx.state_exchange.get_plan_state(ref)
        except ReferenceError_:
            ctx.metrics.record_degradation()
            return {}
        dag = dict(state["dag"])
        emb = state["embedding"]
        operands = dag.get("operands", [])
        if operands:
            # 真实消费：用 plan embedding 对检索目标做语义相似度排序。
            op_vecs = ctx.embedding.embed([str(o) for o in operands])
            sims = op_vecs @ emb
            order = list(np.argsort(-sims))
            dag["operands"] = [operands[i] for i in order]
        ctx.blackboard["state_consumed"] = True
        return dag

    def _resolve_facts(self, message: AgentMessage, ctx: RunContext) -> dict[str, Any]:
        ref = message.input_parameters.get("facts_ref")
        if not ref or ctx.artifact_store is None:
            return {}
        try:
            return ctx.artifact_store.get_json(ref)
        except ReferenceError_:
            ctx.metrics.record_degradation()
            return {}

    def _augment_from_memory(
        self, plan: dict[str, Any], evidence: dict[str, Any], ctx: RunContext
    ) -> list[str]:
        """从共享记忆检索可复用经验。

        - 命中「同一子问题」（签名一致）→ 复用结论（answer），下游跳过重复计算；
        - 命中「相似子问题」（操作相同、签名不同）→ 复用策略/模板（solution），
          如 A1 的修复策略用于 A2、B1 的改造规范用于 B2。
        记录 Retrieved / Used 命中；效果反馈（Effective/Harmful）由 Reviewer 验收后写回。
        """
        if ctx.memory is None:
            return []
        from agent_runtime.memory.signature import task_signature

        operation = plan.get("operation") or "noop"
        operands = plan.get("operands", [])
        defect = plan.get("defect") or ""
        signature = task_signature(operation, evidence)
        ctx.blackboard["signature"] = signature

        query = f"operation {operation} defect {defect} operands {operands}"
        keywords = [str(operation), *([str(defect)] if defect else []), *[str(o) for o in operands]]
        hits = ctx.memory.retrieve(query, keywords=keywords, top_k=3)
        ctx.metrics.record_memory(retrieved=len(hits))

        refs = [f"memory://{h.record.memory_id}" for h in hits]
        reused_ids: list[str] = []
        best = next(
            (
                h
                for h in hits
                if h.record.payload.get("operation") == operation
                and h.record.success_feedback is not False
            ),
            None,
        )
        if best is not None:
            ctx.memory.mark_used(best.record.memory_id)
            ctx.metrics.record_memory(used=1)
            reused_ids.append(best.record.memory_id)
            payload = best.record.payload
            if payload.get("signature") == signature:
                ctx.blackboard["reused_answer"] = payload.get("answer")
            elif payload.get("solution") is not None:
                ctx.blackboard["reused_solution"] = payload.get("solution")

        ctx.blackboard["reused_memory_ids"] = reused_ids
        return refs


__all__ = ["RetrieverAgent"]
