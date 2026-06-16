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


async def _fake_llm_redline(prompt: str, **kwargs) -> str:
    # 引用接地(带 [kb:1]),但正文越界:确诊 + 用药
    return ('{"interpretation": "确诊为痛风，建议服用别嘌醇 100mg [kb:1]。", '
            '"lifestyle": "多饮水 [kb:1]。", "triage_advice": "见 [kb:1]。"}')


def test_red_line_in_interpretation_downgrades(monkeypatch):
    monkeypatch.setattr(react_chain, "_retrieve_kb_for", _fake_retrieve)
    monkeypatch.setattr(react_chain, "_llm_complete", _fake_llm_redline)

    report = Report(report_id="r2", user_id="u1", source_object_key="k",
                    indicators=[_ind("尿酸", 600.0, "150-420")])
    it = asyncio.run(react_chain.interpret_report(report))["interpretations"][0]
    # 引用虽接地,但正文越红线(确诊/用药)→ 降级:不输出越界原文、citations 清空、强制就医
    assert it["grounded"] is False
    assert it["citations"] == []
    assert "确诊" not in it["interpretation"] and "别嘌醇" not in it["interpretation"]
    assert it["escalated"] is True


async def _fake_retrieve_mixed(query: str, top_k: int = 4) -> list[dict]:
    # 一条好 chunk + 两条畸形(缺 ids / 缺 text)
    return [
        {"doc_id": "kb", "chunk_id": "1", "text": "ok"},
        {"doc_id": "bad"},          # 缺 chunk_id
        {"text": "no ids"},          # 缺 doc_id/chunk_id
    ]


def test_malformed_chunks_skipped_not_aborted(monkeypatch):
    monkeypatch.setattr(react_chain, "_retrieve_kb_for", _fake_retrieve_mixed)
    monkeypatch.setattr(react_chain, "_llm_complete", _fake_llm)  # 引用 [kb:1]

    report = Report(report_id="r3", user_id="u1", source_object_key="k",
                    indicators=[_ind("γ-谷氨酰转移酶", 70.0, "10-50")])
    it = asyncio.run(react_chain.interpret_report(report))["interpretations"][0]
    # 畸形 chunk 被跳过,好 chunk 仍可接地;不因坏数据落 except
    assert "error" not in it
    assert it["grounded"] is True
    assert it["citations"] == ["kb:1"]


def test_ungrounded_gets_safe_degraded_text(monkeypatch):
    monkeypatch.setattr(react_chain, "_retrieve_kb_for", _fake_retrieve)
    monkeypatch.setattr(react_chain, "_llm_complete", _fake_llm)

    result = asyncio.run(react_chain.interpret_report(_report()))
    wbc = next(it for it in result["interpretations"] if it["indicator"] == "白细胞计数")
    # 未接地 → 不输出未核验的 LLM 原文,改安全降级文案 + 免责
    assert "依据" in wbc["interpretation"]
    assert wbc["disclaimer"]
    assert "炎症" not in wbc["interpretation"]      # LLM 原始解读未被当权威输出


def test_joint_hints_surface_per_indicator(monkeypatch):
    monkeypatch.setattr(react_chain, "_retrieve_kb_for", _fake_retrieve)
    monkeypatch.setattr(react_chain, "_llm_complete", _fake_llm)

    result = asyncio.run(react_chain.interpret_report(_report()))
    by_name = {it["indicator"]: it for it in result["interpretations"]}
    # 肝三联三项("偏高"经归一化为 high)都应带上肝损伤联合结论 hint
    for name in ("丙氨酸氨基转移酶", "天门冬氨酸氨基转移酶", "γ-谷氨酰转移酶"):
        hints = by_name[name]["joint_hints"]
        assert hints and any("肝细胞" in h for h in hints)
    # 未参与任何联合的白细胞:字段存在但为空(形状一致,不 KeyError)
    assert by_name["白细胞计数"]["joint_hints"] == []
