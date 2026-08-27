# openEuler 兼容报告 (OPEN_EULER_COMPATIBILITY)

> 目标环境：**openEuler 24.03-LTS-SP3 / x86_64**
> 状态：脚本与代码已按目标环境设计；**最终验证由用户在 openEuler VM 上执行** `scripts/verify_openeuler.sh`，并将输出回填本报告「实测结果」章节。

## 1. 环境要求

| 项 | 要求 | 检查方式 |
| --- | --- | --- |
| OS | openEuler 24.03-LTS-SP3 | `/etc/os-release` |
| 架构 | x86_64 | `uname -m` |
| Python | ≥ 3.10（系统自带通常 3.11） | `python3 --version` |
| 包管理 | dnf | `scripts/bootstrap.sh` |
| cgroup | v2（沙箱资源限制增强） | `stat -fc %T /sys/fs/cgroup` |
| 共享内存 | `/dev/shm` 可写 | `verify_openeuler.sh` |
| Socket/IPC | Unix Domain Socket | `verify_openeuler.sh` |
| 容器（可选） | Podman | `command -v podman` |

## 2. 依赖策略

- **核心依赖**：pydantic、numpy、psutil、PyYAML —— 均为纯 Python/通用 wheel，openEuler 上可用。
- **可选依赖**：hnswlib/faiss-cpu/sentence-transformers/msgpack/openai/fastapi —— 缺失时自动降级（默认 numpy + JSON + mock）。
- 安装使用 `dnf`（非 apt），Python 走隔离 venv，避免污染系统环境。

## 3. 系统能力使用与降级矩阵

| 能力 | 用途 | openEuler 行为 | 不可用时降级 |
| --- | --- | --- | --- |
| Unix Domain Socket | 结构化消息 IPC 通道 | 启用 | 进程内异步队列 |
| `multiprocessing.shared_memory` | 大向量零拷贝传输 | 启用 | 序列化传输 |
| `resource.setrlimit` | CPU/内存/进程数限制 | 启用 | 仅 timeout |
| cgroup v2 | 沙箱资源限制增强 | 启用（若挂载） | rlimit |
| Linux namespace | 沙箱隔离增强 | 启用（若有权限） | 工作目录隔离 |
| Podman/bubblewrap/seccomp | 容器/系统调用过滤 | 可选启用 | subprocess |

## 4. 一键流程

```bash
bash scripts/bootstrap.sh          # dnf 安装系统依赖（需 root/sudo）
bash scripts/install.sh            # venv + pip install -e .
bash scripts/verify_openeuler.sh   # 能力检查 + 测试 + 10 轮稳定性摘要
bash scripts/run_tests.sh
bash scripts/run_demo.sh
bash scripts/run_benchmark.sh
```

## 5. 实测结果（待回填）

> 在 openEuler 24.03-LTS-SP3 上运行 `verify_openeuler.sh` 后，将输出粘贴于此。

```
（待用户在 openEuler VM 上执行后回填）
- OS / 版本：
- 内核：
- 架构：
- Python：
- 依赖：
- cgroup v2：
- 共享内存：
- Socket/IPC：
- 沙箱：
- 测试摘要：
- 10 轮稳定性摘要：
```

## 6. 已知差异与注意

- 开发在 Windows 进行：UDS / rlimit / cgroup / namespace 在 Windows 下不可用，代码自动降级；这些能力的真实验证以 openEuler 为准。
- 首次运行可选重后端（faiss/sentence-transformers）需联网下载，离线环境请使用默认 mock/numpy 后端。
