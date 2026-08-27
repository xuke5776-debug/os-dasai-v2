# 共享记忆机制说明 (SHARED_MEMORY)

> 实现：`src/agent_runtime/memory/`。

## 1. 目标

把任务执行过程中的摘要、证据、策略、经验沉淀为**可标识、可检索、可复用**的记忆单元，
使系统在处理相似任务时复用既有结论，减少重复计算与协作开销，实现跨任务知识积累。

## 2. 统一记忆单元 (`MemoryRecord`)

必选基本元数据：`memory_id` / `source_agent` / `created_at` / `task_topic` / `summary`。

扩展元数据：`memory_type` / `tags` / `keywords` / `embedding_ref` / `artifact_refs` /
`evidence_refs` / `confidence` / `quality_score` / `reuse_count` / `last_accessed_at` /
`version` / `parent_version` / `expiration_policy` / `provenance` / `task_id` /
`success_feedback` / `payload`（结构化结论，便于直接复用）。

## 3. 记忆分型

| 类型 | 含义 | 示例 |
| --- | --- | --- |
| Working | 当前任务临时上下文 | 中间变量 |
| Episodic | 具体任务经历 | 某次修复的轨迹与证据 |
| Semantic | 抽象事实/知识 | 某 API 的行为约定 |
| Procedural | 可复用策略/模板/流程 | 「加日志+异常+测试」的补丁模板 |

## 4. 存储与检索

- **元数据**：SQLite（`:memory:` 或文件持久化，支持跨任务/跨会话复用）。
- **向量**：可插拔后端（默认 numpy 暴力；可切 hnswlib / faiss），L2 归一化内积≈余弦。
- **检索**：关键词 / 标签 / 语义 **混合**评分：`0.6·语义 + 0.25·关键词 + 0.15·标签`，
  再乘质量权重 `(0.5 + 0.5·quality_score)`；低于质量阈值的记忆默认排除。

## 5. 质量控制与版本

- **去重**：语义近重（余弦 ≥ 0.97）+ 内容签名（topic+summary 规范化）。完全重复则提升
  `reuse_count` 而不新建；语义近重则作为新 `version` 链接 `parent_version`。
- **错误记忆降权**：`success_feedback=False` 写入时 `quality_score ≤ 0.2`；负迁移反馈再降权，
  逐步跌破阈值而被检索排除（隔离）。
- **provenance**：记录 trace_id 与参与 Agent，可追溯来源。

## 6. 命中分级度量

| 指标 | 含义 | 记录位置 |
| --- | --- | --- |
| Retrieved Hit | 被检索返回 | Retriever 检索后 `record_memory(retrieved=...)` |
| Used Hit | 被实际复用（进入决策） | Retriever 复用时 `record_memory(used=1)` + `mark_used` |
| Effective Hit | 复用后任务成功（正向作用） | Reviewer 验收后 `record_memory(effective=1)` + `record_feedback(True)` |
| Harmful Hit | 复用后任务失败（负迁移） | Reviewer 验收后 `record_memory(harmful=1)` + `record_feedback(False)` |

**有效记忆命中率** = Effective / Used。

## 7. 复用如何降低重复计算

1. Reviewer 在任务成功后写入过程性记忆（含 `payload.answer` 等结论）。
2. 下一次相似任务，Retriever 检索命中并标记复用，将结论写入黑板 `reused_answer`。
3. Executor 检测到 `reused_answer` 则**跳过重复计算**，直接复用结论（不记录 compute 工具调用）。

集成测试 `tests/integration/test_memory_reuse.py` 验证：第二次运行检索命中、有效复用，
且工具调用（重复计算）数量低于第一次。

## 8. 跨任务复用的装配

跨任务复用需共享同一 `MemoryStore`：实验/场景运行器创建一个共享实例并注入各次运行的
`RunContext`（见 `build_context(..., memory=shared_store)`）。
