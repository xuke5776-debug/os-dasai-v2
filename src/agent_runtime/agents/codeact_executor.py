"""CodeAct Executor Agent：执行计划得到结果。

P1 直接进行确定性计算；P5 接入沙箱（LLM 生成 Python 代码并在受限环境执行）。
"""

from __future__ import annotations

from typing import Any

from agent_runtime.protocol.message import ActionType, AgentMessage, MessageStatus
from agent_runtime.runtime.agent import BaseAgent
from agent_runtime.runtime.context import RunContext
from agent_runtime.runtime.errors import ReferenceError_

_OPS = {
    "sum": lambda xs: sum(xs),
    "product": lambda xs: _product(xs),
    "max": lambda xs: max(xs),
    "min": lambda xs: min(xs),
    "mean": lambda xs: sum(xs) / len(xs) if xs else 0,
    "count": lambda xs: len(xs),
    "concat": lambda xs: "".join(str(x) for x in xs),
}


def _product(xs: list[Any]) -> Any:
    out: Any = 1
    for x in xs:
        out *= x
    return out


class CodeActExecutorAgent(BaseAgent):
    """根据 operation + evidence 计算结果。"""

    def __init__(self, **kwargs) -> None:
        super().__init__(
            name="executor",
            capabilities=["execute", "codeact", "compute"],
            actions=[ActionType.EXECUTE],
            **kwargs,
        )

    async def handle(self, message: AgentMessage, ctx: RunContext) -> AgentMessage:
        plan = message.input_parameters.get("plan")
        if plan is None:
            plan = self._resolve_plan(message, ctx)
        evidence = message.input_parameters.get("evidence")
        if evidence is None:
            evidence = self._resolve_evidence(message, ctx)
        plan = plan or {}
        evidence = evidence or {}
        operation = plan.get("operation", "noop")
        operands = plan.get("operands", [])

        if operation == "codefix":
            value: Any = await self._handle_codefix(evidence, ctx)
        else:
            value = await self._handle_arithmetic(operation, operands, evidence, ctx)

        ctx.blackboard["execution"] = value
        ctx.call_llm(
            f"Execute operation {operation} over {len(operands)} operands.",
            system="You are a careful code executor.",
        )

        status = MessageStatus.OK if value is not None else MessageStatus.ERROR
        return self.reply(
            message,
            ctx,
            action_type=ActionType.EXECUTE,
            capability="execute",
            result={"value": value},
            status=status,
            confidence=0.92,
        )

    async def _handle_arithmetic(
        self, operation: str, operands: list[Any], evidence: dict[str, Any], ctx: RunContext
    ) -> Any:
        values = [evidence.get(k) for k in operands]
        values = [v for v in values if v is not None]
        reused = ctx.blackboard.get("reused_answer")
        if reused is not None:
            value = reused  # 同一子问题：复用结论，跳过重复计算。
        elif ctx.sandbox is not None:
            value = await self._execute_in_sandbox(operation, values, ctx)
        else:
            ctx.record_tool(f"compute:{operation}:{operands}")
            value = self._compute(operation, values)
        ctx.blackboard["solution_used"] = value
        return value

    async def _handle_codefix(self, evidence: dict[str, Any], ctx: RunContext) -> bool:
        """应用修复/改造策略并在沙箱中验证（CodeAct）。

        策略来自证据，或复用共享记忆中的相似经验（reused_solution）。
        """
        from agent_runtime.agents.code_strategies import apply_strategy

        module = evidence.get("module")
        test = evidence.get("test")
        strategy = evidence.get("strategy") or ctx.blackboard.get("reused_solution")
        if not module or not test or not strategy:
            return False
        fixed = apply_strategy(strategy, module)
        if fixed is None:
            return False
        ctx.blackboard["solution_used"] = strategy
        program = fixed + "\n\n" + test
        if ctx.artifact_store is not None:
            ctx.artifact_store.put(fixed, summary="fixed module")
        if ctx.sandbox is not None:
            ctx.record_tool("sandbox:codefix")
            return ctx.sandbox.run(program).ok
        ctx.record_tool("local:codefix")
        return self._local_verify(program)

    @staticmethod
    def _local_verify(program: str) -> bool:
        """无沙箱时的回退验证：在独立命名空间执行（仅用于本项目受控代码）。"""
        try:
            ns: dict[str, Any] = {}
            exec(compile(program, "<codefix>", "exec"), ns)  # noqa: S102 - 受控测试代码
            return True
        except Exception:  # noqa: BLE001
            return False

    def _compute(self, operation: str, values: list[Any]) -> Any:
        fn = _OPS.get(operation)
        if fn is None:
            return None
        try:
            return fn(values)
        except Exception:  # noqa: BLE001
            return None

    async def _execute_in_sandbox(self, operation: str, values: list[Any], ctx: RunContext) -> Any:
        """生成 Python 代码并在沙箱中执行，解析结果；失败则降级本地计算。"""
        import json

        assert ctx.sandbox is not None
        code = self._codegen(operation, values)
        result = ctx.sandbox.run(code)
        ctx.record_tool(f"sandbox:{operation}")
        if ctx.artifact_store is not None and result.stdout:
            ctx.artifact_store.put(result.stdout, summary="codeact stdout")
        if not result.ok:
            ctx.metrics.record_degradation()
            return self._compute(operation, values)
        try:
            return json.loads(result.stdout.strip()).get("value")
        except (ValueError, AttributeError):
            ctx.metrics.record_degradation()
            return self._compute(operation, values)

    @staticmethod
    def _codegen(operation: str, values: list[Any]) -> str:
        """确定性地生成执行代码（mock 模式下代表 LLM 生成的 CodeAct 代码）。"""
        return (
            "import json\n"
            f"values = {values!r}\n"
            f"op = {operation!r}\n"
            "def product(xs):\n"
            "    r = 1\n"
            "    for x in xs:\n"
            "        r *= x\n"
            "    return r\n"
            "ops = {\n"
            "    'sum': sum, 'product': product, 'max': max, 'min': min,\n"
            "    'mean': lambda xs: sum(xs) / len(xs) if xs else 0,\n"
            "    'count': len, 'concat': lambda xs: ''.join(str(x) for x in xs),\n"
            "}\n"
            "fn = ops.get(op)\n"
            "print(json.dumps({'value': fn(values) if fn else None}))\n"
        )

    def _resolve_plan(self, message: AgentMessage, ctx: RunContext) -> dict[str, Any]:
        ref = message.input_parameters.get("plan_ref") or message.state_reference
        if not ref or ctx.state_exchange is None:
            return {}
        try:
            return dict(ctx.state_exchange.get_plan_state(ref)["dag"])
        except ReferenceError_:
            ctx.metrics.record_degradation()
            return {}

    def _resolve_evidence(self, message: AgentMessage, ctx: RunContext) -> dict[str, Any]:
        ref = message.input_parameters.get("evidence_ref")
        if not ref or ctx.artifact_store is None:
            return {}
        try:
            return ctx.artifact_store.get_json(ref)
        except ReferenceError_:
            ctx.metrics.record_degradation()
            return {}


__all__ = ["CodeActExecutorAgent"]
