# 结构化通信协议规范 (PROTOCOL_SPEC)

> 协议版本：`1.0`。实现：`src/agent_runtime/protocol/`。

## 1. 设计原则

- **高密度语义单元**：通信内容收敛为「动作 / 参数 / 结果 / 能力」，而非自然语言长文本。
- **引用而非搬运**：长内容（日志、代码、文档、向量）以 `artifact://` / `state://` / `memory://` / `vector://` 引用 + 摘要承载。
- **唯一真源**：`AgentMessage`（Pydantic 模型）是协议唯一真源；`text_mode` 由映射器渲染为自然语言，仅用于基线对比。
- **可校验 / 可路由 / 可幂等 / 可追踪**：结构化消息支持 schema 校验、能力路由、幂等去重、全链路 trace。

## 2. 消息字段 (`AgentMessage`)

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| protocol_version | str | 协议版本，主版本一致即兼容 |
| message_id | str | 全局唯一消息 ID |
| trace_id | str | 全链路追踪 ID |
| task_id | str | 任务 ID |
| step_id | str | 步骤 ID |
| source_agent | str | 源 Agent |
| target_agent | str | 目标 Agent |
| timestamp | float | 生成时间戳 |
| action_type | enum | 动作类型（见下） |
| capability | str | 能力描述 |
| input_parameters | dict | 输入参数（结构化模式会收敛长内容） |
| result | dict? | 结果 |
| status | enum | pending/ok/error/timeout/retry/skipped |
| dependencies | list[str] | 依赖步骤 |
| artifact_references | list[str] | artifact 引用 |
| evidence_references | list[str] | 证据引用 |
| state_reference | str? | 非文本状态引用（state:// / vector://） |
| confidence | float? | 置信度 |
| error | dict? | 错误详情 |
| metrics | dict | 开销度量（tokens/bytes/latency 等） |
| idempotency_key | str? | 幂等键 |

### ActionType
`register / handshake / discover / plan / retrieve / execute / review / summarize / memorize / result / error / ack`

### MessageStatus
`pending / ok / error / timeout / retry / skipped`

## 3. 传输表示与开销计量

同一条消息有两种「上线」表示（`protocol/serialization.py`）：

- **text_mode**（`render_text`）：冗长自然语言，内联完整内容——模拟传统「全文透传」。
- **structured_mode**（`encode_structured`）：紧凑 JSON（短键 + 引用），长内容收敛为摘要 + 引用。

计量口径统一为 token（BPE 近似，可切 tiktoken）与字符数，保证双模式对比公平。
结构化模式支持核心字段无损往返（`decode_structured`）；文本模式解析是有损的
（自然语言不携带稳定机器结构），这正是结构化协议的优势。

## 4. 协议机制

| 机制 | 实现 | 说明 |
| --- | --- | --- |
| schema 校验 | `protocol/schema.py::validate_message` | Pydantic 校验 + 版本兼容检查，失败抛 `ProtocolError` |
| 协议版本 | `is_compatible` | 主版本一致即兼容 |
| 注册 / 握手 | `registry/registry.py::handshake` | 协议协商，兼容则注册 |
| 能力发现 | `registry/registry.py::discover` | 按能力解析到具体 Agent，驱动路由 |
| 协议映射 | `protocol/mapper.py::to_wire/from_wire` | text ↔ structured 双向转换 |
| 幂等 | `protocol/idempotency.py` | 相同请求复用缓存结果，降低重复计算 |
| 超时 / 重试 | `runtime/agent.py::BaseAgent.run` | 超时控制 + 重试 + 失败隔离 |
| 错误响应 | `BaseAgent._error_message` | 失败返回 error 消息而非崩溃 |
| 全链路 trace | trace_id/task_id/step_id | 贯穿所有消息与日志 |

## 5. JSON Schema

完整 JSON Schema 可通过以下方式导出：

```python
from agent_runtime.protocol.schema import message_json_schema
import json; print(json.dumps(message_json_schema(), ensure_ascii=False, indent=2))
```

## 6. 公平性保证

`text_mode` 与 `structured_mode` 共享同一 `AgentMessage`、同一 Agent 逻辑、同一
Provider、温度、max_tokens、重试与随机种子；差异仅在传输表示。
`mapper.semantically_equivalent` 用于断言两模式核心语义一致。
