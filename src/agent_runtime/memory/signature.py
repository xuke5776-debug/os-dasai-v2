"""任务签名：用于判定记忆复用是「同一子问题」还是「相似子问题」。

- 签名一致 → 同一子问题 → 可直接复用结论（answer）；
- 操作相同但签名不同 → 相似子问题 → 复用策略/模板（solution）。
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def task_signature(operation: str, evidence: dict[str, Any]) -> str:
    """基于操作 + 已解析证据值生成稳定签名。"""
    items = sorted((k, str(v)) for k, v in evidence.items() if v is not None)
    raw = f"{operation}|" + json.dumps(items, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


__all__ = ["task_signature"]
