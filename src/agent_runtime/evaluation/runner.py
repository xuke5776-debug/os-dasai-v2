"""基准实验运行器。

运行 4 组主实验（A 文本基线 / B 结构化 / C 结构化+状态 / D 全系统）与若干消融，
统计 16 项指标 + 派生指标，按时间戳落盘到 `results/<ts>-<suite>/`（不覆盖旧实验）。
"""

from __future__ import annotations

import asyncio
import json
import platform
import sys
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from agent_runtime.config import load_config
from agent_runtime.evaluation.stats import summarize_runs
from agent_runtime.memory.store import MemoryStore
from agent_runtime.observability.metrics import MetricsSnapshot
from agent_runtime.providers.factory import build_embedding
from agent_runtime.runtime.builder import build_context, build_default_agents
from agent_runtime.runtime.orchestrator import Orchestrator
from agent_runtime.runtime.task import Task
from agent_runtime.sandbox.capabilities import summary as capability_summary

SUM_KEYS = [
    "message_count",
    "text_tokens",
    "text_chars",
    "state_transfers",
    "state_bytes",
    "artifact_refs",
    "llm_calls",
    "llm_prompt_tokens",
    "llm_completion_tokens",
    "tool_calls",
    "repeated_tool_calls",
    "memory_retrieved",
    "memory_used",
    "memory_effective",
    "memory_harmful",
    "error_count",
    "degradation_count",
    "latency_sec",
]
STAT_KEYS = [*SUM_KEYS, "rss_peak_mb", "task_quality", "task_success", "total_llm_tokens"]


@dataclass(frozen=True)
class ExperimentConfig:
    id: str
    label: str
    mode: str
    use_state: bool
    use_memory: bool
    use_sandbox: bool


MAIN_SUITE = [
    ExperimentConfig("A", "Text Baseline", "text", False, False, False),
    ExperimentConfig("B", "Structured Protocol", "structured", False, False, False),
    ExperimentConfig("C", "Structured + State", "structured", True, False, False),
    ExperimentConfig("D", "Full System", "structured", True, True, True),
]

ABLATION_SUITE = [
    ExperimentConfig("D", "Full System", "structured", True, True, True),
    ExperimentConfig("D-noMem", "−Shared Memory", "structured", True, False, True),
    ExperimentConfig("D-noState", "−State Exchange", "structured", False, True, True),
    ExperimentConfig("D-noSandbox", "−CodeAct Sandbox", "structured", True, True, False),
    ExperimentConfig("B", "Structured only", "structured", False, False, False),
    ExperimentConfig("A", "Text Baseline", "text", False, False, False),
]


def _default_task_factory() -> list[Task]:
    """主实验任务序列：两个相同任务，便于体现记忆复用。"""
    from scenarios.demo import make_demo_task

    return [make_demo_task(), make_demo_task()]


def _aggregate(snaps: list[MetricsSnapshot]) -> dict[str, Any]:
    agg: dict[str, Any] = dict.fromkeys(SUM_KEYS, 0.0)
    rss = 0.0
    quals: list[float] = []
    success = True
    for s in snaps:
        for k in SUM_KEYS:
            agg[k] += float(getattr(s, k))
        rss = max(rss, s.rss_peak_mb)
        quals.append(s.task_quality)
        success = success and s.task_success
    agg["rss_peak_mb"] = rss
    agg["task_quality"] = sum(quals) / len(quals) if quals else 0.0
    agg["task_success"] = 1.0 if success else 0.0
    agg["total_llm_tokens"] = agg["llm_prompt_tokens"] + agg["llm_completion_tokens"]
    return agg


