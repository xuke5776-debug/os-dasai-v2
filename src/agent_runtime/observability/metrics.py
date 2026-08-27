"""指标采集。

集中采集赛题要求的 16 项指标及派生指标。一个 `MetricsCollector` 对应一次
任务运行（或一次实验重复），可序列化为 dict 落盘。
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any

try:  # psutil 为核心依赖，但保留降级以增强健壮性
    import psutil

    _PROC = psutil.Process()
except Exception:  # noqa: BLE001
    psutil = None  # type: ignore[assignment]
    _PROC = None


@dataclass
class MetricsSnapshot:
    """单次运行的指标快照。"""

    # 1. Agent 消息次数
    message_count: int = 0
    # 2. 文本 token / 字符
    text_tokens: int = 0
    text_chars: int = 0
    # 3. 非文本状态次数与字节
    state_transfers: int = 0
    state_bytes: int = 0
    # 4. Artifact 引用次数
    artifact_refs: int = 0
    # 5. 端到端耗时（秒）
    latency_sec: float = 0.0
    # 7. LLM 调用次数 / token
    llm_calls: int = 0
    llm_prompt_tokens: int = 0
    llm_completion_tokens: int = 0
    # 8. 工具调用与重复调用
    tool_calls: int = 0
    repeated_tool_calls: int = 0
    # 9/10. 记忆命中
    memory_retrieved: int = 0
    memory_used: int = 0
    memory_effective: int = 0
    memory_harmful: int = 0
    # 11/12. 成功率 / 质量
    task_success: bool = False
    task_quality: float = 0.0
    # 13/14. 资源
    cpu_percent: float = 0.0
    rss_peak_mb: float = 0.0
    # 16. 错误 / 降级
    error_count: int = 0
    degradation_count: int = 0

    # 附加：每步延迟样本（用于 P50/P95）
    step_latencies: list[float] = field(default_factory=list)
    # 工具调用签名计数（用于识别重复计算）
    _tool_signatures: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("_tool_signatures", None)
        d["derived"] = {
            "memory_hit_rate": self._safe_div(self.memory_retrieved, max(self.message_count, 1)),
            "effective_hit_rate": self._safe_div(self.memory_effective, self.memory_used),
            "total_llm_tokens": self.llm_prompt_tokens + self.llm_completion_tokens,
        }
        return d

    @staticmethod
    def _safe_div(a: float, b: float) -> float:
        return float(a) / float(b) if b else 0.0


class MetricsCollector:
    """指标采集器：贯穿一次任务运行，由各模块写入。"""

    def __init__(self) -> None:
        self.snapshot = MetricsSnapshot()
        self._start: float | None = None

    # ----- 计时 -----
    def start(self) -> None:
        self._start = time.perf_counter()
        self._sample_resources()

    def stop(self) -> None:
        if self._start is not None:
            self.snapshot.latency_sec = time.perf_counter() - self._start
        self._sample_resources()

    def record_step_latency(self, seconds: float) -> None:
        self.snapshot.step_latencies.append(seconds)

    # ----- 通信 -----
    def record_message(self, *, tokens: int = 0, chars: int = 0) -> None:
        self.snapshot.message_count += 1
        self.snapshot.text_tokens += tokens
        self.snapshot.text_chars += chars

    def record_state_transfer(self, n_bytes: int) -> None:
        self.snapshot.state_transfers += 1
        self.snapshot.state_bytes += n_bytes

    def record_artifact_ref(self, n: int = 1) -> None:
        self.snapshot.artifact_refs += n

    # ----- 模型 / 工具 -----
    def record_llm(self, prompt_tokens: int, completion_tokens: int) -> None:
        self.snapshot.llm_calls += 1
        self.snapshot.llm_prompt_tokens += prompt_tokens
        self.snapshot.llm_completion_tokens += completion_tokens

    def record_tool_call(self, signature: str) -> None:
        self.snapshot.tool_calls += 1
        prev = self.snapshot._tool_signatures.get(signature, 0)
        if prev > 0:
            self.snapshot.repeated_tool_calls += 1
        self.snapshot._tool_signatures[signature] = prev + 1

    # ----- 记忆 -----
    def record_memory(
        self,
        *,
        retrieved: int = 0,
        used: int = 0,
        effective: int = 0,
        harmful: int = 0,
    ) -> None:
        self.snapshot.memory_retrieved += retrieved
        self.snapshot.memory_used += used
        self.snapshot.memory_effective += effective
        self.snapshot.memory_harmful += harmful

    # ----- 结果 -----
    def set_result(self, success: bool, quality: float) -> None:
        self.snapshot.task_success = success
        self.snapshot.task_quality = quality

    def record_error(self) -> None:
        self.snapshot.error_count += 1

    def record_degradation(self) -> None:
        self.snapshot.degradation_count += 1

    # ----- 资源 -----
    def _sample_resources(self) -> None:
        if _PROC is None:
            return
        try:
            rss_mb = _PROC.memory_info().rss / (1024 * 1024)
            self.snapshot.rss_peak_mb = max(self.snapshot.rss_peak_mb, rss_mb)
            self.snapshot.cpu_percent = _PROC.cpu_percent(interval=None)
        except Exception:  # noqa: BLE001
            pass

    def sample_resources(self) -> None:
        """对外暴露的资源采样（可在长任务中周期调用）。"""
        self._sample_resources()


__all__ = ["MetricsCollector", "MetricsSnapshot"]
