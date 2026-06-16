"""医学解读主链:接地驱动的有界重试(ReAct, max 3 步)。

每个异常指标走一个**有界重试**循环,由引用守卫(citation_guard)当停止条件:

    检索证据 → LLM 生成解读 → 引用守卫判定是否「真的接地」
        ├─ 接地 → 收尾
        └─ 未接地 → 放宽检索(扩窗 + 带方向/联合信号),累积证据,重试(至多 3 步)

这就是「ReAct」在本场景的克制落地:loop 由守卫反馈驱动,而非让 LLM 自由多步漫游。
三步仍未接地 → 不把未经核验的解读当权威输出,改走 medical_advice 的确定性安全建议
(就医分级 + 饮食运动作息 + 免责),并标 grounded=False。建议这一步永远经过临床红线层,
绝不让 LLM 直接给用药/诊断。
"""
from __future__ import annotations

from typing import Any

from loguru import logger

from app.agents.interpreter.citation_guard import GuardResult, guard
from app.agents.interpreter.joint_analysis import detect_joint_signals
from app.agents.interpreter.medical_advice import (
    DISCLAIMER,
    build_advice,
    lifestyle_advice,
    violates_red_line,
)
from app.agents.interpreter.prompts import SYSTEM_PROMPT
from app.agents.interpreter.risk_grading import RiskLevel, TriageLevel, grade_risk
from app.agents.parser.schemas import Report
from app.config import get_settings
from app.observability.metrics import agent_invocations

MAX_REACT_STEPS = 3
_UNGROUNDED_INTERP = (
    "未能在知识库中为该指标找到充分依据,以下仅为基于偏离幅度的分级提示,请就医由医生确认。"
)


async def _retrieve_kb_for(query: str, top_k: int = 4) -> list[dict]:
    # 重型 RAG 依赖(pymilvus / sentence-transformers / FlagEmbedding)惰性导入,
    # 使 react_chain 可在 CI 轻量环境被导入(golden 测试会 monkeypatch 掉本函数)。
    from app.rag.hybrid_retrieval import hybrid_search
    from app.rag.reranker import cross_encoder_rerank

    s = get_settings()
    chunks = await hybrid_search(collection=s.milvus_collection_medical, query=query, top_k=20)
    return cross_encoder_rerank(query, chunks, top_k=top_k)


async def _llm_complete(prompt: str, **kwargs) -> str:
    """LLM 调用包装:openai 依赖惰性导入,同时给 golden 测试一个稳定的 monkeypatch 点。"""
    from app.core.llm import chat_complete

    return await chat_complete(prompt, **kwargs)


def _render_prompt(ind, evidence: list[dict], risk) -> str:
    citations = "\n".join(
        f"[{e['doc_id']}:{e['chunk_id']}] {e['text'][:300]}" for e in evidence
    ) or "（无）"
    return f"""
指标：{ind.name} = {ind.value}{ind.unit or ''}（参考 {ind.ref_range or '—'}）
方向：{ind.abnormal_direction}
分级：{risk.risk_level.value} · 就医建议：{risk.triage.value}{'（危急值兜底）' if risk.is_critical else ''}

请基于以下证据生成 JSON：{{"interpretation": "...", "lifestyle": "...", "triage_advice": "..."}}
每个字段都要包含至少 1 条 [doc_id:chunk_id] 引用，引用必须来自下方证据，禁止下「诊断结论」。
证据：
{citations}
"""


def _safe_json(raw: str) -> dict:
    import json
    import re

    m = re.search(r"\{.*\}", raw or "", re.DOTALL)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}


def _step_query(ind, step: int) -> str:
    """第 1 步用裸指标名;后续步放宽:带异常方向 + 临床意义,捞进更多/更相关证据。"""
    if step == 1:
        return ind.name
    return f"{ind.name} {ind.abnormal_direction or ''} 临床意义 参考范围".strip()