def run_once(cfg_exp: ExperimentConfig, task_factory: Callable[[], list[Task]], seed: int) -> dict:
    config = load_config(load_env=False, random_seed=seed)
    tasks = task_factory()
    memory = MemoryStore(embedding=build_embedding(config)) if cfg_exp.use_memory else None
    snaps: list[MetricsSnapshot] = []
    for task in tasks:
        ctx = build_context(
            config,
            cfg_exp.mode,
            task_id=task.task_id,
            use_memory=cfg_exp.use_memory,
            use_state_exchange=cfg_exp.use_state,
            use_sandbox=cfg_exp.use_sandbox,
            memory=memory,
        )
        orch = Orchestrator(build_default_agents(config))
        result = asyncio.run(orch.run_task(task, ctx))
        snaps.append(result.metrics)
    return _aggregate(snaps)


def run_suite(
    suite: str = "main",
    repeat: int = 5,
    seed: int = 42,
    task_factory: Callable[[], list[Task]] | None = None,
) -> dict[str, Any]:
    configs = MAIN_SUITE if suite == "main" else ABLATION_SUITE
    factory = task_factory or _default_task_factory

    results: dict[str, Any] = {}
    for cfg_exp in configs:
        runs = [run_once(cfg_exp, factory, seed + i) for i in range(repeat)]
        results[cfg_exp.id] = {
            "label": cfg_exp.label,
            "config": asdict(cfg_exp),
            "summary": summarize_runs(runs, STAT_KEYS),
            "raw": runs,
        }

    _attach_derived(results)
    return {
        "suite": suite,
        "repeat": repeat,
        "seed": seed,
        "env": _env_info(),
        "results": results,
    }


def _attach_derived(results: dict[str, Any]) -> None:
    baseline = results.get("A") or next(iter(results.values()))
    base_tokens = baseline["summary"]["text_tokens"]["mean"] or 1.0
    base_latency = baseline["summary"]["latency_sec"]["mean"] or 1.0
    base_tools = baseline["summary"]["tool_calls"]["mean"] or 1.0
    for r in results.values():
        s = r["summary"]
        used = s["memory_used"]["mean"]
        effective = s["memory_effective"]["mean"]
        r["derived"] = {
            "token_saving_vs_A": round(1 - s["text_tokens"]["mean"] / base_tokens, 4),
            "latency_improvement_vs_A": round(1 - s["latency_sec"]["mean"] / base_latency, 4),
            "repeated_calc_reduction_vs_A": round(1 - s["tool_calls"]["mean"] / base_tools, 4),
            "effective_hit_rate": round(effective / used, 4) if used else 0.0,
            "success_rate": round(s["task_success"]["mean"], 4),
        }


def _env_info() -> dict[str, Any]:
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "capabilities": capability_summary(),
    }


def write_results(payload: dict[str, Any], root: str = "results") -> Path:
    ts = time.strftime("%Y%m%d-%H%M%S")
    out_dir = Path(root) / f"{ts}-{payload['suite']}"
    (out_dir / "raw").mkdir(parents=True, exist_ok=True)

    # 配置快照
    (out_dir / "config.yaml").write_text(
        _to_yaml(
            {
                "suite": payload["suite"],
                "repeat": payload["repeat"],
                "seed": payload["seed"],
                "env": payload["env"],
                "configs": [r["config"] for r in payload["results"].values()],
            }
        ),
        encoding="utf-8",
    )
    # 原始数据
    for cid, r in payload["results"].items():
        for k, run in enumerate(r["raw"]):
            (out_dir / "raw" / f"{cid}_run_{k:02d}.json").write_text(
                json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8"
            )
    # 聚合
    summary = {
        "suite": payload["suite"],
        "repeat": payload["repeat"],
        "seed": payload["seed"],
        "env": payload["env"],
        "results": {
            cid: {
                "label": r["label"],
                "config": r["config"],
                "summary": r["summary"],
                "derived": r["derived"],
            }
            for cid, r in payload["results"].items()
        },
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "report.md").write_text(render_report(summary), encoding="utf-8")
    return out_dir


