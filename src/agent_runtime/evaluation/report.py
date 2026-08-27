"""从结果目录生成 / 打印报告。"""

from __future__ import annotations

import json
from pathlib import Path

from agent_runtime.evaluation.runner import render_report


def generate_report_cli(args) -> int:
    results_dir = Path(args.results)
    summary_path = results_dir / "summary.json"
    if not summary_path.is_file():
        print(f"未找到 summary.json: {summary_path}")
        return 1
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    report = render_report(summary)
    (results_dir / "report.md").write_text(report, encoding="utf-8")
    print(report)
    return 0


__all__ = ["generate_report_cli"]
