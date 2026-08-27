"""Demo 场景：多步事实 QA + 计算。

用于 P1 验证运行时端到端可用。任务确定性、可自动验收。
"""

from __future__ import annotations

from agent_runtime.runtime.task import Task, VerdictResult


def make_demo_task() -> Task:
    """构造一个对一组事实求和的多步任务。

    知识库（facts）包含较多带描述的条目，模拟真实协作中需要在 Agent 间传递的
    「大上下文」。基线模式会反复内联搬运整个知识库；引用模式只传 artifact 引用，
    因此能体现通信开销的差异。
    """
    facts: dict = {"a": 3, "b": 4, "c": 5, "d": 10}
    # 噪声条目：扩大知识库规模（模拟真实上下文），与答案无关。
    for i in range(30):
        facts[f"doc_{i}"] = (
            f"Reference document {i}: this entry describes background knowledge "
            f"that an agent might need to inspect while retrieving evidence."
        )
    operands = ["a", "b", "c"]
    expected_value = sum(facts[k] for k in operands)

    def verifier(outputs: dict) -> VerdictResult:
        ok = outputs.get("answer") == expected_value
        return VerdictResult(
            success=ok,
            quality=1.0 if ok else 0.0,
            detail={"answer": outputs.get("answer"), "expected": expected_value},
        )

    return Task(
        topic="demo-sum",
        description="Compute the sum of selected facts a, b, c.",
        payload={"facts": facts, "question": "sum", "operands": operands},
        expected={"answer": expected_value},
        verifier=verifier,
        tags=["demo", "arithmetic"],
    )


__all__ = ["make_demo_task"]