def render_report(summary: dict[str, Any]) -> str:
    lines = [
        f"# 实验报告 ({summary['suite']})",
        "",
        f"- 重复次数: {summary['repeat']}　随机种子基: {summary['seed']}",
        f"- 环境: Python {summary['env']['python']} / {summary['env']['platform']} / {summary['env']['machine']}",
        "",
        "## 关键指标（均值）",
        "",
        "| 配置 | 成功率 | text_tokens | Token节省 | 时延(s) | 时延改善 | 工具调用 | 重复计算降低 | 有效记忆命中率 | RSS峰值(MB) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for cid, r in summary["results"].items():
        s = r["summary"]
        d = r["derived"]
        lines.append(
            f"| {cid} {r['label']} | {d['success_rate']:.0%} | "
            f"{s['text_tokens']['mean']:.0f} | {d['token_saving_vs_A']:.1%} | "
            f"{s['latency_sec']['mean']:.4f} | {d['latency_improvement_vs_A']:.1%} | "
            f"{s['tool_calls']['mean']:.1f} | {d['repeated_calc_reduction_vs_A']:.1%} | "
            f"{d['effective_hit_rate']:.2f} | {s['rss_peak_mb']['mean']:.1f} |"
        )
    lines += [
        "",
        "## 通信开销（均值 ± 标准差）",
        "",
        "| 配置 | messages | text_tokens | text_chars | state_transfers | state_bytes | artifact_refs |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for cid, r in summary["results"].items():
        s = r["summary"]
        lines.append(
            f"| {cid} | {s['message_count']['mean']:.0f}±{s['message_count']['std']:.0f} | "
            f"{s['text_tokens']['mean']:.0f}±{s['text_tokens']['std']:.0f} | "
            f"{s['text_chars']['mean']:.0f} | {s['state_transfers']['mean']:.1f} | "
            f"{s['state_bytes']['mean']:.0f} | {s['artifact_refs']['mean']:.1f} |"
        )
    lines += [
        "",
        "## 记忆复用",
        "",
        "| 配置 | retrieved | used | effective | harmful | 有效命中率 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for cid, r in summary["results"].items():
        s = r["summary"]
        d = r["derived"]
        lines.append(
            f"| {cid} | {s['memory_retrieved']['mean']:.1f} | {s['memory_used']['mean']:.1f} | "
            f"{s['memory_effective']['mean']:.1f} | {s['memory_harmful']['mean']:.1f} | "
            f"{d['effective_hit_rate']:.2f} |"
        )
    lines.append("")
    return "\n".join(lines)


def _to_yaml(data: Any, indent: int = 0) -> str:
    """极简 YAML 序列化（避免引入额外依赖即可读写配置快照）。"""
    pad = "  " * indent
    if isinstance(data, dict):
        out = []
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                out.append(f"{pad}{k}:")
                out.append(_to_yaml(v, indent + 1))
            else:
                out.append(f"{pad}{k}: {v}")
        return "\n".join(out)
    if isinstance(data, list):
        out = []
        for item in data:
            if isinstance(item, dict):
                out.append(f"{pad}-")
                out.append(_to_yaml(item, indent + 1))
            else:
                out.append(f"{pad}- {item}")
        return "\n".join(out)
    return f"{pad}{data}"


def run_benchmark_cli(args) -> int:
    payload = run_suite(suite=args.suite, repeat=args.repeat, seed=args.seed)
    out_dir = write_results(payload)
    print(
        render_report(
            {
                "suite": payload["suite"],
                "repeat": payload["repeat"],
                "seed": payload["seed"],
                "env": payload["env"],
                "results": {
                    cid: {
                        "label": r["label"],
                        "config": r["config"],
                        "summary": r["summary"],
                        "derived": r["derived"],
                    }
                    for cid, r in payload["results"].items()
                },
            }
        )
    )
    print(f"\n结果已保存到: {out_dir}")
    return 0


__all__ = [
    "run_suite",
    "run_once",
    "write_results",
    "render_report",
    "run_benchmark_cli",
    "ExperimentConfig",
]
