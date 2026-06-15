"""风险分级单测样例。"""
from app.agents.interpreter.risk_grading import RiskLevel, TriageLevel, grade_risk


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


# ---- 补强:四档边界 + 低侧偏离 + 非数值 + 无参考范围 ----

def test_watch_band():
    # dev=(60-50)/50=0.2 ∈ (0.1, 0.3) → 关注观察 / 全科
    r = grade_risk("γ-谷氨酰转移酶", 60.0, "10-50")
    assert r.risk_level == RiskLevel.WATCH
    assert r.triage == TriageLevel.GENERAL


def test_recheck_band():
    # dev=(70-50)/50=0.4 ∈ [0.3, 0.6) → 建议复查 / 全科
    r = grade_risk("γ-谷氨酰转移酶", 70.0, "10-50")
    assert r.risk_level == RiskLevel.RECHECK
    assert r.triage == TriageLevel.GENERAL


def test_seek_care_boundary_at_0_6():
    # dev=(80-50)/50=0.6 恰好 → 不 < 0.6 → 建议就医 / 专科
    r = grade_risk("γ-谷氨酰转移酶", 80.0, "10-50")
    assert r.risk_level == RiskLevel.SEEK_CARE
    assert r.triage == TriageLevel.SPECIALIST


def test_low_side_deviation_uses_lower_bound():
    # 低于下限:dev=(10-8)/10=0.2 → 关注观察
    r = grade_risk("血红蛋白", 8.0, "10-50")
    assert r.risk_level == RiskLevel.WATCH
    assert r.deviation_pct is not None and round(r.deviation_pct, 2) == 0.2


def test_non_numeric_value_defaults_to_watch():
    r = grade_risk("尿蛋白", "阳性", "阴性")
    assert r.risk_level == RiskLevel.WATCH
    assert r.triage == TriageLevel.GENERAL
    assert r.deviation_pct is None


def test_missing_ref_range_is_mild():
    # 无参考范围无法判偏离幅度 → dev 视为 0 → 轻度偏离 / 无需就医(保守不夸大)
    r = grade_risk("某指标", 100.0, None)
    assert r.risk_level == RiskLevel.MILD
    assert r.triage == TriageLevel.NONE
