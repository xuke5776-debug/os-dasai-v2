"""全局配置加载。

配置来源优先级（高→低）：
1. 显式传入的覆盖参数；
2. 环境变量（含 .env 文件，若存在）；
3. 代码内默认值。

设计为纯标准库实现（不依赖 python-dotenv），保证 openEuler 上零额外依赖即可工作。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

_ENV_LOADED = False


def _load_dotenv(path: str | os.PathLike[str] = ".env") -> None:
    """将 .env 文件中的键值对加载进 os.environ（不覆盖已存在的变量）。"""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    _ENV_LOADED = True
    p = Path(path)
    if not p.is_file():
        return
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _get(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


def _get_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class LLMConfig:
    provider: str = "mock"
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    temperature: float = 0.0
    max_tokens: int = 1024


@dataclass(frozen=True)
class EmbeddingConfig:
    provider: str = "mock"
    model: str = "all-MiniLM-L6-v2"
    dim: int = 256


@dataclass(frozen=True)
class SandboxConfig:
    backend: str = "subprocess"
    timeout_sec: int = 10
    mem_mb: int = 256
    cpu_sec: int = 8
    network: str = "disabled"


@dataclass(frozen=True)
class Config:
    """运行时全局配置（不可变）。"""

    llm: LLMConfig = field(default_factory=LLMConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    sandbox: SandboxConfig = field(default_factory=SandboxConfig)
    vector_backend: str = "numpy"
    state_shared_memory: bool = False
    random_seed: int = 42
    data_dir: str = ".agent_data"
    log_level: str = "INFO"
    log_format: str = "json"

    # ----- 派生路径 -----
    @property
    def artifact_dir(self) -> Path:
        return Path(self.data_dir) / "artifacts"

    @property
    def memory_dir(self) -> Path:
        return Path(self.data_dir) / "memory"

    @property
    def state_dir(self) -> Path:
        return Path(self.data_dir) / "state"

    def with_overrides(self, **overrides: Any) -> Config:
        """返回应用覆盖参数后的新配置实例。"""
        return replace(self, **overrides)


def load_config(load_env: bool = True, **overrides: Any) -> Config:
    """从环境变量构造配置，可选地先加载 .env，并应用显式覆盖。"""
    if load_env:
        _load_dotenv()

    cfg = Config(
        llm=LLMConfig(
            provider=_get("AGENT_LLM_PROVIDER", "mock"),
            api_key=_get("AGENT_LLM_API_KEY", ""),
            base_url=_get("AGENT_LLM_BASE_URL", "https://api.openai.com/v1"),
            model=_get("AGENT_LLM_MODEL", "gpt-4o-mini"),
            temperature=_get_float("AGENT_LLM_TEMPERATURE", 0.0),
            max_tokens=_get_int("AGENT_LLM_MAX_TOKENS", 1024),
        ),
        embedding=EmbeddingConfig(
            provider=_get("AGENT_EMBEDDING_PROVIDER", "mock"),
            model=_get("AGENT_EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
            dim=_get_int("AGENT_EMBEDDING_DIM", 256),
        ),
        sandbox=SandboxConfig(
            backend=_get("AGENT_SANDBOX_BACKEND", "subprocess"),
            timeout_sec=_get_int("AGENT_SANDBOX_TIMEOUT_SEC", 10),
            mem_mb=_get_int("AGENT_SANDBOX_MEM_MB", 256),
            cpu_sec=_get_int("AGENT_SANDBOX_CPU_SEC", 8),
            network=_get("AGENT_SANDBOX_NETWORK", "disabled"),
        ),
        vector_backend=_get("AGENT_VECTOR_BACKEND", "numpy"),
        state_shared_memory=_get("AGENT_STATE_SHM", "false").lower() in ("1", "true", "yes"),
        random_seed=_get_int("AGENT_RANDOM_SEED", 42),
        data_dir=_get("AGENT_DATA_DIR", ".agent_data"),
        log_level=_get("AGENT_LOG_LEVEL", "INFO"),
        log_format=_get("AGENT_LOG_FORMAT", "json"),
    )
    if overrides:
        cfg = cfg.with_overrides(**overrides)
    return cfg


__all__ = [
    "Config",
    "LLMConfig",
    "EmbeddingConfig",
    "SandboxConfig",
    "load_config",
]
