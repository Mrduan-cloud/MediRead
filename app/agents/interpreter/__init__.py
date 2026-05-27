"""医学解读 Agent — RAG + 多指标联合 + ReAct 推理 + 风险分级。

注: 顶层 attribute 走 PEP 562 lazy import,这样:
    from app.agents.interpreter import interpret_report     # 触发 react_chain 加载(及其 langchain / loguru 依赖)
    from app.agents.interpreter.risk_grading import grade_risk  # 仅加载 risk_grading,纯逻辑测试不必拉满栈

旧实现是顶层 ``from .react_chain import interpret_report``,导致即便只测
``risk_grading`` 的纯逻辑函数,也会被强制 import loguru / prometheus / langchain。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

__all__ = ["interpret_report"]

if TYPE_CHECKING:
    from app.agents.interpreter.react_chain import interpret_report


def __getattr__(name: str):
    if name == "interpret_report":
        from app.agents.interpreter.react_chain import (
            interpret_report as _f,
        )
        return _f
    raise AttributeError(f"module 'app.agents.interpreter' has no attribute {name!r}")
