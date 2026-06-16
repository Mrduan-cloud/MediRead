"""多指标联合分析单测（方向感知 + 扩充规则）。"""
from app.agents.interpreter.joint_analysis import (
    detect_joint_signals,
    normalize_direction,
)

# ---- 标准名常量(对齐 app/data/synonyms.json),避免散落字面量 ----
ALT, AST, GGT = "丙氨酸氨基转移酶", "天门冬氨酸氨基转移酶", "γ-谷氨酰转移酶"
HGB, RBC = "血红蛋白", "红细胞计数"
TC, TG, LDL = "总胆固醇", "甘油三酯", "低密度脂蛋白胆固醇"
CR, BUN = "肌酐", "尿素氮"
FPG, HBA1C = "空腹血糖", "糖化血红蛋白"


def _patterns(signals):
    return {s.pattern for s in signals}


# ============ 向后兼容:不传 directions 时不校验方向(历史行为) ============

def test_liver_triad():
    signals = detect_joint_signals([ALT, AST, GGT])
    assert "liver_injury" in _patterns(signals)


def test_anemia_pair():
    signals = detect_joint_signals([HGB, RBC])
    assert any(s.pattern == "anemia" for s in signals)


def test_dyslipidemia_any():
    signals = detect_joint_signals([TG])
    assert any(s.pattern == "dyslipidemia" for s in signals)


def test_unrelated_no_signal():
    signals = detect_joint_signals(["白细胞计数"])
    assert signals == []


# ============ normalize_direction ============

def test_normalize_direction_variants():
    assert normalize_direction("high") == "high"
    assert normalize_direction("HIGH") == "high"
    assert normalize_direction("偏高") == "high"
    assert normalize_direction("升高") == "high"
    assert normalize_direction("low") == "low"
    assert normalize_direction("偏低") == "low"
    assert normalize_direction(None) is None
    assert normalize_direction("") is None
    assert normalize_direction("abnormal") is None  # 方向未知


# ============ 方向感知:方向匹配才命中 ============

def test_liver_triad_all_high_fires():
    signals = detect_joint_signals(
        [ALT, AST, GGT],
        directions={ALT: "high", AST: "high", GGT: "high"},
    )
    assert "liver_injury" in _patterns(signals)


def test_liver_triad_wrong_direction_suppressed():
    # 其中一项方向相反(AST 偏低)→ 不符合「三项同步偏高」→ 不命中
    signals = detect_joint_signals(
        [ALT, AST, GGT],
        directions={ALT: "high", AST: "low", GGT: "high"},
    )
    assert "liver_injury" not in _patterns(signals)


def test_unknown_direction_suppressed_when_checking():
    # 提供了 directions 但方向未知(None)→ 保守不命中
    signals = detect_joint_signals(
        [ALT, AST, GGT],
        directions={ALT: "high", AST: None, GGT: "high"},
    )
    assert "liver_injury" not in _patterns(signals)


def test_anemia_requires_low():
    # 方向为高 → 不是贫血(可能是红细胞增多)
    high = detect_joint_signals([HGB, RBC], directions={HGB: "high", RBC: "high"})
    assert "anemia" not in _patterns(high)
    # 方向为低 → 命中贫血
    low = detect_joint_signals([HGB, RBC], directions={HGB: "low", RBC: "low"})
    assert "anemia" in _patterns(low)


def test_require_any_filters_by_direction():
    # 血脂三项里只有 TG 偏高、TC 偏低 → dyslipidemia 只应取方向匹配(TG)
    signals = detect_joint_signals([TC, TG], directions={TC: "low", TG: "high"})
    dys = next(s for s in signals if s.pattern == "dyslipidemia")
    assert dys.matched_indicators == [TG]


# ============ 新增规则 ============

def test_hypercholesterolemia():
    signals = detect_joint_signals([TC, LDL], directions={TC: "high", LDL: "high"})
    assert "hypercholesterolemia" in _patterns(signals)


def test_renal_impairment():
    signals = detect_joint_signals([CR, BUN], directions={CR: "high", BUN: "high"})
    s = next(s for s in signals if s.pattern == "renal_impairment")
    assert s.direction == "high"
    assert s.panel == "kidney_function_panel"


def test_dysglycemia_any():
    signals = detect_joint_signals([HBA1C], directions={HBA1C: "high"})
    assert "dysglycemia" in _patterns(signals)


def test_signal_carries_panel_and_direction():
    signals = detect_joint_signals([ALT, AST, GGT],
                                   directions={ALT: "high", AST: "high", GGT: "high"})
    liver = next(s for s in signals if s.pattern == "liver_injury")
    assert liver.panel == "liver_function_panel"
    assert liver.direction == "high"
    assert liver.hint  # 非空联合结论
