"""CodeAct 执行器与沙箱。

让 LLM 生成的 Python 代码在受限环境中执行并回传 stdout / stderr / exit code /
资源占用 / artifact 引用。隔离手段（按可用性自动降级）：

- subprocess + timeout（基础，跨平台）；
- `resource.setrlimit`：CPU / 内存(AS) / 文件大小 / 打开文件 / 进程数（POSIX）；
- 独立工作目录（tempdir）+ 隔离环境变量白名单 + Python `-I` 隔离模式；
- 独立进程组 + 超时强制清理，避免残留进程；
- 输出大小限制；
- openEuler 上可选 Podman（`--network=none`）作为更强隔离，缺失自动降级。
"""

from __future__ import annotations

import contextlib
import os
import subprocess
import sys
import tempfile
import time

from agent_runtime.config import SandboxConfig
from agent_runtime.sandbox.capabilities import has_rlimit, select_backend
from agent_runtime.sandbox.result import ExecutionResult

_MAX_OUTPUT_BYTES = 64 * 1024


def _make_preexec(cfg: SandboxConfig):
    """构造 POSIX 子进程的资源限制函数。"""
    if not has_rlimit():
        return None

    import resource

    def _set_limits() -> None:  # 在子进程中执行
        limits = [
            (resource.RLIMIT_CPU, (cfg.cpu_sec, cfg.cpu_sec + 1)),
            (resource.RLIMIT_AS, (cfg.mem_mb * 1024 * 1024, cfg.mem_mb * 1024 * 1024)),
            (resource.RLIMIT_FSIZE, (16 * 1024 * 1024, 16 * 1024 * 1024)),
            (resource.RLIMIT_NOFILE, (64, 64)),
        ]
        for res, (soft, hard) in limits:
            with contextlib.suppress(ValueError, OSError):
                resource.setrlimit(res, (soft, hard))
        # 进程数限制（部分平台可能不支持，失败则忽略）。
        with contextlib.suppress(ValueError, OSError, AttributeError):
            resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))
        with contextlib.suppress(OSError):
            os.setsid()

    return _set_limits


def _safe_env(cfg: SandboxConfig) -> dict[str, str]:
    """环境变量白名单。"""
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "AGENT_SANDBOX": "1",
    }
    if cfg.network == "disabled":
        # 最佳努力：清除代理并标记；强网络隔离依赖 namespace / Podman。
        env["NO_PROXY"] = "*"
        env["AGENT_SANDBOX_NETWORK"] = "disabled"
    return env


def _peak_rss_delta_mb(before: int) -> float:
    if not has_rlimit():
        return 0.0
    import resource

    after = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    delta = max(0, after - before)
    # Linux: ru_maxrss 单位 KB；macOS: 单位 bytes。
    if sys.platform == "darwin":
        return delta / (1024 * 1024)
    return delta / 1024


class CodeActExecutor:
    """在受限环境执行 Python 代码。"""

    def __init__(self, config: SandboxConfig | None = None) -> None:
        self.config = config or SandboxConfig()
        self.backend = select_backend(self.config.backend)
        self.degraded = self.backend != (self.config.backend or "subprocess").lower()

    def run(self, code: str, *, stdin: str = "") -> ExecutionResult:
        """执行代码并返回结果。"""
        if self.backend == "podman":
            try:
                return self._run_podman(code, stdin)
            except Exception:  # noqa: BLE001 - Podman 失败降级 subprocess
                self.degraded = True
                self.backend = "subprocess"
        return self._run_subprocess(code, stdin)

    # ------------------------------------------------------------------ 子进程
    def _run_subprocess(self, code: str, stdin: str) -> ExecutionResult:
        workdir = tempfile.mkdtemp(prefix="codeact_")
        script = os.path.join(workdir, "main.py")
        with open(script, "w", encoding="utf-8") as f:
            f.write(code)

        before_rss = 0
        if has_rlimit():
            import resource

            before_rss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss

        popen_kwargs: dict = {
            "cwd": workdir,
            "env": _safe_env(self.config),
            "stdin": subprocess.PIPE,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "text": True,
        }
        preexec = _make_preexec(self.config)
        if preexec is not None:
            popen_kwargs["preexec_fn"] = preexec
        if os.name == "nt":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]

        start = time.perf_counter()
        timed_out = False
        error: str | None = None
        try:
            proc = subprocess.Popen(  # noqa: S603 - 受控执行：隔离 + 限制
                [sys.executable, "-I", "main.py"], **popen_kwargs
            )
            try:
                out, err = proc.communicate(input=stdin, timeout=self.config.timeout_sec)
            except subprocess.TimeoutExpired:
                timed_out = True
                self._kill(proc)
                out, err = proc.communicate()
            exit_code = proc.returncode if proc.returncode is not None else -1
        except Exception as exc:  # noqa: BLE001
            out, err, exit_code, error = "", "", -1, f"{type(exc).__name__}: {exc}"
        finally:
            self._cleanup_dir(workdir)

        duration = time.perf_counter() - start
        out, truncated_o = self._truncate(out)
        err, truncated_e = self._truncate(err)
        return ExecutionResult(
            stdout=out,
            stderr=err,
            exit_code=exit_code,
            timed_out=timed_out,
            duration_sec=duration,
            peak_rss_mb=_peak_rss_delta_mb(before_rss),
            truncated=truncated_o or truncated_e,
            backend="subprocess",
            error=error,
        )

    # ------------------------------------------------------------------ Podman
    def _run_podman(self, code: str, stdin: str) -> ExecutionResult:
        start = time.perf_counter()
        cmd = [
            "podman",
            "run",
            "--rm",
            "-i",
            "--network=none",
            f"--memory={self.config.mem_mb}m",
            "--pids-limit=64",
            "python:3.11-slim",
            "python",
            "-I",
            "-",
        ]
        timed_out = False
        error: str | None = None
        try:
            proc = subprocess.Popen(  # noqa: S603
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                out, err = proc.communicate(input=code, timeout=self.config.timeout_sec)
            except subprocess.TimeoutExpired:
                timed_out = True
                proc.kill()
                out, err = proc.communicate()
            exit_code = proc.returncode if proc.returncode is not None else -1
        except Exception as exc:  # noqa: BLE001
            out, err, exit_code, error = "", "", -1, f"{type(exc).__name__}: {exc}"

        duration = time.perf_counter() - start
        out, to = self._truncate(out)
        err, te = self._truncate(err)
        return ExecutionResult(
            stdout=out,
            stderr=err,
            exit_code=exit_code,
            timed_out=timed_out,
            duration_sec=duration,
            truncated=to or te,
            backend="podman",
            error=error,
        )

    # ------------------------------------------------------------------ 工具
    @staticmethod
    def _truncate(text: str) -> tuple[str, bool]:
        data = (text or "").encode("utf-8")
        if len(data) <= _MAX_OUTPUT_BYTES:
            return text or "", False
        return data[:_MAX_OUTPUT_BYTES].decode("utf-8", errors="ignore") + "\n…[truncated]", True

    @staticmethod
    def _kill(proc: subprocess.Popen) -> None:
        try:
            if os.name == "posix":
                os.killpg(os.getpgid(proc.pid), 9)
            else:
                proc.kill()
        except (ProcessLookupError, OSError):
            pass

    @staticmethod
    def _cleanup_dir(path: str) -> None:
        import shutil

        shutil.rmtree(path, ignore_errors=True)


__all__ = ["CodeActExecutor"]
