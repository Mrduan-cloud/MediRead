"""结构化日志 (loguru) — JSON 输出可选。"""
from __future__ import annotations

import json
import logging
import sys

from loguru import logger

from app.config import get_settings


def _json_sink(message):
    record = message.record
    out = {
        "ts": record["time"].isoformat(),
        "level": record["level"].name,
        "logger": record["name"],
        "msg": record["message"],
    }
    if record["extra"]:
        out.update(record["extra"])
    if record["exception"]:
        out["exc"] = str(record["exception"])
    sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")


class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back  # type: ignore[assignment]
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging() -> None:
    s = get_settings()
    logger.remove()
    if s.log_json:
        logger.add(_json_sink, level=s.log_level, enqueue=True)
    else:
        logger.add(
            sys.stdout,
            level=s.log_level,
            colorize=True,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                "<level>{message}</level>"
            ),
        )
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    for noisy in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi", "tortoise"):
        logging.getLogger(noisy).handlers = [InterceptHandler()]
        logging.getLogger(noisy).propagate = False
