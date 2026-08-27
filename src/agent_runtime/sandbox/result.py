"""沙箱执行结果。"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ExecutionResult:
    """CodeAct 代码执行结果。"""

    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool
    duration_sec: float
    peak_rss_mb: float = 0.0
    truncated: bool = False
    backend: str = "subprocess"
    error: str | None = None
    artifact_refs: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and not self.timed_out and self.error is None

    def to_dict(self) -> dict:
        return {
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "timed_out": self.timed_out,
            "duration_sec": round(self.duration_sec, 4),
            "peak_rss_mb": round(self.peak_rss_mb, 3),
            "truncated": self.truncated,
            "backend": self.backend,
            "error": self.error,
            "artifact_refs": self.artifact_refs,
            "ok": self.ok,
        }


__all__ = ["ExecutionResult"]
