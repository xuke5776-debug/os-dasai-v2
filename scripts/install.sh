#!/usr/bin/env bash
# 在隔离的 Python 虚拟环境中安装本项目（幂等）。不需要 root。
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

VENV_DIR="${VENV_DIR:-.venv}"

echo "[install] 项目根目录: $ROOT_DIR"

# 优先使用 uv（若可用），否则回退 venv + pip。
if command -v uv >/dev/null 2>&1; then
    echo "[install] 使用 uv 创建环境"
    uv venv "$VENV_DIR" 2>/dev/null || true
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
    uv pip install -e ".[dev]"
else
    echo "[install] 使用 venv + pip 创建环境"
    if [ ! -d "$VENV_DIR" ]; then
        python3 -m venv "$VENV_DIR"
    fi
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
    python -m pip install --upgrade pip
    python -m pip install -e ".[dev]"
fi

# 准备 .env（不覆盖已有；不包含真实密钥）。
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    cp .env.example .env
    echo "[install] 已从 .env.example 生成 .env（默认 mock-first，无需 API Key）"
fi

echo "[install] 完成。验证环境：bash scripts/verify_openeuler.sh"
