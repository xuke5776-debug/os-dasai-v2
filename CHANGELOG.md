# CHANGELOG

遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/) 风格。

## [Unreleased]

### P0 — 需求分析与架构冻结
- 新增项目骨架、`pyproject.toml`、`.env.example`、`.gitignore`。
- 新增规划文档：`CLAUDE.md`、`README.md`。
- 新增 `docs/`：需求追踪矩阵、架构、路线图、实验计划、风险登记册、决策记录、openEuler 兼容报告。
- 新增基础设施：`config.py`（配置加载）、`observability/logging.py`（结构化日志）。

### P1 — 最小多 Agent Runtime 与纯文本基线
- Provider 抽象 + 确定性 mock LLM/embedding + tokenizer（BPE 近似）+ OpenAI 兼容适配器 + 工厂。
- 结构化协议消息模型 `AgentMessage`（全字段）与 text/structured 上线表示计量（`serialization.py`）。
- 指标采集器 `MetricsCollector`（覆盖 16 项指标 + 派生指标）。
- 多 Agent 运行时：`BaseAgent`（状态机/超时/重试/失败隔离）、`RunContext`、`Channel`、`Orchestrator`（四阶段流水线）。
- 四类 Agent：Planner / Retriever / CodeActExecutor / ReviewerSummarizer。
- CLI（`version` / `demo` / `benchmark`+`report` 占位）与 demo 场景。
- 测试：providers / metrics / 端到端双模式（13 项全过）；ruff、mypy 通过。
- 验证：demo 下 structured 相比 text 节省约 32.6% 通信 token，成功率保持。

### P2 — 结构化通信、握手和能力发现
- 协议 schema 校验与版本兼容（`protocol/schema.py`）；JSON Schema 导出。
- 结构化编解码往返（`serialization.encode/decode_structured`，显式短键映射）。
- 协议映射 text↔structured（`protocol/mapper.py`）+ 语义等价断言。
- 幂等控制（`protocol/idempotency.py`，相同请求复用结果）。
- 注册表：注册 / 握手 / 能力发现（`registry/`），Agent 名片。
- 编排器集成握手 + 能力发现路由 + 幂等去重。
- 文档：`docs/PROTOCOL_SPEC.md`。
- 测试：协议 / 注册 / 双模式公平性（共 26 项全过）；ruff、mypy 通过。

### P3 — 非文本状态与 Artifact Reference
- 内容寻址 Artifact 存储（`artifact_store/`）：URI、内容去重、引用计数 GC、作用域、失效检测与降级。
- 非文本状态交换（`state_exchange/`）：embedding / compact state vector / plan DAG 的生成、存储、传输与解释。
- 共享内存向量缓冲（`SharedVectorBuffer`）：可选 `multiprocessing.shared_memory`，不可用自动降级。
- 编排器引用化：状态/事实/证据以引用承载，消息不内联全文；接收方真实消费 plan embedding（语义排序）。
- 文档：`docs/STATE_EXCHANGE.md`。
- 测试：artifact / state / 状态模式（共 39 项全过）；ruff、mypy 通过。
- 验证：Demo 中 C（结构化+状态+引用）相对文本基线节省约 85% 通信 token，成功率保持 100%。

### P4 — 共享记忆存储、检索、质量控制和复用
- 统一记忆单元 `MemoryRecord`（全部必选 + 建议元数据）、四类记忆 `MemoryType`。
- SQLite 元数据 + 可插拔向量后端（`memory/vector_backend.py`，numpy 默认，hnswlib/faiss 可选）。
- `MemoryStore`：写入、去重（语义近重+内容签名）、版本链接、关键词/标签/语义混合检索、质量控制、错误记忆降权、provenance、复用反馈。
- 命中分级度量：Retrieved / Used / Effective / Harmful；有效命中率。
- 接入 Agent：Reviewer 沉淀记忆 + 写回反馈；Retriever 检索复用；Executor 复用结论跳过重复计算。
- 文档：`docs/SHARED_MEMORY.md`。
- 测试：记忆存储 / 检索 / 跨任务复用（共 51 项全过）；ruff、mypy 通过。
- 验证：相似任务第二次运行命中并有效复用，工具调用（重复计算）减少。

