# 概要与详细设计 (DESIGN)

## 一、概要设计

### 1.1 问题
多 Agent 协作以自然语言/JSON 透传中间结果，导致：通信冗长 token 高、内部状态反复
编解码增加时延与语义损耗、中间经验难沉淀复用。本项目从**系统层机制**解决这三点。

### 1.2 总体方案
- **结构化通信协议**：`AgentMessage`（Pydantic 全字段）作为唯一真源，收敛为动作/参数/结果/能力。
- **非文本状态传递**：embedding / compact state vector / plan DAG 在 Agent 间直接交换且被真实消费。
- **共享记忆复用**：统一记忆单元 + 混合检索 + 质量控制 + 命中分级，跨任务复用经验。
- **CodeAct 沙箱**：LLM 生成代码在受限环境执行并验证。
- **双模式 + 评测**：text/structured 公平对比，4 组主实验 + 消融。

### 1.3 模块划分
见 `docs/ARCHITECTURE.md` 第 3 节（13 个模块：runtime/agents/protocol/registry/scheduler/
state_exchange/artifact_store/memory/sandbox/observability/evaluation/providers/api）。

## 二、详细设计

### 2.1 运行时与 Agent 生命周期
- `BaseAgent.run` 统一包装：状态机（CREATED→READY→RUNNING→SUCCEEDED/FAILED/TIMEOUT→TERMINATED）、
  `asyncio.wait_for` 超时、重试（确定性零退避）、失败隔离（异常转 error 消息而非崩溃）。
- `Orchestrator`：握手注册 → 能力发现解析流水线 → 逐阶段投递（计量）→ 幂等去重 → 故障中止与降级。

### 2.2 通信协议与公平计量
- 字段见 `docs/PROTOCOL_SPEC.md`。
- `serialization`：text 渲染（内联全文）vs structured 编码（短键 + 引用），统一 token/char 计量。
- `mapper`：text↔structured 双向；结构化无损往返核心字段；`semantically_equivalent` 公平性断言。

### 2.3 非文本状态与 Artifact
- `StateExchange.put_plan_state`：DAG + embedding + compact vector，内容寻址，`state://` 引用，
  大向量经 `SharedVectorBuffer`（可选共享内存）传输。
- 接收方消费：Retriever 用 plan embedding 对检索目标语义排序、用 DAG 还原 operands。
- `ArtifactStore`：内容寻址、引用计数 GC、作用域、失效检测与降级。详见 `docs/STATE_EXCHANGE.md`。

### 2.4 共享记忆
- `MemoryRecord` 全字段；SQLite 元数据 + 可插拔向量后端；混合检索（语义+关键词+标签）×质量权重。
- 去重（语义近重+内容签名）、版本链接、错误记忆降权、provenance；命中分级 Retrieved/Used/Effective/Harmful。
- 复用：`task_signature` 区分同一子问题（复用结论）与相似子问题（复用策略）。详见 `docs/SHARED_MEMORY.md`。

### 2.5 CodeAct 沙箱
- subprocess + timeout + `setrlimit`（CPU/内存/文件/句柄/进程）+ 工作目录隔离 + 环境白名单 +
  Python `-I` + 独立进程组超时清理 + 输出限制；Podman（`--network=none`）可选；能力探测降级。

### 2.6 评测
- 16 项指标采集（`MetricsCollector`）+ 派生指标；多次重复统计（均值/std/P50/P95）；
  结果带时间戳落盘不覆盖。详见 `docs/EXPERIMENT_PLAN.md` 与 `docs/EXPERIMENT_REPORT.md`。

### 2.7 关键数据流
见 `docs/ARCHITECTURE.md` 第 4 节。

## 三、可靠性与可复现
- mock-first 确定性；固定随机种子；配置与代码分离；结构化日志带 trace_id/task_id；
  全链路降级（引用失效/记忆不可用/LLM 失败/沙箱不可用）。
