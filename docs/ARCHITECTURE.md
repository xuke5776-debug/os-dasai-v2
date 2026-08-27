# 总体架构 (ARCHITECTURE)

## 1. 设计目标

实现多智能体协作的 **系统层机制**，三大支柱：

1. 低开销结构化通信（替代自然语言透传）；
2. 非文本中间状态直接交换（被接收方真实消费）；
3. 共享记忆的跨任务复用。

所有机制必须可在 text/structured 双模式下公平对比，并在 openEuler 24.03-LTS-SP3 上运行。

## 2. 架构总览

```
                       ┌──────────────────────────────────────────┐
                       │            Evaluation / Benchmark          │
                       │   (16 指标采集 + 4 组主实验 + 消融 + 统计) │
                       └───────────────┬──────────────────────────┘
                                       │ 驱动
┌───────────────────────────────────── Multi-Agent Runtime (asyncio) ──────────────────────────────┐
│                                                                                                     │
│   ┌─────────────┐    ┌───────────────┐    ┌──────────────────────────────────────────────────┐   │
│   │  Registry   │◄──►│   Scheduler    │◄──►│  Agents                                          │   │
│   │ 注册/握手/  │    │ 路由/DAG调度/  │    │  Planner / Retriever / CodeActExecutor /          │   │
│   │ 能力发现    │    │ 消息总线(UDS)  │    │  ReviewerSummarizer                               │   │
│   └─────────────┘    └───────┬───────┘    └───────┬──────────────────────────────────────────┘   │
│                              │                     │                                                │
│                    ┌─────────▼─────────┐   ┌───────▼────────┐   ┌──────────────┐  ┌────────────┐  │
│                    │ Protocol          │   │ State Exchange │   │ Artifact     │  │ Sandbox    │  │
│                    │ Pydantic 契约/    │   │ embedding/     │   │ Store        │  │ CodeAct    │  │
│                    │ schema/版本/      │   │ state vector/  │   │ 内容寻址/    │  │ subprocess │  │
│                    │ text<->struct映射 │   │ plan DAG       │   │ URI/GC       │  │ +rlimit    │  │
│                    └───────────────────┘   └───────┬────────┘   └──────┬───────┘  └─────┬──────┘  │
│                                                     │                   │                │         │
│   ┌────────────────────────────────────────────────▼───────────────────▼────────────────▼─────┐  │
│   │                          Shared Memory (SQLite 元数据 + 可插拔向量后端)                      │  │
│   │     Working / Episodic / Semantic / Procedural  ·  检索/去重/版本/质量/provenance/命中度量   │  │
│   └──────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                                     │
│   ┌────────────────────────┐                                     ┌───────────────────────────┐    │
│   │ Providers              │                                     │ Observability             │    │
│   │ mock LLM/embedding +   │                                     │ 结构化日志/metrics/       │    │
│   │ OpenAI兼容 + tokenizer │                                     │ psutil(CPU/RSS)/trace聚合 │    │
│   └────────────────────────┘                                     └───────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## 3. 模块职责

| 模块 | 目录 | 职责 |
| --- | --- | --- |
| Runtime | `runtime/` | 事件循环、Agent 生命周期与状态机、超时/重试/失败隔离/恢复 |
| Agents | `agents/` | Planner（规划/DAG）、Retriever（记忆/证据检索）、CodeActExecutor（生成并执行代码）、ReviewerSummarizer（审查/总结/沉淀记忆） |
| Protocol | `protocol/` | Pydantic 全字段消息契约、schema 校验、协议版本、text↔structured 映射、幂等 |
| Registry | `registry/` | Agent 注册、握手、能力发现 |
| Scheduler | `scheduler/` | 消息路由、依赖（DAG）调度、消息总线（进程内队列 / UDS） |
| State Exchange | `state_exchange/` | 生成/编解码 embedding、compact state vector、plan DAG；shared_memory 传输大向量 |
| Artifact Store | `artifact_store/` | 内容寻址存储、URI、引用计数/GC、作用域、失效处理、降级文本 |
| Memory | `memory/` | 统一记忆单元、SQLite 元数据、向量索引、检索/去重/版本/质量控制/provenance、命中指标 |
| Sandbox | `sandbox/` | CodeAct 执行：subprocess+timeout+rlimit、目录/环境/文件/网络隔离；cgroup v2/namespace/Podman 可降级 |
| Observability | `observability/` | 结构化日志（trace_id/task_id）、metrics 收集、psutil CPU/RSS 采样、trace 聚合 |
| Evaluation | `evaluation/` | benchmark runner、16 指标统计、派生指标、统计分析（均值/std/P50/P95） |
| Providers | `providers/` | LLM/embedding 抽象 + 确定性 mock + OpenAI 兼容适配器 + token 计数 |
| API | `api/` | FastAPI 控制/查询接口（可选，供 Dashboard） |

## 4. 数据流：一个任务的生命周期

1. **任务输入** → Scheduler 创建 `task_id` / `trace_id`，分配给 Planner。
2. **Planner** 产出 plan DAG（结构化）→ 作为 state 写入 State Exchange，引用通过协议消息传递。
3. **Retriever** 用 plan 关键词/embedding 检索共享记忆与 artifact，返回引用 + 摘要（非全文）。
4. **CodeActExecutor** 在沙箱执行代码，产物写 Artifact Store，仅回传 `artifact://` 引用与 stdout 摘要。
5. **ReviewerSummarizer** 审查结果、判定成功/失败、把经验沉淀为共享记忆（含 provenance、quality_score）。
6. **Observability** 全程采集 metrics；**Evaluation** 汇总 16 项指标。