### P5 — CodeAct 沙箱与资源限制
- `ExecutionResult`（stdout/stderr/exit code/timeout/资源/截断/backend）。
- 系统能力探测（`sandbox/capabilities.py`：rlimit/cgroup v2/namespace/共享内存/UDS/podman/bwrap）+ 后端选择降级。
- `CodeActExecutor`：subprocess + timeout + `setrlimit`（CPU/内存/文件/句柄/进程数）+ 工作目录隔离 + 环境白名单 + Python `-I` + 独立进程组超时清理 + 输出限制；可选 Podman（`--network=none`）降级。
- Executor Agent 接入沙箱：确定性生成 Python 代码并执行，解析结果，stdout 落 artifact，失败降级。
- 测试：基础执行/非零退出/超时/输出截断/能力概览/全流程 CodeAct（共 57 项全过）；ruff、mypy 通过。

### P6 — 连续任务、稳定性、故障恢复
- 可复用代码策略（`agents/code_strategies.py`）：零除防护、加日志+异常处理。
- 任务签名（`memory/signature.py`）：区分「同一子问题（复用结论）」与「相似子问题（复用策略）」。
- 泛化记忆复用：Retriever 复用结论或策略；Executor 支持 `codefix`（应用策略 + 沙箱验证）与算术两类操作。
- 关联连续任务组（自动验收、沙箱验证）：A 相似缺陷修复（A1→A2 复用修复策略）、B 重复工程改造（B1→B2 复用改造规范）。
- 稳定性：10 轮连续执行（成功率与 RSS 增长检查）+ 故障注入（Agent 崩溃隔离 / LLM 暂时失败恢复 / 记忆库不可用降级 / 引用失效降级）。
- 测试：场景 A/B 复用、10 轮稳定、故障注入（共 66 项全过）；ruff、mypy 通过。
- 验证：A2/B2 在不提供策略时，仅靠复用 A1/B1 的过程性记忆即可通过沙箱验收；无记忆时失败，证明复用价值。

### P7 — 对照实验、消融实验和统计分析
- 统计聚合（`evaluation/stats.py`：均值/std/P50/P95）。
- 实验运行器（`evaluation/runner.py`）：4 组主实验 + 6 项消融，16 指标聚合 + 派生指标，结果带时间戳落 `results/`（不覆盖）。
- 报告生成（`evaluation/report.py`）+ CLI `benchmark` / `report`。
- 实验产出（真实数据）：C/D 相对文本基线节省 **85.1%** token，成功率 100%；D 有效记忆命中率 1.00、重复计算降低 12.5%；消融定位 token 节省来自非文本状态、重复计算降低来自共享记忆；诚实记录 CodeAct 沙箱的时延权衡。
- 文档：`docs/EXPERIMENT_REPORT.md`；原始数据 `results/<ts>-main`、`results/<ts>-ablation`。
- 测试：统计/主实验冒烟/记忆复用（共 69 项全过）；ruff、mypy 通过。

### P8 — openEuler 适配与一键部署
- 六个脚本：`bootstrap.sh`（dnf）/`install.sh`（venv/uv，幂等）/`run_tests.sh`/`run_demo.sh`/`run_benchmark.sh`/`verify_openeuler.sh`。
- 脚本要求：幂等、dnf 非 apt、隔离 Python 环境、明确 root 步骤、不提交 Key、支持 .env、能力检测可降级。
- `verify_openeuler.sh` 输出 OS/内核/架构/Python/依赖/cgroup v2/共享内存/Socket/沙箱/测试摘要/10 轮稳定性摘要。
- 文档：`docs/DEPLOYMENT.md`；`docs/OPEN_EULER_COMPATIBILITY.md`（待用户在 openEuler VM 回填实测）。

### P9 — Demo、报告、视频脚本和答辩材料
- 零依赖静态 Dashboard 生成器（`dashboard/generate_dashboard.py` → `dashboard/index.html`）。
- 交付文档补齐：`DESIGN` / `TEST_REPORT` / `EXPERIMENT_REPORT` / `VIDEO_SCRIPT` / `PPT_OUTLINE` / `JUDGE_QA` / `LIMITATIONS` / `DELIVERABLES`。
- 答辩 PPT：`deliverables/build_ppt.py` 生成 `deliverables/答辩PPT.pptx`（12 页，Midnight Executive 配色，内容 QA 通过）。
- 需求追踪矩阵全部状态更新并附证据；README 文档索引补全。
- 最终质量门禁：69 测试全过、覆盖率 78%、ruff/format/mypy 全部通过。
