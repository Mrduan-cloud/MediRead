"""Extractor 内部纯逻辑单测 — 不依赖 PaddleOCR。"""
from app.agents.parser.extractor import _group_into_rows, _row_to_indicator
from app.agents.parser.layout import get_column_anchors


def _mk(text: str, x_lo: float, x_hi: float, y_c: float) -> dict:
    return {"text": text, "confidence": 0.99, "bbox": [x_lo, y_c - 6, x_hi, y_c + 6]}


def test_group_into_rows_two_rows():
    lines = [
        _mk("ALT", 100, 200, 100),
        _mk("65", 600, 700, 100),
        _mk("HGB", 100, 200, 130),
        _mk("145", 600, 700, 130),
    ]
    rows = _group_into_rows(lines, y_tol=8)
    assert len(rows) == 2
    assert rows[0][0]["text"] == "ALT"


def test_row_to_indicator_numeric():
    anchors = get_column_anchors("generic")
    # 总宽 1000；按 anchors:
    # name 0.05–0.30  → x: 50–300
    # value 0.30–0.45 → x: 300–450
    # unit 0.45–0.55  → x: 450–550
    # ref_range 0.55–0.75 → x: 550–750
    row = [
        _mk("ALT", 60, 200, 100),
        _mk("65", 320, 420, 100),
        _mk("U/L", 460, 530, 100),
        _mk("7-40", 580, 700, 100),
    ]
    ind = _row_to_indicator(row, anchors, page_w=1000)
    assert ind is not None
    assert ind.value == 65
    assert ind.unit == "U/L"
    assert ind.ref_range == "7-40"
