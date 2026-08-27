# 需求追踪矩阵 (Requirements Traceability Matrix)

> 逐条映射《赛题要求.docx》到实现模块、验收标准、测试与交付证据。
> 状态图例：✅ 已完成 / 🚧 进行中 / ⬜ 待办

## 强制要求

| ID | 赛题原文摘要 | 必选 | 评分项 | 实现模块 | 验收/测试与交付证据 | 状态 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | ≥3 Agent，覆盖规划/检索/执行/总结中≥3 类，完成多步骤复杂任务 | 是 | 系统完整性 | `agents/`,`runtime/`,`scheduler` | 四类 Agent；`test_dual_mode`,`test_scenarios` | ✅ |
| R2 | 结构化通信：动作/参数/结果/能力；握手/能力发现/协议映射；不透传全文 | 是 | 通信效率 | `protocol/`,`registry/` | `test_protocol`,`test_registry`；`docs/PROTOCOL_SPEC.md` | ✅ |
| R3 | 同时支持 text_mode 与 structured_mode，相同条件可复现对比 | 是 | 通信效率/实验验证 | `serialization`,`mapper`,`evaluation` | `test_dual_mode`；`docs/EXPERIMENT_REPORT.md` | ✅ |
| R4 | 非文本状态传递，说明生成/传递/接收/使用 | 是 | 状态传递创新 | `state_exchange/` | `test_state_mode`（断言被消费）；`docs/STATE_EXCHANGE.md` | ✅ |
| R5 | 共享记忆，统一记忆单元含 5 项必选元数据 | 是 | 记忆复用 | `memory/` | `test_memory`；`docs/SHARED_MEMORY.md` | ✅ |
| R6 | 关键词/标签/语义检索，跨 Agent 复用 | 是 | 记忆复用 | `memory/store` | `test_memory_retrieval`,`test_memory_reuse` | ✅ |
| R7 | ≥2 组关联连续任务，验证收益 | 是 | 实验验证 | `scenarios/task_group_a`,`task_group_b` | `test_scenarios`；`docs/EXPERIMENT_REPORT.md` | ✅ |
| R8 | 统计消息/token/状态/耗时/命中率/性能提升 | 是 | 实验验证/通信效率 | `observability/`,`evaluation/` | `results/<ts>-*`；16 指标 + 派生 | ✅ |
| R9 | 架构五大模块；≥10 轮稳定 | 是 | 系统完整性 | 全部模块 | `test_10rounds`,`test_fault_injection` | ✅ |
| R10 | 提交源码/设计/部署/实验报告/演示视频 | 是 | 全部 | `docs/`,`scripts/`,`dashboard/` | 源码+全套 docs+视频脚本（录制待出） | 🚧 |

## 鼓励 / 加分项

| ID | 赛题原文摘要 | 评分项 | 实现 | 证据 | 状态 |
| --- | --- | --- | --- | --- | --- |
| E1 | IPC/共享内存/Socket | 状态创新/系统完整 | `SharedVectorBuffer`(shared_memory)、UDS 设计 | `test_state_exchange`；`docs/STATE_EXCHANGE.md` | ✅ |
| E2 | 向量数据库 | 记忆复用 | 可插拔 hnswlib/faiss | `memory/vector_backend.py` | ✅ |
| E3 | WASM/容器沙箱 | 系统完整 | Podman(`--network=none`) 可降级 | `sandbox/executor.py`；openEuler 验证待回填 | 🚧 |
| E4 | eBPF | — | 后期可选，不在关键路径 | `docs/LIMITATIONS.md` | ⬜ |
| E5 | CodeAct（LLM 生成代码沙箱执行） | 系统完整/状态创新 | `sandbox/`,`agents/codeact` | `test_sandbox`,`test_scenarios` | ✅ |

## 环境约束

| ID | 约束 | 处理 | 状态 |
| --- | --- | --- | --- |
| C1 | 在 openEuler 24.03-LTS-SP3 正常编译/运行/测试 | `scripts/verify_openeuler.sh` + 兼容报告 | 🚧（待用户 VM 实测回填） |
| C2 | 纯软件，无 GPU/NPU/专用硬件 | CPU-only、mock-first | ✅ |
| C3 | 无 API Key 仍可运行测试 | 确定性 mock provider | ✅ |

## 最易遗漏要求（已落实防控）

1. 非文本状态必须被消费 → `test_state_mode` 断言 `state_consumed`、消融验证。✅
2. 双模式公平性 → 同源 `AgentMessage` + 固定 LLM 调用/温度/种子。✅
3. 同时报告成功率 → 实验报告所有配置成功率 100%。✅
4. ≥10 轮稳定 + 故障恢复 → `tests/stability/`。✅
5. 实验不可覆盖、带时间戳 → `results/<ts>-*`。✅
