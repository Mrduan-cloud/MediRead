"""interpret_report 端到端 golden snapshot —— 确定性,进 CI。

monkeypatch 掉检索(_retrieve_kb_for)与 LLM(_llm_complete),用固定证据/回复跑完整
解读链路,把**确定性字段**(风险分级 / 就医分级 / 接地 / 重试步数 / 红线升级 / 引用)
钉成快照。覆盖三类行为:
  1. 接地 + 联合信号(肝三联)→ 一步收尾;
  2. 危急值兜底(甲胎蛋白)→ is_critical + 强制专科;
  3. 始终未接地(白细胞)→ 引用守卫驱动重试至 3 步 → grounded=False + 红线强制就医。
"""
from __future__ import annotations

import asyncio

from app.agents.interpreter import react_chain
from app.agents.parser.schemas import Indicator, Report

_EVIDENCE = [{"doc_id": "kb", "chunk_id": "1", "text": "示例医学证据片段。"}]


async def _fake_retrieve(query: str, top_k: int = 4) -> list[dict]:
    return list(_EVIDENCE)


async def _fake_llm(prompt: str, **kwargs) -> str:
    # 白细胞:故意不带任何引用 → 引用守卫判未接地 → 触发有界重试
    if "白细胞" in prompt:
        return ('{"interpretation": "白细胞偏高，提示可能存在炎症。", '
                '"lifestyle": "多休息、多饮水。", "triage_advice": "可观察随访。"}')
    # 其余:带合法引用 [kb:1] → 一步接地
    return ('{"interpretation": "该指标偏离，提示需关注 [kb:1]。", '
            '"lifestyle": "低脂低糖饮食、规律运动。", "triage_advice": "按建议就诊 [kb:1]。"}')


def _ind(name: str, value: float, ref: str) -> Indicator:
    return Indicator(name=name, raw_name=name, value=value, ref_range=ref,
                     abnormal=True, abnormal_direction="偏高")


def _report() -> Report:
    return Report(
        report_id="r1", user_id="u1", source_object_key="k",
        indicators=[
            _ind("丙氨酸氨基转移酶", 70.0, "9-50"),       # 肝三联之一,RECHECK,接地
            _ind("天门冬氨酸氨基转移酶", 60.0, "15-40"),
            _ind("γ-谷氨酰转移酶", 70.0, "10-50"),
            _ind("甲胎蛋白", 500.0, "0-8.78"),             # 危急值兜底
            _ind("白细胞计数", 11.0, "4-10"),               # MILD 但始终未接地 → 强制升级
        ],
    )


_GROUNDED = {"risk_level": "建议复查", "triage": "全科", "grounded": True,
             "react_steps": 1, "is_critical": False, "escalated": False, "citations": ["kb:1"]}

_EXPECTED = {
    "丙氨酸氨基转移酶": _GROUNDED,
    "天门冬氨酸氨基转移酶": _GROUNDED,
    "γ-谷氨酰转移酶": _GROUNDED,
    "甲胎蛋白": {"risk_level": "建议就医", "triage": "专科", "grounded": True,
             "react_steps": 1, "is_critical": True, "escalated": True, "citations": ["kb:1"]},
    "白细胞计数": {"risk_level": "轻度偏离", "triage": "专科", "grounded": False,
              "react_steps": 3, "is_critical": False, "escalated": True, "citations": []},
}


def test_interpret_report_golden(monkeypatch):
    monkeypatch.setattr(react_chain, "_retrieve_kb_for", _fake_retrieve)
    monkeypatch.setattr(react_chain, "_llm_complete", _fake_llm)

    result = asyncio.run(react_chain.interpret_report(_report()))

    # 联合信号:肝三联命中
    assert "liver_injury" in {s["pattern"] for s in result["joint_signals"]}

    proj = {
        it["indicator"]: {
            "risk_level": it["risk_level"], "triage": it["triage"],
            "grounded": it["grounded"], "react_steps": it["react_steps"],
            "is_critical": it["is_critical"], "escalated": it["escalated"],
            "citations": it["citations"],
        }
        for it in result["interpretations"]
    }
    assert proj == _EXPECTED


def test_ungrounded_gets_safe_degraded_text(monkeypatch):
    monkeypatch.setattr(react_chain, "_retrieve_kb_for", _fake_retrieve)
    monkeypatch.setattr(react_chain, "_llm_complete", _fake_llm)

    result = asyncio.run(react_chain.interpret_report(_report()))
    wbc = next(it for it in result["interpretations"] if it["indicator"] == "白细胞计数")
    # 未接地 → 不输出未核验的 LLM 原文,改安全降级文案 + 免责
    assert "依据" in wbc["interpretation"]
    assert wbc["disclaimer"]
    assert "炎症" not in wbc["interpretation"]      # LLM 原始解读未被当权威输出
