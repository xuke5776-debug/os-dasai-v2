# 演示视频脚本（3–5 分钟）

> 目标：清晰展示「系统层机制」与可复现实验结果。建议屏幕录制 + 旁白。

## 0:00–0:30 开场与问题（30s）
- 旁白：「多 Agent 协作普遍用自然语言/JSON 透传中间结果，导致 token 高、时延大、经验难复用。
  我们从系统层解决：低开销通信、非文本状态传递、共享记忆复用。」
- 画面：标题页 + 架构图（`docs/ARCHITECTURE.md`）。

## 0:30–1:10 架构与四类 Agent（40s）
- 旁白：「Planner / Retriever / CodeAct-Executor / Reviewer 四类 Agent；统一结构化协议、
  注册握手与能力发现；核心运行时、协议、状态交换、共享记忆全部自研。」
- 画面：目录结构 `src/agent_runtime/` + 协议字段表（`docs/PROTOCOL_SPEC.md`）。

## 1:10–2:10 Demo：双模式通信对比（60s）
- 终端执行：`bash scripts/run_demo.sh`
- 旁白：「同一任务、同一智能体、同一 LLM 调用次数。A 文本基线内联全文；
  C 引入结构化协议 + 非文本状态 + Artifact 引用。」
- 画面：高亮输出 —— **C 相对 A 节省约 85% token，成功率保持 100%**，并出现 state_transfers 与 artifact_refs。

## 2:10–3:10 共享记忆与连续任务（60s）
- 旁白：「任务组 A：A1 修复零除缺陷并把修复策略沉淀为过程性记忆；
  A2 修复相邻模块——不提供策略，仅靠复用 A1 的记忆即可通过沙箱验收。」
- 终端执行：`pytest tests/integration/test_scenarios.py -q`
- 旁白：「无记忆时 A2 失败，证明复用带来跨任务可迁移能力，而非简单缓存。」
- 画面：CodeAct 沙箱执行修复后的代码并跑测试通过。

## 3:10–4:10 实验与消融（60s）
- 终端执行：`bash scripts/run_benchmark.sh 5 42`
- 画面：报告表格 + Dashboard（`dashboard/index.html`）。
- 旁白：「4 组主实验 + 消融：Token 节省主要来自非文本状态与引用；重复计算降低主要来自共享记忆；
  有效记忆命中率 1.0、无负迁移。所有数据来自 results/ 原始文件，不可覆盖、可复现。」

## 4:10–4:40 openEuler 与稳定性（30s）
- 终端执行：`bash scripts/verify_openeuler.sh`（openEuler VM）
- 旁白：「面向 openEuler 24.03-LTS-SP3，dnf 一键部署；cgroup v2/共享内存/Podman 可用则启用，
  不可用自动降级；10 轮连续稳定、故障注入可恢复。」

## 4:40–5:00 收尾（20s）
- 旁白：「我们交付的是多 Agent 协作的系统层基础设施：低开销、可解释、可复现、可在 openEuler 运行。」
- 画面：评分点对照表（通信效率/状态创新/记忆复用/系统完整/实验验证）。
