"""从最新实验结果生成一个零依赖的静态 HTML Dashboard。

用法：
    python dashboard/generate_dashboard.py [results_dir]
不带参数时自动选取 results/ 下最新的 *-main 目录。输出 dashboard/index.html。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _latest_main_results() -> Path | None:
    results = sorted((ROOT / "results").glob("*-main"))
    return results[-1] if results else None


def _bar(value: float, max_value: float, color: str) -> str:
    width = int((value / max_value) * 260) if max_value else 0
    return (
        f'<div style="background:{color};height:16px;width:{width}px;'
        f'display:inline-block;border-radius:3px"></div> '
        f"<span>{value:.0f}</span>"
    )


def render_html(summary: dict) -> str:
    results = summary["results"]
    max_tokens = max(r["summary"]["text_tokens"]["mean"] for r in results.values()) or 1
    rows = []
    for cid, r in results.items():
        s = r["summary"]
        d = r["derived"]
        rows.append(
            f"<tr><td><b>{cid}</b> {r['label']}</td>"
            f"<td>{d['success_rate']:.0%}</td>"
            f"<td>{_bar(s['text_tokens']['mean'], max_tokens, '#4f8cff')}</td>"
            f"<td>{d['token_saving_vs_A']:.1%}</td>"
            f"<td>{s['state_transfers']['mean']:.0f}</td>"
            f"<td>{s['artifact_refs']['mean']:.0f}</td>"
            f"<td>{d['effective_hit_rate']:.2f}</td>"
            f"<td>{d['repeated_calc_reduction_vs_A']:.1%}</td></tr>"
        )
    env = summary.get("env", {})
    return f"""<!doctype html>
<html lang="zh"><head><meta charset="utf-8">
<title>Agent Runtime Dashboard</title>
<style>
 body{{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;margin:2rem;color:#222}}
 h1{{font-size:1.4rem}} table{{border-collapse:collapse;width:100%;margin-top:1rem}}
 th,td{{border:1px solid #e2e2e2;padding:8px 10px;text-align:left;font-size:14px}}
 th{{background:#f6f8fa}} .meta{{color:#666;font-size:13px}}
 caption{{text-align:left;font-weight:600;margin-bottom:.4rem}}
</style></head><body>
<h1>多智能体协作机制 · 实验 Dashboard</h1>
<p class="meta">套件: {summary.get('suite')} ｜ 重复: {summary.get('repeat')} ｜ 种子: {summary.get('seed')}
 ｜ 环境: Python {env.get('python','?')} / {env.get('platform','?')}</p>
<table>
<caption>关键指标（均值）</caption>
<tr><th>配置</th><th>成功率</th><th>text_tokens</th><th>Token 节省</th>
<th>状态传递</th><th>Artifact 引用</th><th>有效记忆命中率</th><th>重复计算降低</th></tr>
{''.join(rows)}
</table>
<p class="meta">数据来源：results/ 原始实验文件（非虚构）。</p>
</body></html>
"""


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        results_dir = Path(argv[1])
    else:
        latest = _latest_main_results()
        if latest is None:
            print("未找到 results/*-main 目录，请先运行 benchmark。")
            return 1
        results_dir = latest
    summary = json.loads((results_dir / "summary.json").read_text(encoding="utf-8"))
    html = render_html(summary)
    out = Path(__file__).resolve().parent / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"Dashboard 已生成: {out}（数据来自 {results_dir}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
