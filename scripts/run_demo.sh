#!/usr/bin/env bash
# 运行 Demo：对比 A 文本基线 / B 结构化 / C 结构化+非文本状态。
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

VENV_DIR="${VENV_DIR:-.venv}"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m agent_runtime.cli demo
