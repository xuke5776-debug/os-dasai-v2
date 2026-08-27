#!/usr/bin/env bash
# 运行基准实验（主实验 + 消融），结果落 results/<timestamp>-*/（不覆盖）。
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

VENV_DIR="${VENV_DIR:-.venv}"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

REPEAT="${1:-5}"
SEED="${2:-42}"

echo "[benchmark] 主实验 repeat=$REPEAT seed=$SEED"
python -m agent_runtime.cli benchmark --suite main --repeat "$REPEAT" --seed "$SEED"

echo "[benchmark] 消融实验 repeat=$REPEAT seed=$SEED"
python -m agent_runtime.cli benchmark --suite ablation --repeat "$REPEAT" --seed "$SEED"

echo "[benchmark] 完成。结果见 results/ 目录。"
