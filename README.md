# Agent Runtime — 面向多智能体协作的低开销通信、状态传递与共享记忆机制

> OS 大赛 赛题 10（应用创新）参赛项目
> 目标环境：**openEuler 24.03-LTS-SP3 (x86_64)**

本项目研究并实现多智能体协作中的 **系统层机制**，而非普通的工作流编排（LangGraph / AutoGen / CrewAI）。核心解决三个问题：

1. **低开销通信**：用结构化协议替代冗长自然语言交互，把 Agent 间内容收敛为「动作 / 参数 / 结果 / 能力」等高密度语义单元。
2. **非文本状态传递**：让 embedding / 紧凑状态向量 / 计划 DAG 等中间表示在 Agent 间直接交换，并被接收方真实消费。
3. **共享记忆复用**：把任务过程中的摘要、证据、策略、经验沉淀为可标识、可检索、可复用的记忆单元，实现跨任务知识积累。

## 核心特性

- **≥3 个 Agent**：Planner / Retriever / CodeAct-Executor / Reviewer-Summarizer，覆盖规划、检索、执行、总结四类角色。
- **双协作模式**：`text_mode`（纯文本基线）与 `structured_mode`（结构化协议），在相同条件下公平对比。
- **结构化通信协议**：Pydantic 全字段契约 + schema 校验 + 握手 / 注册 / 能力发现 / 协议映射 / 幂等 / 全链路 trace。
- **Artifact Reference**：内容寻址，长内容只存一次，消息仅传引用与摘要，引用失效自动降级文本。
- **共享记忆**：SQLite 元数据 + 可插拔向量后端，区分 Working / Episodic / Semantic / Procedural，区分 Retrieved / Used / Effective / Harmful Hit。
- **CodeAct 沙箱**：LLM 生成 Python 代码在受限环境执行，返回 stdout / stderr / exit code / 资源占用 / artifact 引用。
- **可复现实验**：mock-first，无需 API Key 即可运行全部测试与实验；4 组主实验 + 消融，固定随机种子，结果带时间戳不覆盖。

## 快速开始

> 默认 **mock-first**：无需任何 API Key 或外部模型即可运行。

```bash
# 1. 创建隔离环境并安装
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# 2. 运行测试
pytest -q

# 3. 运行 Demo（双模式对比一个任务）
python -m agent_runtime.cli demo

# 4. 运行基准实验（4 组主实验，结果落 results/<timestamp>/）
python -m agent_runtime.cli benchmark --repeat 5
```

### 在 openEuler 24.03-LTS-SP3 上部署

```bash
bash scripts/bootstrap.sh        # 安装系统依赖（dnf）
bash scripts/install.sh          # 创建隔离 Python 环境并安装项目
bash scripts/verify_openeuler.sh # 输出环境与能力检查 + 测试/稳定性摘要
bash scripts/run_tests.sh
bash scripts/run_benchmark.sh
```

## 文档索引

| 文档 | 说明 |
| --- | --- |
| `docs/DELIVERABLES.md` | **交付物清单（17 项映射）** |
| `docs/DESIGN.md` | 概要与详细设计 |
| `docs/ARCHITECTURE.md` | 总体架构与模块设计 |
| `docs/REQUIREMENTS_TRACEABILITY.md` | 需求追踪矩阵（赛题逐条映射） |
| `docs/ROADMAP.md` | 分阶段路线图 P0–P9 |
| `docs/EXPERIMENT_PLAN.md` | 实验设计与指标定义 |
| `docs/EXPERIMENT_REPORT.md` | 性能实验报告（真实数据） |
| `docs/TEST_REPORT.md` | 测试报告 |
| `docs/PROTOCOL_SPEC.md` | 结构化通信协议规范 |
| `docs/STATE_EXCHANGE.md` | 非文本状态传递机制说明 |
| `docs/SHARED_MEMORY.md` | 共享记忆机制说明 |
| `docs/DEPLOYMENT.md` | 部署文档 |
| `docs/OPEN_EULER_COMPATIBILITY.md` | openEuler 兼容报告 |
| `docs/VIDEO_SCRIPT.md` | 演示视频脚本 |
| `docs/PPT_OUTLINE.md` | 答辩 PPT 大纲（PPT 见 `deliverables/答辩PPT.pptx`） |
| `docs/JUDGE_QA.md` | 评委问题与回答 |
| `docs/LIMITATIONS.md` | 已知限制与未来工作 |
| `docs/RISK_REGISTER.md` | 风险登记册 |
| `docs/DECISIONS.md` | 重大设计决策记录 |

## 评分点对应

| 评分项 | 分值 | 主要支撑 |
| --- | --- | --- |
| 通信效率 | 25 | 结构化协议 + Artifact Reference + 非文本状态，Token 节省率 |
| 状态传递创新 | 20 | embedding / compact state vector / plan DAG，shared_memory 直传，被接收方真实消费 |
| 记忆复用效果 | 20 | 跨任务共享记忆，Effective / Harmful Hit 度量 |
| 系统完整性 | 20 | 多 Agent 运行时、≥10 轮稳定、故障恢复 |
| 实验验证 | 15 | 4 组主实验 + 消融，均值 / std / P50 / P95，原始数据 |

## 许可

MIT License。
