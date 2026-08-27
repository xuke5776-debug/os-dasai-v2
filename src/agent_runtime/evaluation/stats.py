"""统计聚合：均值 / 标准差 / P50 / P95。"""

from __future__ import annotations

from typing import Any

import numpy as np


def summarize(values: list[float]) -> dict[str, float]:
    """对一组数值给出统计摘要。"""
    if not values:
        return {"mean": 0.0, "std": 0.0, "p50": 0.0, "p95": 0.0, "min": 0.0, "max": 0.0, "n": 0}
    arr = np.asarray(values, dtype=float)
    return {
        "mean": float(arr.mean()),
        "std": float(arr.std(ddof=0)),
        "p50": float(np.percentile(arr, 50)),
        "p95": float(np.percentile(arr, 95)),
        "min": float(arr.min()),
        "max": float(arr.max()),
        "n": int(arr.size),
    }


def summarize_runs(runs: list[dict[str, Any]], keys: list[str]) -> dict[str, dict[str, float]]:
    """对多次运行的指标字典按 key 聚合统计。"""
    out: dict[str, dict[str, float]] = {}
    for key in keys:
        out[key] = summarize([float(r.get(key, 0) or 0) for r in runs])
    return out


__all__ = ["summarize", "summarize_runs"]
