"""CodeAct 执行器与沙箱（subprocess+rlimit；cgroup/namespace/Podman 可降级）。"""

from __future__ import annotations

from agent_runtime.sandbox.capabilities import select_backend
from agent_runtime.sandbox.capabilities import summary as capability_summary
from agent_runtime.sandbox.executor import CodeActExecutor
from agent_runtime.sandbox.result import ExecutionResult

__all__ = ["CodeActExecutor", "ExecutionResult", "select_backend", "capability_summary"]
