"""LangChain ReAct 主链：RAG 检索 → 多指标联合分析 → 风险分级 → 结构化解读。"""
from __future__ import annotations

import json
import re
from typing import Any

from loguru import logger

from app.agents.interpreter.joint_analysis import detect_joint_signals
from app.agents.interpreter.prompts import SYSTEM_PROMPT
from app.agents.interpreter.risk_grading import RiskLevel, TriageLevel, grade_risk
from app.agents.parser.schemas import Report
from app.config import get_settings
from app.core.llm import chat_complete
from app.observability.metrics import agent_invocations
from app.rag.hybrid_retrieval import hybrid_search
from app.rag.reranker import cross_encoder_rerank


async def _retrieve_kb_for(name: str) -> list[dict]:
    s = get_settings()
    chunks = await hybrid_search(collection=s.milvus_collection_medical, query=name, top_k=20)
    return cross_encoder_rerank(name, chunks, top_k=4)


def _render_prompt(ind, evidence: list[dict], risk) -> str:
    citations = "\n".join(
        f"[{e['doc_id']}:{e['chunk_id']}] {e['text'][:300]}" for e in evidence
    ) or "（无）"
    return f"""
指标：{ind.name} = {ind.value}{ind.unit or ''}（参考 {ind.ref_range or '—'}）
方向：{ind.abnormal_direction}
分级：{risk.risk_level.value} · 就医建议：{risk.triage.value}{'（危急值兜底）' if risk.is_critical else ''}

请基于以下证据生成 JSON：{{"interpretation": "...", "lifestyle": "...", "triage_advice": "..."}}
每个字段都要包含至少 1 条 [doc_id:chunk_id] 引用，禁止下「诊断结论」。
证据：
{citations}
"""


def _safe_json(raw: str) -> dict:
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}


async def interpret_report(report: Report) -> dict[str, Any]:
    abnormal = [ind for ind in report.indicators if ind.abnormal]
    joint = detect_joint_signals([ind.name for ind in abnormal])

    interpretations: list[dict] = []
    for ind in abnormal:
        try:
            evidence = await _retrieve_kb_for(ind.name)
            risk = grade_risk(ind.name, ind.value, ind.ref_range)
            prompt = _render_prompt(ind, evidence, risk)
            raw = await chat_complete(prompt, system=SYSTEM_PROMPT, response_format="json",
                                       temperature=0.2, max_tokens=600)
            text = _safe_json(raw)
            interpretations.append({
                "indicator": ind.name,
                "value": ind.value,
                "ref_range": ind.ref_range,
                "risk_level": risk.risk_level.value,
                "triage": risk.triage.value,
                "is_critical": risk.is_critical,
                "citations": [f"{e['doc_id']}:{e['chunk_id']}" for e in evidence],
                "interpretation": text.get("interpretation") or "",
                "lifestyle": text.get("lifestyle") or "",
                "triage_advice": text.get("triage_advice") or "",
            })
        except Exception as e:
            logger.exception("interpret {} failed", ind.name)
            interpretations.append({
                "indicator": ind.name,
                "value": ind.value,
                "error": str(e),
                "risk_level": RiskLevel.WATCH.value,
                "triage": TriageLevel.GENERAL.value,
            })

    agent_invocations.labels(agent="interpreter", outcome="ok").inc()
    return {
        "report_id": report.report_id,
        "user_id": report.user_id,
        "joint_signals": [s.__dict__ for s in joint],
        "interpretations": interpretations,
    }
