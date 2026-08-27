"""任务模型。

`Task` 描述一次多步骤协作任务的输入与验收方式。场景（scenarios）通过构造
`Task` 来驱动运行时，并提供确定性的自动验收函数，保证实验可复现。
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class VerdictResult:
    """任务自动验收结果。"""

    success: bool
    quality: float  # 0.0 ~ 1.0
    detail: dict[str, Any] = field(default_factory=dict)


# 验收函数：输入最终输出 dict，返回 VerdictResult。
Verifier = Callable[[dict[str, Any]], VerdictResult]


@dataclass
class Task:
    """一次协作任务。"""

    topic: str
    description: str
    payload: dict[str, Any] = field(default_factory=dict)
    expected: dict[str, Any] = field(default_factory=dict)
    verifier: Verifier | None = None
    task_id: str = field(default_factory=lambda: f"task_{uuid.uuid4().hex[:10]}")
    # 关联任务：用于跨任务记忆复用验证（如 A1->A2）。
    parent_task_id: str | None = None
    tags: list[str] = field(default_factory=list)

    def verify(self, outputs: dict[str, Any]) -> VerdictResult:
        """对输出进行自动验收。"""
        if self.verifier is not None:
            return self.verifier(outputs)
        # 默认验收：将 outputs['answer'] 与 expected['answer'] 比较。
        ans = outputs.get("answer")
        exp = self.expected.get("answer")
        if exp is None:
            return VerdictResult(success=bool(ans), quality=1.0 if ans else 0.0)
        ok = ans == exp
        return VerdictResult(
            success=ok,
            quality=1.0 if ok else 0.0,
            detail={"answer": ans, "expected": exp},
        )


__all__ = ["Task", "VerdictResult", "Verifier"]