## 5. 双模式公平性设计

- 协议模型（Pydantic）为唯一真源。
- `structured_mode`：Agent 间传 `AgentMessage`（结构化字段 + 引用）。
- `text_mode`：同一 `AgentMessage` 经 `mapper` 序列化为自然语言文本透传，接收方再解析；**逻辑、Agent、工具、温度、重试、种子完全一致**，仅通信载体不同。
- 这保证「通信效率」对比是同一任务、同一智能体能力下的纯通信开销差异。

## 6. 候选架构对比与选择

| 方案 | 通信载体 | 优点 | 缺点 | openEuler 兼容 | 评分贡献 | 工作量 | 结论 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 方案1 单进程 asyncio + 内存对象传引用 | Python 对象 | 最简单、最稳 | "系统层"说服力弱，难体现 IPC | 好 | 中 | 低 | 备选 |
| **方案2 多进程 + UDS + shared_memory + SQLite/向量** | UDS 消息 + 共享内存 | 真实 IPC/共享内存，契合系统层创新，可降级 | 复杂度中等 | 好 | 高 | 中 | **推荐** |
| 方案3 方案2 + eBPF/Podman/seccomp 重度增强 | 同上 + 内核态观测 | 上限最高 | 风险大、调试难、依赖内核 | 中（依赖配置） | 高 | 高 | 可选增强 |

**最终选择**：以方案2为主线；进程内队列与 UDS 双实现（默认进程内保证可移植与可测，UDS 作为系统层证据），shared_memory 用于大向量零拷贝传输；方案3 能力（cgroup v2/namespace/Podman）作为沙箱的**可降级增强**，eBPF 仅后期可选。理由：在「系统完整性」与「状态传递创新」上得分高，同时保持可复现与跨平台可测。

## 7. 关键非功能设计

- **可复现**：所有随机性受 `AGENT_RANDOM_SEED` 控制；mock provider 确定性输出。
- **可观测**：每条消息带 trace_id/task_id；metrics 与日志分离，结果落 `results/<ts>/`。
- **鲁棒**：引用失效降级文本；记忆库不可用时跳过检索；LLM 失败重试 + 降级。
- **解耦**：场景与基础设施解耦；评测与运行时解耦；provider 可替换。
