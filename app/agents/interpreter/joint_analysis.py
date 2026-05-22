"""多指标联合分析。

避免「单指标偏离一律打高风险」误判，按已知医学规则做联合判定。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class JointSignal:
    pattern: str                 # 例如 "liver_injury"
    matched_indicators: list[str]
    hint: str                    # 联合判定结论


# 简化版规则（生产可加载 YAML / 规则引擎）
JOINT_RULES: list[dict] = [
    {
        "pattern": "liver_injury",
        "require_all": ["丙氨酸氨基转移酶", "天门冬氨酸氨基转移酶", "γ-谷氨酰转移酶"],
        "hint": "ALT + AST + GGT 三项同步偏高，提示肝细胞 / 胆道系统受损可能。",
    },
    {
        "pattern": "dyslipidemia",
        "require_any": ["总胆固醇", "甘油三酯", "低密度脂蛋白胆固醇"],
        "hint": "血脂相关指标异常，提示血脂代谢紊乱倾向。",
    },
    {
        "pattern": "anemia",
        "require_all": ["血红蛋白", "红细胞计数"],
        "hint": "血红蛋白与红细胞计数同时偏低，提示贫血倾向。",
    },
]


def detect_joint_signals(abnormal_names: list[str]) -> list[JointSignal]:
    signals: list[JointSignal] = []
    name_set = set(abnormal_names)
    for rule in JOINT_RULES:
        if "require_all" in rule and set(rule["require_all"]).issubset(name_set):
            signals.append(JointSignal(rule["pattern"], rule["require_all"], rule["hint"]))
        elif "require_any" in rule and name_set & set(rule["require_any"]):
            matched = list(name_set & set(rule["require_any"]))
            signals.append(JointSignal(rule["pattern"], matched, rule["hint"]))
    return signals
