# 交付物清单 (DELIVERABLES)

赛题要求的 17 项交付物与本仓库对应位置：

| # | 交付物 | 位置 |
| --- | --- | --- |
| 1 | 完整源代码 | `src/agent_runtime/`、`scenarios/`、`tests/`、`scripts/`、`dashboard/` |
| 2 | README | `README.md` |
| 3 | 概要与详细设计 | `docs/DESIGN.md`、`docs/ARCHITECTURE.md` |
| 4 | 通信协议规范 | `docs/PROTOCOL_SPEC.md` |
| 5 | 非文本状态机制说明 | `docs/STATE_EXCHANGE.md` |
| 6 | 共享记忆机制说明 | `docs/SHARED_MEMORY.md` |
| 7 | 部署文档 | `docs/DEPLOYMENT.md` |
| 8 | openEuler 兼容报告 | `docs/OPEN_EULER_COMPATIBILITY.md`（实测待 VM 回填） |
| 9 | 测试报告 | `docs/TEST_REPORT.md` |
| 10 | 性能实验报告 | `docs/EXPERIMENT_REPORT.md` |
| 11 | 原始实验数据 | `results/<timestamp>-main/`、`results/<timestamp>-ablation/` |
| 12 | 复现脚本 | `scripts/*.sh`、`python -m agent_runtime.cli benchmark` |
| 13 | Demo | `scripts/run_demo.sh`、`dashboard/index.html`（`dashboard/generate_dashboard.py`） |
| 14 | 3–5 分钟视频脚本 | `docs/VIDEO_SCRIPT.md` |
| 15 | 答辩 PPT 大纲 + PPT | `docs/PPT_OUTLINE.md`、`deliverables/答辩PPT.pptx`（`deliverables/build_ppt.py`） |
| 16 | 评委问题与回答 | `docs/JUDGE_QA.md` |
| 17 | 已知限制与未来工作 | `docs/LIMITATIONS.md` |

## 过程与治理文档

| 文档 | 位置 |
| --- | --- |
| 需求追踪矩阵 | `docs/REQUIREMENTS_TRACEABILITY.md` |
| 路线图 | `docs/ROADMAP.md` |
| 实验计划 | `docs/EXPERIMENT_PLAN.md` |
| 风险登记册 | `docs/RISK_REGISTER.md` |
| 决策记录 | `docs/DECISIONS.md` |
| 变更日志 | `CHANGELOG.md` |
| 会话恢复备忘 | `CLAUDE.md` |

## 每条赛题要求 → 证据

见 `docs/REQUIREMENTS_TRACEABILITY.md`：每条要求均有代码、测试、日志/实验或文档证据。
