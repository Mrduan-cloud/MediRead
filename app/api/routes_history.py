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
async def list_reports(
    user: CurrentUser = Depends(get_current_user),
    page: int = 1,
    page_size: int = 10,
) -> dict[str, Any]:
    """分页列出当前用户的报告(最新优先)。

    返回 {items, total, page, page_size},供前端「我的报告」侧栏翻页。
    防御非法分页参数:页码至少 1,每页 1..50(50 为旧硬上限,避免一次拉太多)。
    """
    page = max(1, page)
    page_size = max(1, min(page_size, 50))
    base = ReportModel.filter(user_id=user.user_id)
    total = await base.count()
    # 次级排序键 report_id 保证稳定全序:created_at 撞值(同秒批量上传)时,
    # 单凭 -created_at 翻页可能漏项/重项;-report_id 给出确定性 tiebreak。
    rows = (
        await base.order_by("-created_at", "-report_id")
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [
        {
            "report_id": r.report_id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "n_indicators": len(r.indicators) if r.indicators else 0,
            "n_abnormal": sum(1 for i in (r.indicators or []) if i.get("abnormal")),
        }
        for r in rows
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


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
