"""风险分级单测样例。"""
from app.agents.interpreter.risk_grading import grade_risk, RiskLevel, TriageLevel


def test_mild():
    r = grade_risk("γ-谷氨酰转移酶", 55.0, "10-50")
    assert r.risk_level == RiskLevel.MILD


def test_seek_care():
    r = grade_risk("γ-谷氨酰转移酶", 200.0, "10-50")
    assert r.risk_level == RiskLevel.SEEK_CARE
    assert r.triage == TriageLevel.SPECIALIST


def test_critical_tumor_marker():
    r = grade_risk("甲胎蛋白", 500.0, "0-8.78")
    assert r.is_critical is True
    assert r.risk_level == RiskLevel.SEEK_CARE
