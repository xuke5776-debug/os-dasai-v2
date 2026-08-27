# 实验计划 (EXPERIMENT_PLAN)

## 1. 实验目标

证明结构化通信、非文本状态传递、共享记忆复用相较纯文本协作在 **通信开销、任务时延、记忆复用** 上的改进，同时**不牺牲任务成功率**。

## 2. 连续任务场景（自动验收、纯软件、可复现）

> 场景：多 Agent 软件仓库维护。固定输入、有标准答案、可重复执行。

### 任务组 A：相似缺陷修复
- **A1**：定位并修复 Python 项目的异步测试 / 资源释放问题（如未 `await`、未关闭文件/连接）。
- **A2**：修复同仓库/相似仓库中的相关问题。
- **验证点**：A2 是否复用 A1 的代码结构、错误模式、工具轨迹与修复经验（记忆命中且有效）。

### 任务组 B：重复软件工程改造
- **B1**：给一个模块增加日志、异常处理和测试。
- **B2**：给相邻模块执行相同规范的改造。
- **验证点**：B2 是否复用 B1 的规范、补丁模板、策略与证据。

每组均支持：固定输入 / 自动验收 / 可重复 / text_mode 与 structured_mode / 有记忆与无记忆 / 统计质量·token·时延·消息量·复用。

## 3. 四组主实验

| 实验 | 配置 | 说明 |
| --- | --- | --- |
| A | Text Baseline | 纯文本协作基线 |
| B | Structured Protocol | 结构化协议（无状态交换、无记忆） |
| C | Structured + State Exchange | 结构化协议 + 非文本状态 |
| D | Full System | 协议 + 状态 + 共享记忆 + CodeAct + 可观测性 |

## 4. 消融实验

- 去掉 embedding（仅关键词检索）；
- 去掉 Artifact Reference（回退全文传输）；
- 去掉共享记忆；
- 去掉 rerank；
- 比较序列化协议（JSON vs MessagePack vs Protobuf）；
- 比较 Top-K（1/3/5/10）；
- 比较摘要粒度（粗/中/细）。

## 5. 指标定义（16 项）

| # | 指标 | 采集点 |
| --- | --- | --- |
| 1 | Agent 消息次数 | scheduler/bus |
| 2 | 文本 token / 字符数 | providers tokenizer + 消息载体 |
| 3 | 非文本状态次数和字节数 | state_exchange |
| 4 | Artifact 引用次数 | artifact_store |
| 5 | 端到端耗时 | observability |
| 6 | P50 / P95 | evaluation 聚合 |
| 7 | LLM 调用次数 | providers |
| 8 | 工具调用与重复调用次数 | sandbox/tools |
| 9 | 记忆检索命中率 (Retrieved Hit) | memory |
| 10 | 有效记忆命中率 (Effective Hit) | memory + reviewer 反馈 |
| 11 | 任务成功率 | scenarios 自动验收 |
| 12 | 任务质量 | scenarios 评分（测试通过率/规范符合度） |
| 13 | CPU 使用率 | psutil |
| 14 | RSS 峰值 | psutil |
| 15 | 10 轮稳定性 | stability |
| 16 | 错误和降级次数 | observability |

### 派生指标
- **Token 节省率** = 1 − structured_tokens / text_tokens
- **时延改善率** = 1 − structured_latency / text_latency
- **重复计算降低率** = 1 − optimized_repeated_calls / baseline_repeated_calls
- **有效记忆命中率** = 正向作用记忆数 / 实际使用记忆数

### 记忆命中分级
- **Retrieved Hit**：被检索返回。
- **Used Hit**：被 Agent 实际使用（进入上下文/决策）。
- **Effective Hit**：使用后对任务产生正向作用。
- **Harmful Hit / Negative Transfer**：使用后产生负向作用。

## 6. 公平性协议

- 固定：模型/版本、temperature、max_tokens、任务、Agent 数量、工具集、重试上限、随机种子。
- 每种配置至少重复 **5 次**（建议 5–10）。
- 报告：均值、标准差、P50、P95；**同时报告成功率**，不得以准确率换 token。
- 保存原始日志、配置与带时间戳结果到 `results/<timestamp>/`；**禁止覆盖旧实验**。

## 7. 结果目录约定

```
results/
└── 20260625-1540-<config_hash>/
    ├── config.yaml          # 本次实验完整配置快照
    ├── raw/                 # 每次重复的原始日志与 metrics
    │   ├── run_01.jsonl
    │   └── ...
    ├── summary.json         # 聚合指标（均值/std/P50/P95/成功率）
    └── report.md            # 人类可读小结
```

## 8. 复现命令

```bash
python -m agent_runtime.cli benchmark --suite main --repeat 5 --seed 42
python -m agent_runtime.cli benchmark --suite ablation --repeat 5 --seed 42
python -m agent_runtime.cli report --results results/<timestamp>
```
