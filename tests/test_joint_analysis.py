"""多指标联合分析单测。"""
from app.agents.interpreter.joint_analysis import detect_joint_signals


def test_liver_triad():
    signals = detect_joint_signals([
        "丙氨酸氨基转移酶", "天门冬氨酸氨基转移酶", "γ-谷氨酰转移酶",
    ])
    patterns = {s.pattern for s in signals}
    assert "liver_injury" in patterns


def test_anemia_pair():
    signals = detect_joint_signals(["血红蛋白", "红细胞计数"])
    assert any(s.pattern == "anemia" for s in signals)


def test_dyslipidemia_any():
    signals = detect_joint_signals(["甘油三酯"])
    assert any(s.pattern == "dyslipidemia" for s in signals)


def test_unrelated_no_signal():
    signals = detect_joint_signals(["白细胞计数"])
    assert signals == []