async def _interpret_indicator(ind, joint_patterns: list[str]) -> dict[str, Any]:
    risk = grade_risk(ind.name, ind.value, ind.ref_range)
    evidence_by_key: dict[str, dict] = {}
    gen: dict = {}
    guard_res: GuardResult | None = None
    steps = 0

    for step in range(1, MAX_REACT_STEPS + 1):
        steps = step
        # 逐步放宽精排窗口(4 / 8 / 12),证据按 doc:chunk 去重累积。
        # 跳过缺 doc_id/chunk_id/text 的畸形 chunk(与 citation_guard 同走防御式 .get,
        # 一条坏数据不该让整条指标解读落 except 全降级)。
        for e in await _retrieve_kb_for(_step_query(ind, step), top_k=4 * step):
            doc_id, chunk_id = e.get("doc_id"), e.get("chunk_id")
            if doc_id is None or chunk_id is None or "text" not in e:
                continue
            evidence_by_key[f"{doc_id}:{chunk_id}"] = e
        evidence = list(evidence_by_key.values())

        raw = await _llm_complete(
            _render_prompt(ind, evidence, risk), system=SYSTEM_PROMPT,
            response_format="json", temperature=0.2, max_tokens=600,
        )
        gen = _safe_json(raw)
        guard_res = guard(
            {
                "interpretation": gen.get("interpretation") or "",
                "lifestyle": gen.get("lifestyle") or "",
                "triage_advice": gen.get("triage_advice") or "",
            },
            evidence,
        )
        if guard_res.grounded:
            break

    grounded = bool(guard_res and guard_res.grounded)
    llm_interp = gen.get("interpretation") or ""
    # 临床红线:即便引用接地,若解读正文越界(用药/诊断)也不当权威输出 → 降级处理
    if grounded and violates_red_line(llm_interp):
        grounded = False
    # citations 跟随最终 grounded:降级后不展示我们不输出的解读所对应的引用
    valid_cites = (
        guard_res.fields["interpretation"].valid
        if grounded and guard_res and "interpretation" in guard_res.fields else []
    )
    # 建议永远经临床红线层(就医分级 + 安全生活方式 + 免责);未接地会被强制就医兜底
    advice = build_advice(risk, joint_patterns, grounded=grounded,
                          llm_lifestyle=gen.get("lifestyle"))

    return {
        "indicator": ind.name,
        "value": ind.value,
        "ref_range": ind.ref_range,
        "risk_level": risk.risk_level.value,
        "triage": advice["triage"],            # 经红线升级后的就医分级
        "is_critical": risk.is_critical,
        "grounded": grounded,
        "react_steps": steps,
        "citations": valid_cites,              # 只列经守卫校验为真的引用
        "interpretation": llm_interp if grounded else _UNGROUNDED_INTERP,
        "lifestyle": advice["lifestyle"],
        "triage_advice": advice["triage_advice"],
        "disclaimer": advice["disclaimer"],
        "escalated": advice["escalated"],
    }


async def interpret_report(report: Report) -> dict[str, Any]:
    abnormal = [ind for ind in report.indicators if ind.abnormal]
    # 方向感知:把异常方向一并交给联合检测,避免「方向错配」误命中(如 ALT 偏低也判肝损伤)。
    joint = detect_joint_signals(
        [ind.name for ind in abnormal],
        directions={ind.name: ind.abnormal_direction for ind in abnormal},
    )

    # 指标 → 命中的联合信号 pattern(供 medical_advice 选生活方式建议)
    # 指标 → 联合结论 hint(回填到 per-indicator,让每个指标卡片能展示参与的联合判定)
    patterns_by_indicator: dict[str, list[str]] = {}
    hints_by_indicator: dict[str, list[str]] = {}
    for s in joint:
        for n in s.matched_indicators:
            patterns_by_indicator.setdefault(n, []).append(s.pattern)
            hints_by_indicator.setdefault(n, []).append(s.hint)

    interpretations: list[dict] = []
    had_error = False
    for ind in abnormal:
        try:
            it = await _interpret_indicator(ind, patterns_by_indicator.get(ind.name, []))
        except Exception as e:
            had_error = True
            logger.exception("interpret {} failed", ind.name)
            # 出错也保持与正常项一致的字段形状(下游 it["citations"] 等不会 KeyError),
            # 并保守降级:强制就医 + 免责,绝不静默给一个"看起来正常"的结果。
            it = {
                "indicator": ind.name,
                "value": ind.value,
                "ref_range": ind.ref_range,
                "risk_level": RiskLevel.WATCH.value,
                "triage": TriageLevel.SPECIALIST.value,
                "is_critical": False,
                "grounded": False,
                "react_steps": 0,
                "citations": [],
                "interpretation": _UNGROUNDED_INTERP,
                "lifestyle": lifestyle_advice(ind.name, patterns_by_indicator.get(ind.name, [])),
                "triage_advice": "解读过程出错,建议就医由医生进一步确认。",
                "disclaimer": DISCLAIMER,
                "escalated": True,
                "error": str(e),
            }

        # 把该指标参与的联合结论 hint 回填(正常 / 出错两条路径统一处理),
        # 让联合判定不止停在报告级 joint_signals,也能落到每个指标卡片。
        it["joint_hints"] = hints_by_indicator.get(ind.name, [])
        interpretations.append(it)

    agent_invocations.labels(
        agent="interpreter", outcome="error" if had_error else "ok"
    ).inc()
    return {
        "report_id": report.report_id,
        "user_id": report.user_id,
        "joint_signals": [s.__dict__ for s in joint],
        "interpretations": interpretations,
    }
