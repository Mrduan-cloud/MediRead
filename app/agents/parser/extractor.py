"""6 字段抽取 + 强约束输出 — 真实实现：bbox 按行归并 + 列定位。"""
from __future__ import annotations

import re
from typing import Any

from jsonschema import validate as jsonschema_validate
from loguru import logger

from app.agents.parser.layout import detect_template, get_column_anchors
from app.agents.parser.normalizer import normalize_indicator_name, parse_ref_range
from app.agents.parser.ocr import ocr_image, ocr_pdf
from app.agents.parser.schemas import Indicator, Report


REPORT_JSON_SCHEMA = {
    "type": "object",
    "required": ["report_id", "user_id", "indicators"],
    "properties": {
        "report_id": {"type": "string"},
        "user_id": {"type": "string"},
        "indicators": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "raw_name", "value"],
                "properties": {
                    "name": {"type": "string"},
                    "raw_name": {"type": "string"},
                    "value": {},
                    "unit": {"type": ["string", "null"]},
                    "ref_range": {"type": ["string", "null"]},
                },
            },
        },
    },
}


_NUM_RE = re.compile(r"^-?\d+(?:\.\d+)?$")


def _bbox_center_y(line: dict) -> float:
    bbox = line.get("bbox", [0, 0, 0, 0])
    return (bbox[1] + bbox[3]) / 2 if bbox else 0


def _bbox_center_x(line: dict) -> float:
    bbox = line.get("bbox", [0, 0, 0, 0])
    return (bbox[0] + bbox[2]) / 2 if bbox else 0


def _group_into_rows(lines: list[dict], y_tol: float = 12.0) -> list[list[dict]]:
    """按 y 中心点把 OCR token 归并为行。"""
    if not lines:
        return []
    sorted_lines = sorted(lines, key=_bbox_center_y)
    rows: list[list[dict]] = []
    current: list[dict] = []
    cy_prev = -1e9
    for ln in sorted_lines:
        cy = _bbox_center_y(ln)
        if current and abs(cy - cy_prev) > y_tol:
            rows.append(sorted(current, key=_bbox_center_x))
            current = []
        current.append(ln)
        cy_prev = cy
    if current:
        rows.append(sorted(current, key=_bbox_center_x))
    return rows


def _page_width(lines: list[dict]) -> float:
    if not lines:
        return 1.0
    return max(ln.get("bbox", [0, 0, 0, 0])[2] for ln in lines) or 1.0


def _row_to_indicator(row: list[dict], anchors: dict[str, tuple[float, float]],
                      page_w: float) -> Indicator | None:
    cells: dict[str, str] = {}
    for tok in row:
        rel_x = _bbox_center_x(tok) / page_w
        for col, (lo, hi) in anchors.items():
            if lo <= rel_x < hi:
                cells[col] = (cells.get(col, "") + " " + tok["text"]).strip()
                break

    name = cells.get("name", "").strip()
    value_raw = cells.get("value", "").strip()
    if not name or not value_raw:
        return None
    # value 必须像数字或定性结果
    value: float | str
    if _NUM_RE.match(value_raw.replace(",", "")):
        value = float(value_raw.replace(",", ""))
    elif value_raw in {"阴性", "阳性", "+", "-", "弱阳性"}:
        value = value_raw
    else:
        return None

    return Indicator(
        name=name,
        raw_name=name,
        value=value,
        unit=cells.get("unit") or None,
        ref_range=cells.get("ref_range") or None,
    )


def _mark_abnormal(ind: Indicator) -> Indicator:
    if isinstance(ind.value, (int, float)):
        low, high = parse_ref_range(ind.ref_range)
        if low is not None and float(ind.value) < low:
            ind.abnormal = True
            ind.abnormal_direction = "low"
        elif high is not None and float(ind.value) > high:
            ind.abnormal = True
            ind.abnormal_direction = "high"
    return ind


def _ocr_lines_to_indicators(lines: list[dict]) -> list[Indicator]:
    template = detect_template(lines)
    anchors = get_column_anchors(template)
    page_w = _page_width(lines)
    rows = _group_into_rows(lines)
    result: list[Indicator] = []
    for row in rows:
        ind = _row_to_indicator(row, anchors, page_w)
        if ind is None:
            continue
        ind.name = normalize_indicator_name(ind.raw_name)
        result.append(_mark_abnormal(ind))
    return result


def parse_report(
    *,
    report_id: str,
    user_id: str,
    file_bytes: bytes,
    file_format: str,
    source_object_key: str,
) -> Report:
    if file_format == "pdf":
        ocr_pages = ocr_pdf(file_bytes)
        lines = [ln for page in ocr_pages for ln in page]
    else:
        lines = ocr_image(file_bytes)

    indicators = _ocr_lines_to_indicators(lines)
    logger.info("extracted {} indicators from {} OCR lines", len(indicators), len(lines))

    report = Report(
        report_id=report_id,
        user_id=user_id,
        source_object_key=source_object_key,
        indicators=indicators,
    )
    jsonschema_validate(report.model_dump(), REPORT_JSON_SCHEMA)
    return report
