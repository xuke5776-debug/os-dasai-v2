# 路线图 (ROADMAP) P0–P9

每阶段给出：目标 / 输入 / 输出 / 关键文件 / 测试 / 验收标准 / 风险 / 回滚。

---

## P0 需求分析与架构冻结
- **目标**：项目骨架 + 规划文档 + 需求追踪矩阵。
- **输入**：赛题要求.docx、总控提示词。
- **输出**：目录结构、pyproject、配置样例、全套 docs。
- **关键文件**：`pyproject.toml`, `CLAUDE.md`, `README.md`, `docs/*`。
- **测试**：文档自检（结构完整）。
- **验收**：需求追踪矩阵覆盖所有强制要求；架构方案冻结。
- **风险**：需求理解偏差。**回滚**：修订 docs，不影响代码。

## P1 最小多 Agent Runtime 与纯文本基线
- **目标**：asyncio 运行时 + 四类 Agent + Provider 抽象 + mock + text_mode。
- **输入**：P0 架构。
- **输出**：可运行的 text_mode 端到端协作。
- **关键文件**：`runtime/`, `agents/`, `providers/`, `observability/`。
- **测试**：`tests/unit/test_providers.py`, `tests/integration/test_text_mode.py`。
- **验收**：mock 下完成一个多步任务并输出指标。
- **风险**：异步调度死锁。**回滚**：退化为同步顺序执行。

## P2 结构化通信、握手和能力发现
- **目标**：Pydantic 协议全字段 + schema 校验 + 注册/握手/能力发现 + text↔structured 映射 + 幂等/重试/trace。
- **输出**：structured_mode 与 text_mode 公平对比。
- **关键文件**：`protocol/`, `registry/`, `scheduler/`。
- **测试**：`tests/unit/test_protocol.py`, `test_registry.py`, `tests/integration/test_dual_mode.py`。
- **验收**：两模式同任务可运行，结构化 token 明显更低且成功率不降。
- **风险**：映射不等价导致不公平。**回滚**：固定映射模板并断言一致性。

## P3 非文本状态与 Artifact Reference
- **目标**：embedding/compact state vector/plan DAG 交换（shared_memory 传输）+ 内容寻址 Artifact Store。
- **输出**：接收方真实消费状态；消息只带引用。
- **关键文件**：`state_exchange/`, `artifact_store/`。
- **测试**：`tests/unit/test_state_exchange.py`, `test_artifact_store.py`。
- **验收**：状态参与检索/路由；引用失效自动降级。
- **风险**：shared_memory 句柄泄漏。**回滚**：降级为序列化传输。

## P4 共享记忆存储、检索、质量控制和复用
- **目标**：统一记忆单元 + SQLite + 向量后端 + 四类记忆 + 检索/去重/版本/质量/provenance + 命中指标。
- **输出**：跨任务记忆复用。
- **关键文件**：`memory/`。
- **测试**：`tests/unit/test_memory*.py`。
- **验收**：Retrieved/Used/Effective/Harmful Hit 可统计；复用降低重复计算。
- **风险**：负迁移。**回滚**：质量分阈值过滤 + 关闭语义检索回退关键词。

## P5 CodeAct 沙箱与资源限制
- **目标**：LLM 生成 Python 在受限环境执行，返回完整结果。
- **输出**：subprocess+timeout+rlimit；cgroup v2/namespace/Podman 可降级。
- **关键文件**：`sandbox/`, `agents/codeact`。
- **测试**：`tests/unit/test_sandbox.py`, `tests/openeuler/test_cgroup.py`。
- **验收**：超时/内存/输出限制生效；残留进程清理。
- **风险**：平台差异。**回滚**：仅 subprocess+timeout。

## P6 连续任务、10 轮稳定性、故障恢复
- **目标**：任务组 A/B + ≥10 轮稳定 + 故障注入恢复。
- **关键文件**：`scenarios/`, `tests/stability/`。
- **测试**：`tests/stability/test_10rounds.py`, `test_fault_injection.py`。
- **验收**：10 轮无崩溃、无资源泄漏（RSS 稳定）。
- **风险**：内存增长。**回滚**：每轮重建运行时。

## P7 对照实验、消融实验和统计分析
- **目标**：4 组主实验 + 消融，16 指标 + 派生指标，统计分析。
- **关键文件**：`evaluation/`, `benchmarks/`。
- **测试**：benchmark smoke test。
- **验收**：结果落 `results/<ts>/`，含均值/std/P50/P95 与成功率。
- **风险**：实验不公平。**回滚**：固化配置矩阵与种子。

## P8 openEuler 适配与一键部署
- **目标**：六个脚本 + 兼容报告。
- **关键文件**：`scripts/*.sh`, `docs/OPEN_EULER_COMPATIBILITY.md`。
- **测试**：`tests/openeuler/`。
- **验收**：`verify_openeuler.sh` 输出齐全；用户在 openEuler VM 验证通过。
- **风险**：dnf 包差异。**回滚**：可选依赖降级。

## P9 Demo、报告、视频脚本和答辩材料
- **目标**：Dashboard/Demo + 全套交付文档 + 视频脚本 + 答辩 PPT。
- **关键文件**：`dashboard/`, `docs/*`, `*.pptx`。
- **验收**：17 项交付物齐全，每条赛题要求有证据。
- **风险**：时间不足。**回滚**：优先核心机制与实验报告。
