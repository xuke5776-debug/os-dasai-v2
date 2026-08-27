"""任务组 B：重复软件工程改造（增加日志 + 异常处理）。

B1 对模块 `process_a` 执行「加日志 + 异常处理」改造（提供改造规范/策略）；
B2 对相邻模块 `process_b` 执行相同规范的改造（**不提供策略**，需复用 B1 的过程性记忆）。
两者均由沙箱运行测试自动验收。
"""

from __future__ import annotations

from agent_runtime.runtime.task import Task, VerdictResult


def _verifier(outputs: dict) -> VerdictResult:
    ok = outputs.get("answer") is True
    return VerdictResult(success=ok, quality=1.0 if ok else 0.0)


def make_b1() -> Task:
    module = "def process_a(x):\n    return int(x)\n"
    test = 'assert process_a("5") == 5\nassert process_a("abc") is None\n'
    return Task(
        topic="add-logging-exception",
        description="Add logging and exception handling to process_a.",
        payload={
            "question": "codefix",
            "operands": ["module", "test", "strategy"],
            "defect": "needs_robustness",
            "facts": {
                "module": module,
                "test": test,
                "strategy": "add_logging_and_exception",
            },
        },
        expected={"answer": True},
        verifier=_verifier,
        tags=["refactor", "needs_robustness"],
    )


def make_b2(parent_task_id: str | None = None) -> Task:
    module = "def process_b(x):\n    return int(x) + 1\n"
    test = 'assert process_b("5") == 6\nassert process_b("abc") is None\n'
    return Task(
        topic="add-logging-exception",
        description="Apply the same logging/exception refactor to process_b (reuse strategy).",
        payload={
            "question": "codefix",
            "operands": ["module", "test", "strategy"],
            "defect": "needs_robustness",
            "facts": {"module": module, "test": test},
        },
        expected={"answer": True},
        verifier=_verifier,
        tags=["refactor", "needs_robustness"],
        parent_task_id=parent_task_id,
    )


def make_group() -> list[Task]:
    b1 = make_b1()
    b2 = make_b2(parent_task_id=b1.task_id)
    return [b1, b2]


__all__ = ["make_b1", "make_b2", "make_group"]
