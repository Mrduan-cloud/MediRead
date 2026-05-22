"""上传体检报告。"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.auth import CurrentUser, get_current_user
from app.config import get_settings
from app.core.storage import upload_object
from app.schemas.models import ReportModel

router = APIRouter()


@router.post("")
async def upload_report(
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    s = get_settings()
    raw = await file.read()
    if len(raw) > s.upload_max_bytes:
        raise HTTPException(413, f"file too large > {s.upload_max_bytes // 1024 // 1024} MB")
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in s.upload_allowed_ext:
        raise HTTPException(415, f"unsupported file type: {ext}; allowed: {s.upload_allowed_ext}")

    report_id = uuid.uuid4().hex
    key = f"reports/raw/{user.user_id}/{report_id}.{ext}"
    await upload_object(key, raw, content_type=file.content_type or "application/octet-stream")

    await ReportModel.create(
        report_id=report_id,
        user_id=user.user_id,
        source_object_key=key,
    )
    return {
        "report_id": report_id,
        "object_key": key,
        "format": "pdf" if ext == "pdf" else "image",
        "size_bytes": len(raw),
    }
