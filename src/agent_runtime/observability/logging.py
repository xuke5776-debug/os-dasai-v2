"""结构化日志。

每条日志可携带 trace_id / task_id 等上下文字段，支持 JSON 与文本两种格式。
默认输出到 stderr，避免污染 stdout（stdout 可能用于 Demo/数据流）。
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

_CONFIGURED = False

# 标准 LogRecord 自带属性，用于在格式化时筛出自定义 extra 字段。
_RESERVED = set(logging.makeLogRecord({}).__dict__.keys()) | {"message", "asctime", "taskName"}


class JsonFormatter(logging.Formatter):
    """将日志记录格式化为单行 JSON。"""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


class TextFormatter(logging.Formatter):
    """人类可读文本格式，附加自定义上下文字段。"""

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        extras = {
            k: v for k, v in record.__dict__.items() if k not in _RESERVED and not k.startswith("_")
        }
        if extras:
            ctx = " ".join(f"{k}={v}" for k, v in extras.items())
            return f"{base} | {ctx}"
        return base


def setup_logging(level: str = "INFO", fmt: str = "json") -> None:
    """配置根 logger（幂等）。"""
    global _CONFIGURED
    handler = logging.StreamHandler(sys.stderr)
    if fmt == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(TextFormatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))

    root = logging.getLogger("agent_runtime")
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.propagate = False
    _CONFIGURED = True


def get_logger(name: str, **context: Any) -> logging.LoggerAdapter:
    """获取带默认上下文（如 trace_id/task_id）的 logger 适配器。"""
    if not _CONFIGURED:
        setup_logging()
    logger = logging.getLogger(f"agent_runtime.{name}")
    return logging.LoggerAdapter(logger, context)


__all__ = ["setup_logging", "get_logger", "JsonFormatter", "TextFormatter"]
