"""触发报告解析。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.agents.parser.extractor import parse_report
from app.auth import CurrentUser, get_current_user
from app.core.storage import download_object
from app.schemas.models import ReportModel

router = APIRouter()


@router.post("/{report_id}")
async def trigger_parse(report_id: str, user: CurrentUser = Depends(get_current_user)) -> dict:
    rec = await ReportModel.filter(report_id=report_id, user_id=user.user_id).first()
    if not rec:
        raise HTTPException(404, "report not found")
    file_bytes = await download_object(rec.source_object_key)
    file_format = "pdf" if rec.source_object_key.endswith(".pdf") else "image"
    report = parse_report(
        report_id=report_id,
        user_id=user.user_id,
        file_bytes=file_bytes,
        file_format=file_format,
        source_object_key=rec.source_object_key,
    )
    rec.indicators = [ind.model_dump() for ind in report.indicators]
    await rec.save(update_fields=["indicators"])
    return report.model_dump()
