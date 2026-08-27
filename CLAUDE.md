# CLAUDE.md — 项目状态与会话恢复备忘

> 本文件用于在多次会话间恢复上下文。每完成一个阶段必须更新。

## 项目一句话

为 openEuler 24.03-LTS-SP3 实现「面向多智能体协作的低开销通信、状态传递与共享记忆机制」原型，强调**系统层机制**，支持 text/structured 双模式公平对比、≥3 Agent、≥10 轮稳定、2 组关联连续任务、4 组主实验 + 消融。

## 关键约束（务必牢记）

- **mock-first**：默认无需任何 API Key / 外部模型即可跑全部测试与实验（确定性 mock LLM + mock embedding）。
- **公平实验**：固定模型/温度/max_tokens/工具/重试/随机种子；每配置重复 5 次；同时报告成功率；结果带时间戳落 `results/<timestamp>/` 且**禁止覆盖**。
- **引用而非搬运**：Artifact/State/Memory 用内容寻址 + URI 引用，消息只带引用与摘要。
- **非文本状态必须被消费**：embedding/state vector/plan DAG 须参与检索/路由/上下文构建，不能传而不用。
- **禁止虚构**：所有实验结论来自真实运行日志与结果文件。
- 核心 Runtime/协议/状态/记忆**自研**；LangGraph/AutoGen/CrewAI 仅作适配器或对照。
- 开发在 Windows 进行，目标 openEuler；代码保持跨平台，系统增强（cgroup/namespace/Podman）不可用时**可降级**。

## 已确认决策（默认值）

1. LLM：mock-first + 可选 OpenAI 兼容适配器。
2. Embedding/向量：hash-mock embedding + numpy 检索，可插拔 sentence-transformers/hnswlib/FAISS。
3. 沙箱：subprocess+timeout+rlimit；openEuler 上 cgroup v2+namespace，Podman/bubblewrap 可选可降级。
4. openEuler 验证：用户自行在 openEuler VM 上运行 `verify_openeuler.sh`。
5. 实验：每配置 ×5，4 组主实验 + 关键消融。

## Python 版本策略

- 代码 `requires-python >= 3.10`，工具 target 3.10。
- openEuler 24.03-LTS-SP3 自带 Python（通常 3.11），以目标环境实际为准。
- 避免使用 3.11+ 专属语法；类型注解使用 `from __future__ import annotations` 保证兼容。

## 阶段进度

| 阶段 | 内容 | 状态 |
| --- | --- | --- |
| P0 | 项目骨架 + 规划文档 + 需求追踪矩阵 | 已完成 |
| P1 | 多 Agent 运行时 + 四类 Agent + Provider + text_mode | 已完成 |
| P2 | 结构化协议 + 注册/握手/能力发现 + 协议映射 + structured_mode | 已完成 |
| P3 | 非文本状态交换 + Artifact Store | 已完成 |
| P4 | 共享记忆 | 已完成 |
| P5 | CodeAct 沙箱 | 已完成 |
| P6 | 连续任务 A/B + 10 轮稳定性 | 已完成 |
| P7 | 实验框架 + 4 组主实验 + 消融 | 已完成 |
| P8 | openEuler 适配脚本 + 兼容报告 | 已完成 |
| P9 | Dashboard/Demo + 交付文档 + 答辩 PPT | 已完成 |

> 全部阶段 P0–P9 已完成。69 测试通过、覆盖率 78%、ruff/mypy 干净。
> 待办：用户在 openEuler 24.03-LTS-SP3 VM 上运行 `scripts/verify_openeuler.sh` 回填兼容报告实测；录制演示视频。

## 常用命令

```bash
pip install -e ".[dev]"
pytest -q
ruff check src tests
ruff format --check src tests
mypy src
python -m agent_runtime.cli demo
python -m agent_runtime.cli benchmark --repeat 5
```

## 目录速览

源码在 `src/agent_runtime/`，按模块拆分：runtime / agents / protocol / registry / scheduler / state_exchange / artifact_store / memory / sandbox / observability / evaluation / providers / api。场景在 `scenarios/`，实验编排在 `benchmarks/`，文档在 `docs/`，实验结果在 `results/`。
