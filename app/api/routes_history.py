"""多次报告趋势对比 — 按归一化标准名聚合。"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.auth import CurrentUser, get_current_user
from app.schemas.models import InterpretationModel, ReportModel

router = APIRouter()


@router.get("/series")
async def series(user: CurrentUser = Depends(get_current_user), limit: int = 20) -> dict[str, Any]:
    rows = await ReportModel.filter(user_id=user.user_id).order_by("-created_at").limit(limit)
    by_indicator: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if not r.indicators:
            continue
        for ind in r.indicators:
            try:
                val = float(ind["value"])
            except (TypeError, ValueError):
                continue
            by_indicator[ind["name"]].append({
                "report_id": r.report_id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "value": val,
                "ref_range": ind.get("ref_range"),
                "abnormal": ind.get("abnormal", False),
            })
    return {"user_id": user.user_id, "series": by_indicator}


@router.get("/reports")
async def list_reports(user: CurrentUser = Depends(get_current_user)) -> list[dict]:
    rows = await ReportModel.filter(user_id=user.user_id).order_by("-created_at").limit(50)
    return [
        {
            "report_id": r.report_id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "n_indicators": len(r.indicators) if r.indicators else 0,
            "n_abnormal": sum(1 for i in (r.indicators or []) if i.get("abnormal")),
        }
        for r in rows
    ]


@router.get("/report/{report_id}")
async def get_report(report_id: str, user: CurrentUser = Depends(get_current_user)) -> dict:
    """单份报告详情:结构化指标 + 最近一次 AI 解读(若有)。

    供前端「点开历史报告」直接复看,无需重新上传 / 解析原图。
    """
    rec = await ReportModel.filter(report_id=report_id, user_id=user.user_id).first()
    if not rec:
        raise HTTPException(404, "report not found")
    last = (
        await InterpretationModel.filter(report_id=report_id, user_id=user.user_id)
        .order_by("-created_at")
        .first()
    )
    return {
        "report_id": rec.report_id,
        "created_at": rec.created_at.isoformat() if rec.created_at else None,
        "hospital": rec.hospital,
        "indicators": rec.indicators or [],
        "interpretation": last.payload if last else None,
    }
