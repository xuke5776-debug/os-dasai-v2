# 评委问题与回答 (Judge Q&A)

**Q1：你们和 LangGraph / AutoGen / CrewAI 有何本质区别？**
A：那些是工作流编排框架。我们实现的是协作的**系统层机制**并全部自研：结构化通信协议、
非文本状态的内容寻址与（可选）共享内存传输、跨任务共享记忆的检索/质量控制/复用、CodeAct 沙箱。
框架可作为适配器或对照，但不进核心路径。

**Q2：token 节省会不会以牺牲任务成功率为代价？**
A：不会。所有实验**同时报告成功率**，四组配置成功率均 100%。Token 节省来自「引用替代全文搬运」
与「短键结构化」，不改变任务语义。见 `docs/EXPERIMENT_REPORT.md`。

**Q3：非文本状态是不是「传了但没用」？**
A：被真实消费。Retriever 用 plan embedding 对检索目标做语义排序、用 plan DAG 还原 operands；
单测 `test_state_mode` 断言 `state_consumed` 且 `state_transfers>0`。去掉状态（消融）token 节省从 85% 退回 6%。

**Q4：共享记忆是不是只是缓存答案？**
A：不是。区分「同一子问题（复用结论）」与「相似子问题（复用策略）」。任务组 A/B 中，A2/B2
**不提供修复/改造策略**，仅靠复用 A1/B1 的过程性记忆即可通过沙箱验收；无记忆则失败。
并区分 Retrieved/Used/Effective/Harmful，错误记忆降权隔离。

**Q5：实验是否公平、可复现？**
A：固定模型/温度/max_tokens/工具/重试/随机种子；mock-first 确定性，无需 API Key；
每配置重复 5 次报告均值/std/P50/P95；结果带时间戳落 `results/` 且禁止覆盖。任何人可独立复核。

**Q6：CodeAct 沙箱安全性如何？为什么 D 配置时延变高？**
A：subprocess + timeout + setrlimit（CPU/内存/文件/句柄/进程）+ 目录隔离 + 环境白名单 +
Python `-I` + 独立进程组超时清理 + 输出限制；openEuler 上可叠加 cgroup v2 / Podman（`--network=none`）。
D 时延升高是子进程隔离的**真实代价**（消融 `D-noSandbox` 时延回落即证明），属安全/时延权衡，
可用常驻 worker 摊薄（未来工作）。

**Q7：为什么用 mock LLM？真实 LLM 下结论还成立吗？**
A：mock 保证可复现且 CI 无需密钥；机制带来的**相对收益方向**与 LLM 无关（引用替代全文、记忆复用避免重复推导）。
项目提供 OpenAI 兼容适配器，可切真实模型复测。

**Q8：如何保证在 openEuler 上能跑？**
A：纯软件、核心依赖均为通用 wheel；`scripts/` 用 dnf、隔离 venv、幂等；`verify_openeuler.sh`
输出 OS/内核/架构/依赖/cgroup/共享内存/Socket/沙箱/测试与 10 轮稳定性摘要；系统增强不可用自动降级。

**Q9：规模变大后向量检索会不会成为瓶颈？**
A：默认 numpy 暴力（小规模足够）；向量后端可插拔为 hnswlib/faiss（近似最近邻 O(log N)），
通过 `AGENT_VECTOR_BACKEND` 切换，缺依赖自动回退。

**Q10：故障下系统是否稳定？**
A：10 轮连续执行成功且 RSS 增长受控；故障注入测试覆盖 Agent 崩溃隔离、LLM 暂时失败恢复、
记忆库不可用降级、引用失效降级，运行时均不崩溃。
