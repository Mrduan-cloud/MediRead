"""报告解析 Agent — OCR + 版式识别 + 6 字段抽取 + 归一化。

顶层 attribute 走 PEP 562 lazy import,纯逻辑测试(只 import normalizer / schemas)
不会拉到 paddleocr / pdf2image 等 OCR 重型依赖。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

__all__ = ["parse_report"]

if TYPE_CHECKING:
    from app.agents.parser.extractor import parse_report


def __getattr__(name: str):
    if name == "parse_report":
        from app.agents.parser.extractor import parse_report as _f
        return _f
    raise AttributeError(f"module 'app.agents.parser' has no attribute {name!r}")
