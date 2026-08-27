"""任务组 A：相似缺陷修复（零除防护）。

A1 修复 `safe_divide` 的零除缺陷（提供修复策略）；A2 修复相邻模块 `safe_modulo`
的同类缺陷（**不提供策略**，需复用 A1 沉淀的过程性记忆）。两者均由沙箱运行测试自动验收。
"""

from __future__ import annotations

from agent_runtime.runtime.task import Task, VerdictResult


def _verifier(outputs: dict) -> VerdictResult:
    ok = outputs.get("answer") is True
    return VerdictResult(success=ok, quality=1.0 if ok else 0.0)


def make_a1() -> Task:
    module = "def safe_divide(a, b):\n    return a / b\n"
    test = "assert safe_divide(6, 3) == 2\nassert safe_divide(1, 0) is None\n"
    return Task(
        topic="fix-zero-division",
        description="Fix the zero-division defect in safe_divide.",
        payload={
            "question": "codefix",
            "operands": ["module", "test", "strategy"],
            "defect": "zero_division",
            "facts": {
                "module": module,
                "test": test,
                "strategy": "guard_zero_division",
            },
        },
        expected={"answer": True},
        verifier=_verifier,
        tags=["bugfix", "zero_division"],
    )


def make_a2(parent_task_id: str | None = None) -> Task:
    module = "def safe_modulo(a, b):\n    return a % b\n"
    test = "assert safe_modulo(7, 3) == 1\nassert safe_modulo(1, 0) is None\n"
    return Task(
        topic="fix-zero-division",
        description="Fix the zero-division defect in safe_modulo (reuse prior strategy).",
        payload={
            "question": "codefix",
            "operands": ["module", "test", "strategy"],
            "defect": "zero_division",
            # 注意：不提供 strategy，迫使系统复用 A1 的过程性记忆。
            "facts": {"module": module, "test": test},
        },
        expected={"answer": True},
        verifier=_verifier,
        tags=["bugfix", "zero_division"],
        parent_task_id=parent_task_id,
    )


def make_group() -> list[Task]:
    a1 = make_a1()
    a2 = make_a2(parent_task_id=a1.task_id)
    return [a1, a2]


__all__ = ["make_a1", "make_a2", "make_group"]
