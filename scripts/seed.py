"""一键初始化全栈：MySQL 表 + Milvus 集合 + 医学知识库 + Demo Report。

用法：
    python -m scripts.seed
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from loguru import logger

from app.config import get_settings
from app.core.db import close_db, init_db
from app.core.storage import ensure_bucket
from app.observability.logging import setup_logging
from app.rag.ingestion import ingest_markdown_dir
from app.schemas.models import ReportModel


ROOT = Path(__file__).resolve().parents[1]


async def seed_kb() -> None:
    s = get_settings()
    n = await ingest_markdown_dir(
        ROOT / "app" / "data" / "kb",
        collection=s.milvus_collection_medical,
        base_metadata={"source": "seed"},
    )
    logger.info("medical KB seed done, {} chunks", n)


async def seed_demo_report() -> None:
    payload = json.loads(
        (ROOT / "app" / "data" / "seed" / "sample_indicators.json").read_text(encoding="utf-8")
    )
    await ReportModel.update_or_create(
        report_id=payload["report_id"],
        defaults={
            "user_id": payload["user_id"],
            "source_object_key": payload["source_object_key"],
            "indicators": payload["indicators"],
        },
    )
    logger.info("demo report seeded -> {}", payload["report_id"])


async def main() -> None:
    setup_logging()
    ensure_bucket()
    await init_db()
    try:
        await seed_demo_report()
        await seed_kb()
    finally:
        await close_db()
    logger.info("ALL SEED DONE")


if __name__ == "__main__":
    asyncio.run(main())
