"""体检报告结构化字段 — Pydantic + JSONSchema 双层约束。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class Indicator(BaseModel):
    """6 类核心字段（贯穿整个 OCR → 抽取 → 解读链路）。"""

    name: str = Field(..., description="指标标准名（归一化后）")
    raw_name: str = Field(..., description="原始 OCR 识别到的指标名")
    value: float | str = Field(..., description="检验数值（少数项目为定性结果，如阴性 / 阳性）")
    unit: str | None = None
    ref_range: str | None = Field(None, description="参考范围，如 3.5–5.5")
    gender: str | None = None
    age: int | None = None
    abnormal: bool = False
    abnormal_direction: str | None = Field(None, description="high / low / abnormal")


class Report(BaseModel):
    """一次体检报告的结构化结果。"""

    report_id: str
    user_id: str
    source_object_key: str
    hospital: str | None = None
    sampled_at: str | None = None
    indicators: list[Indicator]
