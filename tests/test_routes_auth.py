"""鉴权路由集成测试 —— 内存 SQLite + 最小 app,覆盖登录/注册/锁定/演示账号。

不进 CI 的轻量「纯逻辑」列表(那一步不装 tortoise/httpx 等);本地 + 完整 dev
依赖下可直接 `pytest tests/test_routes_auth.py`。隔离掉 OCR/RAG 重型栈:只挂
routes_auth.router,用 sqlite://:memory: 起一套独立 schema。
"""
from __future__ import annotations

import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from tortoise import Tortoise

from app.api import routes_auth
from app.auth import hash_password
from app.auth.bootstrap import ensure_auth_seed
from app.config import get_settings
from app.schemas.models import AuthAccount

LOGIN = "/api/auth/login"
REGISTER = "/api/auth/register"
DEMO = "/api/auth/demo-accounts"


@pytest_asyncio.fixture
async def client():
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["app.schemas.models"]})
    await Tortoise.generate_schemas()
    app = FastAPI()
    app.include_router(routes_auth.router, prefix="/api/auth")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    await Tortoise.close_connections()


async def test_login_success_returns_token(client):
    await AuthAccount.create(username="alice", password_hash=hash_password("secret123"), role="user")
    r = await client.post(LOGIN, json={"username": "alice", "password": "secret123"})
    assert r.status_code == 200
    body = r.json()
    assert body["user_id"] == "alice"
    assert body["role"] == "user"
    assert body["token_type"] == "bearer"
    assert body["access_token"]


async def test_login_wrong_password_401(client):
    await AuthAccount.create(username="bob", password_hash=hash_password("right-pw"), role="user")
    r = await client.post(LOGIN, json={"username": "bob", "password": "wrong-pw"})
    assert r.status_code == 401


async def test_login_unknown_user_also_401(client):
    # 用户不存在与口令错返回一致的 401,防用户名枚举
    r = await client.post(LOGIN, json={"username": "ghost", "password": "whatever"})
    assert r.status_code == 401


async def test_login_lockout_after_max_failures(client):
    s = get_settings()
    await AuthAccount.create(
        username="locktest", password_hash=hash_password("correct-pw"), role="user"
    )
    for _ in range(s.auth_max_failed_attempts):
        r = await client.post(LOGIN, json={"username": "locktest", "password": "bad"})
        assert r.status_code == 401
    # 达到阈值后再试 → 429(即便口令正确也被锁拒)
    r = await client.post(LOGIN, json={"username": "locktest", "password": "bad"})
    assert r.status_code == 429
    r = await client.post(LOGIN, json={"username": "locktest", "password": "correct-pw"})
    assert r.status_code == 429


async def test_inactive_account_403(client):
    await AuthAccount.create(
        username="banned", password_hash=hash_password("pw123456"), role="user", is_active=False
    )
    r = await client.post(LOGIN, json={"username": "banned", "password": "pw123456"})
    assert r.status_code == 403


async def test_register_then_login(client):
    r = await client.post(REGISTER, json={"username": "carol", "password": "pw123456"})
    assert r.status_code == 201
    assert r.json()["access_token"]
    # 注册后可用新口令登录
    r = await client.post(LOGIN, json={"username": "carol", "password": "pw123456"})
    assert r.status_code == 200


async def test_register_duplicate_409(client):
    await AuthAccount.create(username="dave", password_hash=hash_password("pw123456"), role="user")
    r = await client.post(REGISTER, json={"username": "dave", "password": "another-pw"})
    assert r.status_code == 409


async def test_register_weak_password_422(client):
    r = await client.post(REGISTER, json={"username": "erin", "password": "123"})
    assert r.status_code == 422


async def test_seed_creates_demo_and_admin(client):
    s = get_settings()
    await ensure_auth_seed()
    # 演示账号可用配置的 demo_password 登录
    r = await client.post(LOGIN, json={"username": "demo-001", "password": s.demo_password})
    assert r.status_code == 200
    # 管理员存在且角色为 admin
    r = await client.post(LOGIN, json={"username": s.admin_username, "password": s.admin_password})
    assert r.status_code == 200
    assert r.json()["role"] == "admin"


async def test_demo_accounts_lists_only_demo(client):
    await ensure_auth_seed()
    await AuthAccount.create(username="private-user", password_hash=hash_password("pw123456"))
    r = await client.get(DEMO)
    assert r.status_code == 200
    users = r.json()["users"]
    assert "demo-001" in users
    assert "private-user" not in users  # 非演示账号不外泄
