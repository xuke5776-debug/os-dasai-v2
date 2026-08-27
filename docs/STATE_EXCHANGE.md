# 非文本状态传递机制说明 (STATE_EXCHANGE)

> 实现：`src/agent_runtime/state_exchange/` 与 `src/agent_runtime/artifact_store/`。

## 1. 目标

减少「内部状态 → 文本 → 内部状态」的反复编解码，让中间表示在 Agent 间**直接交换**，
并被接收方**真实消费**（参与检索 / 路由 / 决策 / 上下文构建），从而降低通信开销且不损失任务质量。

## 2. 三类非文本状态

| 类型 | 生成方式 | 数据类型/维度 | 用途（接收方消费） |
| --- | --- | --- | --- |
| embedding / 语义向量 | embedding provider 对文本编码 | float32, (dim,)，默认 256 | 语义相似度排序、检索路由 |
| compact state vector | 对计划/进度提取数值特征 | float32, (3,)：[operand 数, 操作码, 是否有 operand] | 接收方快速判断计划规模/类型 |
| plan DAG | Planner 生成的结构化计划图 | dict（operation + operands + 依赖） | 接收方据此还原 operands、调度执行 |

## 3. 生成 → 传输 → 接收 → 使用

```
Planner 产出 plan(dict)
   │  put_plan_state(plan)
   ▼
StateExchange: 计算 embedding + compact vector，内容寻址存储
   │  返回 StateRef(uri="state://task/<hash>")
   ▼
消息仅携带 state_reference = "state://..."（不内联计划全文）
   │  Channel 计量：state_transfers += 1, state_bytes += nbytes
   ▼
Retriever 收到 state_reference
   │  get_plan_state(uri)  → {dag, embedding, vector}
   ▼
真实消费：用 plan embedding 对 operands 做语义相似度排序（影响检索顺序），
          用 dag 还原 operands 列表 → 进行检索（而非重新解析文本）
```

- **传输**：大向量通过 `SharedVectorBuffer` 传递，可选 `multiprocessing.shared_memory`
  （系统层零拷贝，openEuler 上可经 `AGENT_STATE_SHM=true` 开启），不可用时自动降级进程内拷贝。
- **存储**：内容寻址（哈希），天然去重；`state://` / `vector://` URI 引用。

## 4. 如何减少文本传输

- 计划、事实表、证据等**长内容只存一次**，消息仅传引用（`state://`、`artifact://`）+ 简短摘要。
- Demo 实测（30 条知识库的求和任务，相对纯文本基线）：

| 配置 | text_tokens | state_transfers | artifact_refs | 成功 |
| --- | --- | --- | --- | --- |
| A 文本基线 | 2547 | 0 | 0 | ✅ |
| B 结构化协议 | 2393 (−6.0%) | 0 | 0 | ✅ |
| C 结构化 + 非文本状态 + 引用 | 377 (**−85.2%**) | 2 | 2 | ✅ |

> 复现：`python -m agent_runtime.cli demo`。数据随实现演进可能微调，以实际运行为准。

## 5. 是否影响任务成功率

不影响。三种配置在 Demo 与单测中成功率均为 100%（`tests/integration/test_state_mode.py`）。
非文本状态仅替换通信载体并增强检索决策，不改变任务语义。

## 6. 鲁棒性：引用失效降级

- `get_plan_state` / `get_json` 在引用失效时抛 `ReferenceError_`；
- 接收方捕获后记录 `degradation`，回退到空内容/文本路径，不会导致运行时崩溃；
- 单测：`test_artifact_store.py::test_invalidate_triggers_reference_error`、
  `test_state_exchange.py::test_invalidate_state_raises`。

## 7. Artifact Reference 机制

详见消息字段 `artifact_references` / `state_reference`。URI 规范：

- `artifact://task/{task_id}/{artifact_id}` / `artifact://global/{artifact_id}`
- `state://{scope}/{state_id}`、`vector://{scope}/{vector_id}`

支持：内容寻址稳定 ID、引用计数、垃圾回收（`collect`）、作用域（task/global）、失效检测与降级。
