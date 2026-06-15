"""medical_advice 单测 —— 确定性临床红线层,纯逻辑进 CI。"""
import pytest

from app.agents.interpreter.medical_advice import (
    DISCLAIMER,
    build_advice,
    lifestyle_advice,
    triage_phrase,
    violates_red_line,
)
from app.agents.interpreter.risk_grading import IndicatorRisk, RiskLevel, TriageLevel


def _risk(level: RiskLevel, triage: TriageLevel, *, critical: bool = False, name: str = "甘油三酯") -> IndicatorRisk:
    return IndicatorRisk(indicator=name, value=2.5, deviation_pct=0.4,
                         risk_level=level, triage=triage, is_critical=critical)


# ---------- violates_red_line ----------
@pytest.mark.parametrize("text", [
    "每日服用阿托伐他汀 20mg",
    "建议口服二甲双胍 500mg",
    "确诊为 2 型糖尿病",
    "诊断为脂肪肝",
    "每次 2 片，每日三次",
])
def test_red_line_catches_medication_and_diagnosis(text):
    assert violates_red_line(text) is True


@pytest.mark.parametrize("text", [
    "低脂低糖饮食、增加有氧运动、控制体重。",
    "限酒、规律作息、清淡饮食。",
    "",
])
def test_red_line_passes_safe_lifestyle(text):
    assert violates_red_line(text) is False


# ---------- triage_phrase / lifestyle_advice ----------
def test_triage_phrase_covers_all_levels():
    for lvl in TriageLevel:
        assert triage_phrase(lvl)


def test_lifestyle_joint_pattern_takes_priority():
    # 即便指标关键词命中血脂,联合信号 liver_injury 优先
    adv = lifestyle_advice("甘油三酯", ["liver_injury"])
    assert "肝" in adv or "酒" in adv


def test_lifestyle_keyword_and_default():
    assert "血糖" in lifestyle_advice("空腹血糖", [])
    assert "肾" in lifestyle_advice("血肌酐", [])
    assert lifestyle_advice("某未知指标", []) == lifestyle_advice("另一未知", None)  # 都落默认


# ---------- build_advice ----------
def test_build_advice_normal_keeps_safe_llm_lifestyle():
    adv = build_advice(_risk(RiskLevel.WATCH, TriageLevel.GENERAL),
                       joint_patterns=[], grounded=True,
                       llm_lifestyle="低脂饮食、规律运动。")
    assert adv["triage"] == TriageLevel.GENERAL.value
    assert adv["escalated"] is False
    assert adv["lifestyle"] == "低脂饮食、规律运动。"
    assert adv["disclaimer"] == DISCLAIMER


def test_build_advice_critical_escalates_to_at_least_specialist():
    adv = build_advice(_risk(RiskLevel.SEEK_CARE, TriageLevel.GENERAL, critical=True),
                       grounded=True)
    assert adv["escalated"] is True
    assert adv["triage"] in (TriageLevel.SPECIALIST.value, TriageLevel.EMERGENCY.value)


def test_build_advice_seek_care_escalates():
    adv = build_advice(_risk(RiskLevel.SEEK_CARE, TriageLevel.GENERAL), grounded=True)
    assert adv["escalated"] is True


def test_build_advice_ungrounded_forces_seek_care_and_drops_llm():
    adv = build_advice(_risk(RiskLevel.WATCH, TriageLevel.GENERAL),
                       grounded=False, llm_lifestyle="低脂饮食。")
    assert adv["escalated"] is True
    assert "依据" in adv["triage_advice"]              # 说明因未接地而建议就医
    assert adv["lifestyle"] != "低脂饮食。"             # 未接地 → 弃用 LLM 文本


def test_build_advice_drops_llm_lifestyle_violating_red_line():
    adv = build_advice(_risk(RiskLevel.WATCH, TriageLevel.GENERAL),
                       grounded=True, llm_lifestyle="建议口服二甲双胍 500mg。")
    assert "二甲双胍" not in adv["lifestyle"]           # 越红线 → 改确定性安全建议
