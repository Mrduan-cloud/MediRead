"""Tortoise-ORM 连接管理。"""
from __future__ import annotations

from loguru import logger
from tortoise import Tortoise

from app.config import get_settings

# aerich.models 仅迁移工具 aerich(dev 依赖)需要;运行镜像不含 aerich,
# 强行加载会 ConfigurationError 导致 ORM 初始化失败 → 全部模型「default_connection 为 None」。
# 按可导入性动态决定:装了 aerich(本地迁移)就带上,运行时没有就跳过,保证 ORM 正常起来。
_ORM_MODELS = ["app.schemas.models"]
try:
    import aerich.models  # noqa: F401

    _ORM_MODELS.append("aerich.models")
except ModuleNotFoundError:
    pass

TORTOISE_CONFIG = {
    "connections": {"default": ""},
    "apps": {
        "models": {
            "models": _ORM_MODELS,
            "default_connection": "default",
        }
    },
    "use_tz": True,
    "timezone": "Asia/Shanghai",
}


async def init_db() -> None:
    s = get_settings()
    cfg = {**TORTOISE_CONFIG, "connections": {"default": s.mysql_dsn}}
    await Tortoise.init(config=cfg)
    await Tortoise.generate_schemas(safe=True)
    logger.info("database initialized ({}@{})", s.mysql_db, s.mysql_host)


async def close_db() -> None:
    await Tortoise.close_connections()


async def is_healthy() -> bool:
    try:
        conn = Tortoise.get_connection("default")
        await conn.execute_query("SELECT 1")
        return True
    except Exception as e:
        logger.warning("db health failed: {}", e)
        return False
