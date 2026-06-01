"""`_parse_paddle_result` 纯逻辑测试 —— 锁定 PaddleOCR 2.7.x 返回格式的解析契约。

PaddleOCR 2.7.x `ocr.ocr(img, cls=True)` 按页包裹返回：
    [ [ [box, (text, conf)], ... ] ]
其中 box = 四个角点 [[x,y],[x,y],[x,y],[x,y]]。

本套件不依赖 paddleocr / numpy / PIL，纯 Python，可在 CI pure-logic 环境跑
（`ocr.py` 已把 metrics / 重型依赖全部改为函数内懒加载）。
"""
from app.agents.parser.ocr import _parse_paddle_result

# 轴对齐矩形角点
BOX1 = [[10, 20], [110, 20], [110, 50], [10, 50]]


def _det(box, text, conf):
    """构造一个 PaddleOCR 检测项 [box, (text, conf)]。"""
    return [box, (text, conf)]


def test_parses_page_wrapped_standard_format():
    out = _parse_paddle_result([[_det(BOX1, "白细胞 WBC", 0.98)]])
    assert len(out) == 1
    assert out[0]["text"] == "白细胞 WBC"
    assert out[0]["confidence"] == 0.98
    assert isinstance(out[0]["confidence"], float)
    # bbox = [minx, miny, maxx, maxy]
    assert out[0]["bbox"] == [10, 20, 110, 50]


def test_bbox_from_skewed_quadrilateral():
    """倾斜四边形 → bbox 取四点 min/max 的外接框。"""
    skew = [[12, 18], [108, 22], [112, 52], [8, 48]]
    out = _parse_paddle_result([[_det(skew, "x", 0.9)]])
    assert out[0]["bbox"] == [8, 18, 112, 52]


def test_multiple_detections_keep_order():
    raw = [[
        _det(BOX1, "项目", 0.95),
        _det([[10, 60], [80, 60], [80, 90], [10, 90]], "结果", 0.91),
    ]]
    assert [o["text"] for o in _parse_paddle_result(raw)] == ["项目", "结果"]


def test_confidence_always_cast_to_float():
    out = _parse_paddle_result([[_det(BOX1, "Hb", 1)]])  # 传 int 置信度
    assert out[0]["confidence"] == 1.0
    assert isinstance(out[0]["confidence"], float)


def test_empty_and_none_inputs_return_empty():
    assert _parse_paddle_result(None) == []
    assert _parse_paddle_result([]) == []
    assert _parse_paddle_result([None]) == []   # PaddleOCR 对空白页返回 [None]
    assert _parse_paddle_result([[]]) == []       # 页内无检测


def test_malformed_items_are_skipped_not_crash():
    """畸形检测项要被跳过，整体不崩 —— 真实 OCR 偶发残缺输出的健壮性。"""
    raw = [[
        _det(BOX1, "正常", 0.97),
        None,                       # 空项
        ["only-box-no-text-conf"],  # 缺 (text, conf) → IndexError
        [BOX1],                     # item[1] 越界
        _det([[5, 5], [9, 5], [9, 9], [5, 9]], "又一条", 0.88),
    ]]
    assert [o["text"] for o in _parse_paddle_result(raw)] == ["正常", "又一条"]


def test_non_numeric_confidence_skipped():
    """置信度无法转 float（如被错配成坐标字符串）→ 跳过该项而非抛错。"""
    bad = [BOX1, ("文本", "not-a-number")]
    out = _parse_paddle_result([[bad, _det(BOX1, "好的", 0.9)]])
    assert [o["text"] for o in out] == ["好的"]
