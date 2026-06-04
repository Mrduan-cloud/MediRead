"""历史路由集成测试 —— 内存 SQLite,覆盖单报告详情 / 列表 / 越权隔离。

与 test_routes_auth 同策略:不进 CI 轻量「纯逻辑」列表(那步不装 tortoise/httpx),
本地 + 完整 dev 依赖下 `pytest tests/test_routes_history.py` 可直接跑。
"""
from __future__ import annotations

import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from tortoise import Tortoise

from app.api import routes_history
from app.auth import create_access_token
from app.schemas.models import InterpretationModel, ReportModel


def auth_header(user_id: str = "u1", role: str = "user") -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id, role)}"}


@pytest_asyncio.fixture
async def client():
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["app.schemas.models"]})
    await Tortoise.generate_schemas()
    app = FastAPI()
    app.include_router(routes_history.router, prefix="/api/history")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    await Tortoise.close_connections()


async def test_get_report_returns_indicators(client):
    await ReportModel.create(
        report_id="r1", user_id="u1", source_object_key="k",
        indicators=[{"name": "WBC", "value": 11.2, "abnormal": True}],
    )
    r = await client.get("/api/history/report/r1", headers=auth_header("u1"))
    assert r.status_code == 200
    body = r.json()
    assert body["report_id"] == "r1"
    assert len(body["indicators"]) == 1
    assert body["interpretation"] is None


async def test_get_report_includes_latest_interpretation(client):
    await ReportModel.create(report_id="r2", user_id="u1", source_object_key="k", indicators=[])
    await InterpretationModel.create(
        report_id="r2", user_id="u1", payload={"interpretations": [{"indicator": "X"}]}
    )
    r = await client.get("/api/history/report/r2", headers=auth_header("u1"))
    assert r.status_code == 200
    assert r.json()["interpretation"]["interpretations"][0]["indicator"] == "X"


async def test_get_report_404_when_missing(client):
    r = await client.get("/api/history/report/none", headers=auth_header("u1"))
    assert r.status_code == 404


async def test_get_report_cross_user_isolation(client):
    # u1 的报告,u2 不可见(按 user_id 过滤 → 404 而非 403,不泄露存在性)
    await ReportModel.create(report_id="r3", user_id="u1", source_object_key="k", indicators=[])
    r = await client.get("/api/history/report/r3", headers=auth_header("u2"))
    assert r.status_code == 404


async def test_list_reports_counts(client):
    await ReportModel.create(
        report_id="r4", user_id="u1", source_object_key="k",
        indicators=[{"name": "A", "abnormal": True}, {"name": "B", "abnormal": False}],
    )
    r = await client.get("/api/history/reports", headers=auth_header("u1"))
    assert r.status_code == 200
    rows = r.json()
    assert rows[0]["n_indicators"] == 2
    assert rows[0]["n_abnormal"] == 1
