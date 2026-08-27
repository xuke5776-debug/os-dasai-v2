"""CodeAct 沙箱单元测试。"""

from __future__ import annotations

import asyncio

from scenarios.demo import make_demo_task

from agent_runtime.config import SandboxConfig, load_config
from agent_runtime.runtime.builder import build_context, build_default_agents
from agent_runtime.runtime.orchestrator import Orchestrator
from agent_runtime.sandbox.capabilities import summary
from agent_runtime.sandbox.executor import CodeActExecutor


def test_basic_execution_returns_stdout():
    ex = CodeActExecutor(SandboxConfig(timeout_sec=10))
    result = ex.run("print('hello sandbox')")
    assert result.ok
    assert "hello sandbox" in result.stdout
    assert result.exit_code == 0


def test_nonzero_exit_captured():
    ex = CodeActExecutor(SandboxConfig(timeout_sec=10))
    result = ex.run("import sys; sys.stderr.write('boom'); sys.exit(3)")
    assert result.exit_code == 3
    assert "boom" in result.stderr
    assert not result.ok


def test_timeout_is_enforced():
    ex = CodeActExecutor(SandboxConfig(timeout_sec=1))
    result = ex.run("import time; time.sleep(5)")
    assert result.timed_out is True
    assert not result.ok


def test_output_truncation():
    ex = CodeActExecutor(SandboxConfig(timeout_sec=10))
    result = ex.run("print('x' * (200 * 1024))")
    assert result.truncated is True


def test_capability_summary_keys():
    s = summary()
    for key in ["rlimit", "cgroup_v2", "shared_memory", "unix_socket", "podman"]:
        assert key in s


def test_codeact_in_full_pipeline():
    config = load_config(load_env=False)
    ctx = build_context(config, "structured", task_id="t", use_sandbox=True)
    orch = Orchestrator(build_default_agents(config))
    result = asyncio.run(orch.run_task(make_demo_task(), ctx))
    assert result.success is True
    assert result.outputs["answer"] == 12
    # 通过沙箱执行：记录了 sandbox 工具调用
    assert any(sig.startswith("sandbox:") for sig in ctx.metrics.snapshot._tool_signatures)
