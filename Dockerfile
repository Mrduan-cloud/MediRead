# syntax=docker/dockerfile:1.6
# 多阶段构建：第一阶段装依赖，第二阶段拷贝运行时
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt


FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Shanghai \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# OCR 必须的系统依赖：libgomp/glib/sm/xext/xrender, poppler (PDF→Image)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 libglib2.0-0 libsm6 libxext6 libxrender1 libgl1 \
    poppler-utils curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r app && useradd -r -g app -d /app app

COPY --from=builder /install /usr/local
COPY --chown=app:app . /app

RUN mkdir -p /app/.cache/models /app/.cache/bm25 /app/.cache/paddle && chown -R app:app /app/.cache

USER app
EXPOSE 8000

# 预置 PP-OCR 模型(det/rec/cls)到镜像 → 运行时离线可用,免去首次请求时联网下载
# (数十 MB + 数秒延迟)。以 app 用户执行,模型落到 ~/.paddleocr(=/app/.paddleocr,
# app 的 home),与运行时 PaddleOCR 的默认缓存路径一致,直接命中。
# 依赖 requirements.txt 的 Cython<3 pin(否则 import paddle 段错误,模型也无从下载)。
# build 期需可达 PP-OCR 模型 CDN;失败即 build 红,信号清晰。
RUN python -c "from paddleocr import PaddleOCR; PaddleOCR(lang='ch', use_angle_cls=True, show_log=False)" \
    && echo "PP-OCR models prefetched into image"

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
