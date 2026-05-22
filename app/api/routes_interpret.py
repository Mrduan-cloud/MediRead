"""触发医学解读。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.agents.interpreter.react_chain import interpret_report
from app.agents.parser.schemas import Indicator, Report
from app.auth import CurrentUser, get_current_user
from app.schemas.models import InterpretationModel, ReportModel

router = APIRouter()


@router.post("/{report_id}")
async def trigger_interpret(report_id: str, user: CurrentUser = Depends(get_current_user)) -> dict:
    rec = await ReportModel.filter(report_id=report_id, user_id=user.user_id).first()
    if not rec or not rec.indicators:
        raise HTTPException(404, "report not parsed yet, call /api/parse/{id} first")
    report = Report(
        report_id=rec.report_id,
        user_id=rec.user_id,
        source_object_key=rec.source_object_key,
        indicators=[Indicator(**i) for i in rec.indicators],
    )
    result = await interpret_report(report)
    await InterpretationModel.create(
        report_id=report_id,
        user_id=user.user_id,
        payload=result,
    )
    return result
