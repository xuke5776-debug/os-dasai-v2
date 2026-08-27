#!/usr/bin/env bash
# openEuler 目标环境验证：输出环境信息、系统能力、测试与稳定性摘要。
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

VENV_DIR="${VENV_DIR:-.venv}"
if [ -f "$VENV_DIR/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
fi

echo "============================================================"
echo " openEuler 兼容性验证报告"
echo "============================================================"

echo "## OS / 版本"
if [ -f /etc/os-release ]; then
    grep -E '^(NAME|VERSION)=' /etc/os-release || true
else
    uname -s
fi

echo
echo "## 内核 / 架构"
uname -r
uname -m

echo
echo "## Python"
python --version 2>&1 || python3 --version 2>&1

echo
echo "## 依赖（核心）"
python - <<'PY' 2>&1 || true
mods = ["pydantic", "numpy", "psutil", "yaml"]
for m in mods:
    try:
        mod = __import__(m)
        print(f"  {m}: {getattr(mod, '__version__', 'ok')}")
    except Exception as e:
        print(f"  {m}: 缺失 ({e})")
PY

echo
echo "## 系统能力（沙箱 / IPC / 共享内存）"
python - <<'PY' 2>&1 || true
from agent_runtime.sandbox.capabilities import summary
for k, v in summary().items():
    print(f"  {k}: {v}")
PY

echo
echo "## cgroup v2"
if [ -f /sys/fs/cgroup/cgroup.controllers ]; then
    echo "  可用: $(cat /sys/fs/cgroup/cgroup.controllers)"
else
    echo "  不可用（沙箱将降级到 rlimit/subprocess）"
fi

echo
echo "## 共享内存 /dev/shm"
if [ -d /dev/shm ] && [ -w /dev/shm ]; then
    echo "  可用可写"
else
    echo "  不可用（状态交换将降级到进程内传输）"
fi

echo
echo "## 单元 + 集成测试摘要"
pytest -q -m "not stability" 2>&1 | tail -3 || echo "  pytest 执行失败"

echo
echo "## 10 轮连续稳定性摘要"
pytest -q -m stability 2>&1 | tail -3 || echo "  稳定性测试执行失败"

echo
echo "## Demo（A/B/C 通信对比）"
python -m agent_runtime.cli demo 2>/dev/null | tail -12 || echo "  demo 执行失败"

echo "============================================================"
echo " 验证完成。请将以上输出回填 docs/OPEN_EULER_COMPATIBILITY.md"
echo "============================================================"
