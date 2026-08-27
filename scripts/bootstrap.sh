#!/usr/bin/env bash
# 安装系统级依赖（openEuler 24.03-LTS-SP3，使用 dnf）。
# 幂等：可重复执行；需要 root 或 sudo 权限的步骤已标注。
set -euo pipefail

echo "[bootstrap] openEuler 系统依赖安装"

if ! command -v dnf >/dev/null 2>&1; then
    echo "[bootstrap] 错误：未找到 dnf。本脚本面向 openEuler / RHEL 系，不使用 apt。" >&2
    exit 1
fi

# 需要 root：使用 sudo（若非 root）。
SUDO=""
if [ "$(id -u)" -ne 0 ]; then
    SUDO="sudo"
fi

# 基础依赖：Python、pip、virtualenv、编译工具、git。
PKGS=(python3 python3-pip python3-virtualenv gcc git)

echo "[bootstrap] dnf 安装: ${PKGS[*]}（需要 root）"
$SUDO dnf install -y "${PKGS[@]}" || {
    echo "[bootstrap] 警告：部分基础包安装失败，请检查软件源。" >&2
}

# 可选增强：podman（CodeAct 容器沙箱）。不可用不影响主流程（自动降级）。
if ! command -v podman >/dev/null 2>&1; then
    echo "[bootstrap] 尝试安装可选增强 podman（失败可忽略，将降级到 subprocess 沙箱）"
    $SUDO dnf install -y podman || echo "[bootstrap] podman 不可用，已跳过。"
fi

echo "[bootstrap] 完成。下一步：bash scripts/install.sh"
