"""风险分级 + 就医分级。

四级风险：轻度偏离 / 关注观察 / 建议复查 / 建议就医
就医分级：无需 / 全科 / 专科 / 急诊
"""
from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel

from app.agents.parser.normalizer import parse_ref_range


class RiskLevel(StrEnum):
    MILD = "轻度偏离"
    WATCH = "关注观察"
    RECHECK = "建议复查"
    SEEK_CARE = "建议就医"


class TriageLevel(StrEnum):
    NONE = "无需"
    GENERAL = "全科"
    SPECIALIST = "专科"
    EMERGENCY = "急诊"


class IndicatorRisk(BaseModel):
    indicator: str
    value: float | str
    deviation_pct: float | None
    risk_level: RiskLevel
    triage: TriageLevel
    is_critical: bool = False


CRITICAL_INDICATORS = {
    # 肿瘤标志物显著升高 → 急诊
    "甲胎蛋白": 200.0,
    "癌胚抗原": 20.0,
    "糖类抗原 19-9": 100.0,
    "糖类抗原 125": 200.0,
}


def _deviation(value: float, ref_range: str | None) -> float | None:
    low, high = parse_ref_range(ref_range)
    if isinstance(value, (int, float)):
        if high is not None and value > high:
            return (value - high) / high
        if low is not None and value < low:
            return (low - value) / max(low, 1e-9)
    return None


def grade_risk(indicator: str, value: float | str, ref_range: str | None) -> IndicatorRisk:
    """根据偏离幅度 + 危急值表给出分级。"""
    # 危急值兜底
    threshold = CRITICAL_INDICATORS.get(indicator)
    if threshold and isinstance(value, (int, float)) and value >= threshold:
        return IndicatorRisk(
            indicator=indicator,
            value=value,
            deviation_pct=None,
            risk_level=RiskLevel.SEEK_CARE,
            triage=TriageLevel.SPECIALIST,
            is_critical=True,
        )

    if not isinstance(value, (int, float)):
        return IndicatorRisk(
            indicator=indicator, value=value, deviation_pct=None,
            risk_level=RiskLevel.WATCH, triage=TriageLevel.GENERAL,
        )

    dev = _deviation(value, ref_range) or 0.0
    # 边界包含:恰好 ±10% 视为温和偏离(医学场景的"略高于正常上限"通常归为 MILD,
    # 而不是触发观察。test_risk_grading.py::test_mild 锁定此契约。)
    if dev <= 0.1:
        return IndicatorRisk(indicator=indicator, value=value, deviation_pct=dev,
                             risk_level=RiskLevel.MILD, triage=TriageLevel.NONE)
    if dev < 0.3:
        return IndicatorRisk(indicator=indicator, value=value, deviation_pct=dev,
                             risk_level=RiskLevel.WATCH, triage=TriageLevel.GENERAL)
    if dev < 0.6:
        return IndicatorRisk(indicator=indicator, value=value, deviation_pct=dev,
                             risk_level=RiskLevel.RECHECK, triage=TriageLevel.GENERAL)
    return IndicatorRisk(indicator=indicator, value=value, deviation_pct=dev,
                         risk_level=RiskLevel.SEEK_CARE, triage=TriageLevel.SPECIALIST)
