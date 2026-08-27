"""命令行入口。

子命令：
- `version`：打印版本与协议版本。
- `demo`：在 text / structured 两种模式下运行 Demo 任务并对比通信开销。
- `benchmark`：运行基准实验（P7 实现）。
- `report`：从结果目录生成报告（P7 实现）。
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from agent_runtime import PROTOCOL_VERSION, __version__
from agent_runtime.config import load_config
from agent_runtime.observability.logging import setup_logging


def _cmd_version(_: argparse.Namespace) -> int:
    print(f"agent-runtime {__version__} (protocol {PROTOCOL_VERSION})")
    return 0


def _cmd_demo(args: argparse.Namespace) -> int:
    from agent_runtime.runtime.builder import run_task

    # 延迟导入场景（位于项目根目录的 scenarios 包）。
    try:
        from scenarios.demo import make_demo_task
    except ModuleNotFoundError:
        sys.path.insert(0, ".")
        from scenarios.demo import make_demo_task

    config = load_config()
    # 三种配置：A 文本基线 / B 结构化协议 / C 结构化 + 非文本状态 + 引用。
    configs: list[tuple[str, str, bool]] = [
        ("A:text", "text", False),
        ("B:struct", "structured", False),
        ("C:struct+state", "structured", True),
    ]
    results = {}
    for label, mode, use_state in configs:
        result = asyncio.run(
            run_task(
                make_demo_task(),
                config=config,
                mode=mode,
                use_state_exchange=use_state,
            )
        )
        results[label] = result

    _print_comparison(results)
    return 0


def _print_comparison(results: dict) -> None:
    labels = list(results.keys())
    print("\n=== Demo: A 文本基线 / B 结构化 / C 结构化+非文本状态 ===")
    header = f"{'metric':<18}" + "".join(f"{lbl:>16}" for lbl in labels)
    print(header)

    def row(name: str, fn) -> None:
        print(f"{name:<18}" + "".join(f"{str(fn(results[lbl])):>16}" for lbl in labels))

    row("success", lambda r: r.success)
    row("quality", lambda r: r.metrics.task_quality)
    row("messages", lambda r: r.metrics.message_count)
    row("text_tokens", lambda r: r.metrics.text_tokens)
    row("text_chars", lambda r: r.metrics.text_chars)
    row("state_transfers", lambda r: r.metrics.state_transfers)
    row("state_bytes", lambda r: r.metrics.state_bytes)
    row("artifact_refs", lambda r: r.metrics.artifact_refs)
    row("llm_calls", lambda r: r.metrics.llm_calls)

    base = results[labels[0]].metrics.text_tokens
    print("\nToken 节省率 (相对 A 文本基线):")
    for lbl in labels[1:]:
        toks = results[lbl].metrics.text_tokens
        saving = 1 - toks / base if base else 0.0
        ok = results[lbl].success
        print(f"  {lbl:<16}: {saving:6.1%}   (success={ok})")


def _cmd_benchmark(args: argparse.Namespace) -> int:
    from agent_runtime.evaluation.runner import run_benchmark_cli

    return run_benchmark_cli(args)


def _cmd_report(args: argparse.Namespace) -> int:
    from agent_runtime.evaluation.report import generate_report_cli

    return generate_report_cli(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-runtime", description="多智能体协作运行时")
    parser.add_argument("--log-level", default="WARNING")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("version").set_defaults(func=_cmd_version)

    p_demo = sub.add_parser("demo", help="运行 Demo 任务并对比双模式")
    p_demo.set_defaults(func=_cmd_demo)

    p_bench = sub.add_parser("benchmark", help="运行基准实验")
    p_bench.add_argument("--suite", default="main", choices=["main", "ablation"])
    p_bench.add_argument("--repeat", type=int, default=5)
    p_bench.add_argument("--seed", type=int, default=42)
    p_bench.add_argument("--rounds", type=int, default=10)
    p_bench.set_defaults(func=_cmd_benchmark)

    p_report = sub.add_parser("report", help="从结果目录生成报告")
    p_report.add_argument("--results", required=True)
    p_report.set_defaults(func=_cmd_report)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    setup_logging(level=getattr(args, "log_level", "WARNING"), fmt="text")
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
