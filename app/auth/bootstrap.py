"""认证账号引导 —— 启动时确保「管理员 + 演示账号」存在。

幂等:已存在的账号一律跳过(不覆盖运行期被管理员改过的口令 / 角色),
既保证 demo 永远可登录,又不破坏线上改动。

演示账号 ``demo-001`` 的 username 即 user_id,与 ``scripts/seed.py`` 灌入的
体检报告 user_id 对齐 —— 登录后历史趋势页直接有数据可看。
"""
from __future__ import annotations

from loguru import logger

from app.auth.passwords import hash_password
from app.config import get_settings
from app.schemas.models import AuthAccount

# 演示账号(登录页快速体验)。username == user_id,与已灌的体检报告对齐。
_DEMO_USERS = ["demo-001"]


async def ensure_auth_seed() -> None:
    s = get_settings()
    await _ensure_account(s.admin_username, s.admin_password, role="admin", is_demo=False)
    for u in _DEMO_USERS:
        await _ensure_account(u, s.demo_password, role="user", is_demo=True)


async def _ensure_account(username: str, password: str, *, role: str, is_demo: bool) -> None:
    # 用 get_or_create 保证幂等且对「多 worker 并发启动」的竞态安全:
    # tortoise 会吞掉并发 INSERT 的 IntegrityError 后重新 get,不会抛重复键。
    _, created = await AuthAccount.get_or_create(
        username=username,
        defaults={
            "password_hash": hash_password(password),
            "role": role,
            "is_demo": is_demo,
        },
    )
    if created:
        logger.info("seeded auth account: {} (role={}, demo={})", username, role, is_demo)
