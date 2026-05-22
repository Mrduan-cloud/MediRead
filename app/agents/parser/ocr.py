"""PaddleOCR 调用 — 真实集成，支持图片 / PDF 双格式。"""
from __future__ import annotations

import time
from functools import lru_cache
from io import BytesIO
from typing import Any

from loguru import logger

from app.config import get_settings
from app.observability.metrics import ocr_latency


@lru_cache(maxsize=1)
def _engine():
    """PaddleOCR 实例 — 懒加载（首次约 5-15s 加载权重）。"""
    from paddleocr import PaddleOCR
    s = get_settings()
    kwargs = {"lang": s.ocr_lang, "use_angle_cls": True, "show_log": False}
    if s.ocr_use_gpu:
        kwargs["use_gpu"] = True
    if s.ocr_det_model_dir:
        kwargs["det_model_dir"] = s.ocr_det_model_dir
    if s.ocr_rec_model_dir:
        kwargs["rec_model_dir"] = s.ocr_rec_model_dir
    if s.ocr_cls_model_dir:
        kwargs["cls_model_dir"] = s.ocr_cls_model_dir
    logger.info("loading PaddleOCR ... ({})", "GPU" if s.ocr_use_gpu else "CPU")
    return PaddleOCR(**kwargs)


def _to_numpy(image_bytes: bytes):
    import numpy as np
    from PIL import Image
    img = Image.open(BytesIO(image_bytes)).convert("RGB")
    return np.array(img)


def _parse_paddle_result(raw) -> list[dict[str, Any]]:
    """PaddleOCR.ocr() 返回 [[box, (text, conf)], ...]"""
    out: list[dict[str, Any]] = []
    if not raw:
        return out
    # 兼容 PaddleOCR 2.x 不同返回格式
    page = raw[0] if (raw and isinstance(raw[0], list) and len(raw[0]) > 0 and isinstance(raw[0][0], list)) else raw
    for item in page or []:
        if not item:
            continue
        try:
            box, (text, conf) = item[0], item[1]
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            out.append({
                "text": text,
                "confidence": float(conf),
                "bbox": [min(xs), min(ys), max(xs), max(ys)],
            })
        except (TypeError, ValueError, IndexError):
            continue
    return out


def ocr_image(image_bytes: bytes) -> list[dict[str, Any]]:
    t0 = time.perf_counter()
    arr = _to_numpy(image_bytes)
    raw = _engine().ocr(arr, cls=True)
    out = _parse_paddle_result(raw)
    ocr_latency.labels(format="image").observe(time.perf_counter() - t0)
    return out


def ocr_pdf(pdf_bytes: bytes) -> list[list[dict[str, Any]]]:
    """PDF → 每页一组 OCR 结果。"""
    from pdf2image import convert_from_bytes
    t0 = time.perf_counter()
    pages = convert_from_bytes(pdf_bytes, dpi=200, fmt="png")
    results: list[list[dict[str, Any]]] = []
    for img in pages:
        buf = BytesIO()
        img.save(buf, format="PNG")
        results.append(ocr_image(buf.getvalue()))
    ocr_latency.labels(format="pdf").observe(time.perf_counter() - t0)
    return results
