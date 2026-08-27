# 测试报告 (TEST_REPORT)

> 数据来自实际运行（开发环境 Python 3.11.9 / macOS arm64）。
> openEuler 目标环境结果由 `scripts/verify_openeuler.sh` 生成并回填兼容报告。

## 1. 测试规模与结果

- 测试用例：**69 项，全部通过**。
- 总体覆盖率：**78%**（`coverage report`）。
- 静态检查：`ruff check` 通过、`ruff format --check` 通过、`mypy src` 无错误。

复现：

```bash
bash scripts/run_tests.sh
# 或
pytest -q && ruff check src tests scenarios && mypy src && coverage run -m pytest && coverage report
```

## 2. 测试分层

| 层级 | 目录 | 覆盖内容 |
| --- | --- | --- |
| 单元 | `tests/unit/` | providers / tokenizer / metrics / protocol / registry / artifact / state / memory / 检索 / sandbox / evaluation |
| 集成 | `tests/integration/` | 端到端双模式 / 注册发现 / 状态模式 / 记忆复用 / 连续任务 A·B |
| 稳定性 | `tests/stability/` | 10 轮连续执行 + 故障注入（崩溃隔离 / LLM 暂失 / 记忆不可用 / 引用失效） |

## 3. 关键能力验证

| 能力 | 验证用例 | 结果 |
| --- | --- | --- |
| 双模式公平对比 | `test_dual_mode::test_dual_mode_fair_comparison` | 通过（同任务/同 LLM 调用，结构化省 token） |
| 协议 schema/版本/往返/幂等 | `test_protocol` | 通过 |
| 注册 / 握手 / 能力发现 | `test_registry` | 通过 |
| 非文本状态被真实消费 | `test_state_mode::test_state_mode_succeeds_and_consumes_state` | 通过 |
| Artifact 内容寻址 / GC / 失效 | `test_artifact_store` | 通过 |
| 记忆存储/去重/质量/反馈 | `test_memory` | 通过 |
| 记忆混合检索/质量过滤 | `test_memory_retrieval` | 通过 |
| 跨任务记忆复用降低重复计算 | `test_memory_reuse` | 通过 |
| 连续任务 A/B 策略复用 | `test_scenarios` | 通过（无记忆时 A2/B2 失败，证明复用价值） |
| CodeAct 沙箱（执行/超时/退出码/截断） | `test_sandbox` | 通过 |
| 10 轮连续稳定 + 内存可控 | `test_10rounds` | 通过 |
| 故障注入与恢复 | `test_fault_injection` | 通过 |
| 评测框架/派生指标 | `test_evaluation` | 通过 |

## 4. 覆盖率说明

- 核心模块（协议、记忆、状态交换、运行时、评测）覆盖率 90%+。
- `sandbox/executor.py` 覆盖率较低（约 65%）：未覆盖分支主要为 Podman 后端与平台特定错误路径
  （开发机为 macOS，cgroup/Podman 路径在 openEuler 验证）。subprocess 主路径已覆盖。

## 5. 已知告警

- 无失败、无 skip 滥用、无静默吞异常（异常均转为可观测的 error/degradation 指标）。
