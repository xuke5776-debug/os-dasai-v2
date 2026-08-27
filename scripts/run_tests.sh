#!/usr/bin/env bash
# 运行测试与静态检查（幂等）。
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

VENV_DIR="${VENV_DIR:-.venv}"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "[tests] ruff check"
ruff check src tests scenarios || true

echo "[tests] ruff format --check"
ruff format --check src tests scenarios || true

echo "[tests] mypy"
mypy src || true

echo "[tests] pytest"
pytest -q

echo "[tests] coverage（单元 + 集成）"
coverage run -m pytest -q >/dev/null 2>&1 || true
coverage report || true

echo "[tests] 完成。"
