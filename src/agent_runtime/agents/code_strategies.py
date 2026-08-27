"""可复用的代码修复 / 改造策略（procedural 知识）。

每个策略是对 Python 源码的确定性变换。策略名本身即可作为「过程性记忆」在相似任务
间复用（如 A1 学到的修复策略用于 A2，B1 的改造规范用于 B2），而无需重新推导。
"""

from __future__ import annotations

import re

_RETURN_RE = re.compile(r"^(?P<indent>[ \t]+)return (?P<expr>.+)$", re.MULTILINE)


def guard_zero_division(code: str) -> str:
    """为函数返回语句增加 ZeroDivisionError 防护（相似缺陷修复）。"""

    def repl(m: re.Match) -> str:
        indent = m.group("indent")
        expr = m.group("expr")
        return (
            f"{indent}try:\n"
            f"{indent}    return {expr}\n"
            f"{indent}except ZeroDivisionError:\n"
            f"{indent}    return None"
        )

    return _RETURN_RE.sub(repl, code, count=1)


def add_logging_and_exception(code: str) -> str:
    """为函数增加日志与异常处理（重复工程改造规范）。"""

    def repl(m: re.Match) -> str:
        indent = m.group("indent")
        expr = m.group("expr")
        return (
            f"{indent}import logging\n"
            f"{indent}try:\n"
            f"{indent}    logging.getLogger(__name__).info('invoke')\n"
            f"{indent}    return {expr}\n"
            f"{indent}except Exception:\n"
            f"{indent}    logging.getLogger(__name__).exception('failed')\n"
            f"{indent}    return None"
        )

    return _RETURN_RE.sub(repl, code, count=1)


STRATEGIES = {
    "guard_zero_division": guard_zero_division,
    "add_logging_and_exception": add_logging_and_exception,
}


def apply_strategy(strategy: str, code: str) -> str | None:
    """应用命名策略；未知策略返回 None。"""
    fn = STRATEGIES.get(strategy)
    if fn is None:
        return None
    return fn(code)


__all__ = ["STRATEGIES", "apply_strategy"]
