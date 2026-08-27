"""Token / 字符计数。

用于公平地度量两种协作模式的通信开销。默认使用确定性启发式分词器
（与具体模型无关，但在所有模式下一致，因此对比有意义）；若安装了 tiktoken，
可切换到更接近真实模型的计数。
"""

from __future__ import annotations

import math
from typing import Protocol


class Tokenizer(Protocol):
    name: str

    def count(self, text: str) -> int:
        """返回文本的 token 数。"""
        ...


class HeuristicTokenizer:
    """确定性启发式分词器（BPE 近似）。

    采用业界常用的近似：非 CJK 文本约每 4 个字符 ≈ 1 个 token（含空白与标点），
    CJK 字符按单字 ≈ 1 token。该口径与真实 BPE 分词器（如 tiktoken）的规模高度
    相关，且不会像「逐标点切词」那样高估 JSON 等结构化文本的 token 数，从而保证
    text/structured 双模式对比的公平性。需要更精确计数时可启用 tiktoken。
    """

    name = "heuristic"
    _CHARS_PER_TOKEN = 4

    def count(self, text: str) -> int:
        if not text:
            return 0
        cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
        non_cjk_chars = len(text) - cjk
        non_cjk_tokens = math.ceil(non_cjk_chars / self._CHARS_PER_TOKEN) if non_cjk_chars else 0
        return cjk + non_cjk_tokens


class TiktokenTokenizer:
    """基于 tiktoken 的分词器（可选，更接近真实模型计数）。"""

    name = "tiktoken"

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        import tiktoken  # 延迟导入

        try:
            self._enc = tiktoken.encoding_for_model(model)
        except KeyError:
            self._enc = tiktoken.get_encoding("cl100k_base")

    def count(self, text: str) -> int:
        if not text:
            return 0
        return len(self._enc.encode(text))


def get_tokenizer(prefer_tiktoken: bool = False, model: str = "gpt-4o-mini") -> Tokenizer:
    """返回一个分词器实例；tiktoken 不可用时回退到启发式分词器。"""
    if prefer_tiktoken:
        try:
            return TiktokenTokenizer(model)
        except Exception:  # noqa: BLE001 - 任何导入/加载失败都回退
            pass
    return HeuristicTokenizer()


def count_chars(text: str) -> int:
    """字符数（与 token 数互补的通信开销度量）。"""
    return len(text or "")


__all__ = [
    "Tokenizer",
    "HeuristicTokenizer",
    "TiktokenTokenizer",
    "get_tokenizer",
    "count_chars",
]
