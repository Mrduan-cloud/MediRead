"""版式识别单测 —— 医院模板判定 + header/table/footer 区域划分。

纯逻辑（layout.py 只依赖 stdlib），CI pure-logic 可跑。
"""
from app.agents.parser.layout import detect_regions, detect_template


def _line(text: str, y: float, x: float = 100.0) -> dict:
    """构造一条 OCR 行：bbox=[minx,miny,maxx,maxy]，行高 24px。"""
    return {"text": text, "bbox": [x, y, x + 220, y + 24], "confidence": 0.95}


# ---- detect_template：医院关键字 → 模板，未知兜底 generic ----

def test_detect_template_by_hospital_keyword():
    assert detect_template([{"text": "四川大学华西医院"}]) == "huaxi"
    assert detect_template([{"text": "美年大健康体检中心"}]) == "meinian"
    assert detect_template([{"text": "爱康国宾"}]) == "ikang"
    assert detect_template([{"text": "慈铭体检"}]) == "ciming"
    assert detect_template([{"text": "平安健康检查中心"}]) == "ppd"


def test_detect_template_falls_back_to_generic():
    assert detect_template([{"text": "示例市人民医院"}]) == "generic"
    assert detect_template([]) == "generic"


# ---- detect_regions：按位置 + 关键字划分 header/table/footer ----

def _sample_page() -> list[dict]:
    # page_height=1000 下的一页典型体检报告
    return [
        _line("示例医院检验报告单", 20),                       # header（顶部）
        _line("姓名：张三 性别：男 年龄：35", 70),             # header（顶部 + 关键字）
        _line("白细胞 WBC 6.5 10^9/L 3.5-9.5 正常", 220),     # table
        _line("血红蛋白 Hb 150 g/L 130-175 正常", 320),       # table
        _line("谷丙转氨酶 ALT 56 U/L 9-50 偏高", 520),         # table
        _line("审核医师：王五  检验者：李四", 760),            # footer（关键字，贴表格下方）
        _line("打印时间：2026-05-20  第 1 页", 900),           # footer（最底部）
    ]


def test_regions_basic_bands():
    r = detect_regions(_sample_page(), page_height=1000)
    htext = " ".join(line["text"] for line in r["header"])
    ttext = " ".join(line["text"] for line in r["table"])
    ftext = " ".join(line["text"] for line in r["footer"])
    assert "报告单" in htext and "姓名" in htext
    assert "WBC" in ttext and "Hb" in ttext and "ALT" in ttext
    assert "审核医师" in ftext and "打印时间" in ftext


def test_footer_keyword_pulls_signature_above_bottom_band():
    """签字行 y=760（norm 0.77，未到 footer_band 0.85），但带页脚关键字 → 仍归 footer。"""
    r = detect_regions(_sample_page(), page_height=1000)
    assert any("审核医师" in line["text"] for line in r["footer"])
    assert all("审核医师" not in line["text"] for line in r["table"])


def test_table_rows_not_misclassified_as_header():
    """指标行虽在 header_band 之外，也不能因含数字/中文被误判为 header。"""
    r = detect_regions(_sample_page(), page_height=1000)
    assert all("WBC" not in line["text"] for line in r["header"])


def test_every_line_assigned_exactly_once():
    page = _sample_page()
    r = detect_regions(page, page_height=1000)
    total = len(r["header"]) + len(r["table"]) + len(r["footer"])
    assert total == len(page)


def test_empty_returns_empty_buckets():
    assert detect_regions([]) == {"header": [], "table": [], "footer": []}


def test_auto_span_without_page_height():
    """不给 page_height 时用 y 极值自动定标，顶/底两端仍能分出 header / footer。"""
    r = detect_regions(_sample_page())
    assert any("报告单" in line["text"] for line in r["header"])
    assert any("打印时间" in line["text"] for line in r["footer"])
    assert any("Hb" in line["text"] for line in r["table"])
