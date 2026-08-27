# 部署文档 (DEPLOYMENT)

> 目标环境：openEuler 24.03-LTS-SP3 (x86_64)。默认 **mock-first**，无需 API Key。

## 1. 一键流程

```bash
# 1) 安装系统依赖（dnf，需 root/sudo）
bash scripts/bootstrap.sh

# 2) 创建隔离 Python 环境并安装项目
bash scripts/install.sh

# 3) 验证环境与能力（输出兼容性报告片段）
bash scripts/verify_openeuler.sh

# 4) 运行测试 / Demo / 基准实验
bash scripts/run_tests.sh
bash scripts/run_demo.sh
bash scripts/run_benchmark.sh 5 42
```

## 2. 脚本说明

| 脚本 | 作用 | 需 root | 幂等 |
| --- | --- | --- | --- |
| `bootstrap.sh` | dnf 安装 python3/pip/virtualenv/gcc/git，可选 podman | 是 | 是 |
| `install.sh` | 创建 venv（或 uv），`pip install -e .[dev]`，生成 `.env` | 否 | 是 |
| `run_tests.sh` | ruff + mypy + pytest + coverage | 否 | 是 |
| `run_demo.sh` | 运行 A/B/C 三配置通信对比 | 否 | 是 |
| `run_benchmark.sh [repeat] [seed]` | 主实验 + 消融，结果落 `results/` | 否 | 是 |
| `verify_openeuler.sh` | 环境/能力/测试/稳定性摘要 | 否 | 是 |

## 3. 配置

- 复制 `.env.example` 为 `.env`（`install.sh` 会自动完成）。
- 默认 `AGENT_LLM_PROVIDER=mock`、`AGENT_EMBEDDING_PROVIDER=mock`、`AGENT_VECTOR_BACKEND=numpy`，
  无需任何外部服务即可运行全部测试与实验。
- 如需真实 LLM：设置 `AGENT_LLM_PROVIDER=openai` 与 `AGENT_LLM_API_KEY`（**切勿提交 .env**）。
- 可选系统增强：`AGENT_STATE_SHM=true` 启用共享内存状态传输；`AGENT_SANDBOX_BACKEND=podman` 启用容器沙箱。

## 4. 可选依赖

| 能力 | 安装 | 缺失时 |
| --- | --- | --- |
| 真实向量检索 | `pip install -e ".[vector]"`（hnswlib）或 `.[faiss]` | 回退 numpy |
| 真实 embedding | `pip install -e ".[embedding]"` | 回退 mock |
| 真实 LLM | `pip install -e ".[llm]"` | 回退 mock |
| MessagePack 对照 | `pip install -e ".[serialize]"` | 仅 JSON |
| 容器沙箱 | `dnf install podman` | 回退 subprocess |

## 5. 安全与运维

- 不提交任何密钥；`.env`、`*.key` 已在 `.gitignore`。
- 沙箱默认禁用网络、限制 CPU/内存/进程/输出，超时强制清理进程组。
- 运行期数据写入 `.agent_data/`（可清理）；实验结果写入 `results/`（**保留为证据，勿删**）。

## 6. 故障排查

- `dnf` 不可用：本项目面向 openEuler/RHEL 系，不使用 apt。
- 重后端安装失败（faiss/sentence-transformers）：忽略即可，系统自动降级 mock/numpy。
- cgroup v2 / 共享内存不可用：沙箱与状态传输自动降级，功能不受影响（仅隔离强度/零拷贝优化减弱）。
