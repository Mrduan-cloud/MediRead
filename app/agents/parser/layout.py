"""版式识别 — 对国内主流医院与体检中心的报告模板做版式归类。

目的：定位「项目名 / 结果 / 单位 / 参考范围 / 提示」列位置，提升字段抽取准确率。
"""
from __future__ import annotations

from typing import Literal

HospitalTemplate = Literal[
    "generic",      # 通用模板（兜底）
    "huaxi",        # 华西
    "ppd",          # 平安体检中心
    "meinian",      # 美年大健康
    "ikang",        # 爱康国宾
    "ciming",       # 慈铭
]


def detect_template(ocr_lines: list[dict]) -> HospitalTemplate:
    """根据 OCR 抽到的关键字（医院名 / Logo 周边文本）判定模板。"""
    text = " ".join(line.get("text", "") for line in ocr_lines)
    if "华西" in text:
        return "huaxi"
    if "美年" in text:
        return "meinian"
    if "爱康" in text:
        return "ikang"
    if "慈铭" in text:
        return "ciming"
    if "平安" in text:
        return "ppd"
    return "generic"


def get_column_anchors(template: HospitalTemplate) -> dict[str, tuple[float, float]]:
    """返回各列的 x 范围（相对页宽 0~1），用于按列归并 OCR token。"""
    # TODO: 维护每家医院的列模板坐标
    return {
        "name": (0.05, 0.30),
        "value": (0.30, 0.45),
        "unit": (0.45, 0.55),
        "ref_range": (0.55, 0.75),
        "abnormal": (0.75, 0.85),
    }


# —— 版式区域识别（header / table / footer）——
# 抬头关键字（报告标题 / 患者信息）；页脚关键字（签字 / 审核 / 打印）。
_HEADER_KW = ("报告单", "检验报告", "体检报告", "姓名", "性别", "年龄", "科室", "送检", "住院号", "门诊号")
_FOOTER_KW = ("检验者", "审核", "核对", "医师", "签名", "签字", "打印")


def _y_center(line: dict) -> float:
    """OCR 行的垂直中心。优先用 bbox=[minx,miny,maxx,maxy]，退化到 line['y']。"""
    bbox = line.get("bbox")
    if bbox and len(bbox) >= 4:
        return (float(bbox[1]) + float(bbox[3])) / 2.0
    return float(line.get("y", 0.0))


def _has_kw(text: str, kws: tuple[str, ...]) -> bool:
    return any(k in text for k in kws)


def detect_regions(
    ocr_lines: list[dict],
    page_height: float | None = None,
    header_band: float = 0.18,
    footer_band: float = 0.85,
) -> dict[str, list[dict]]:
    """把 OCR 行朴素划分为 header / table / footer，保持原行顺序。

    - **位置主导**：归一化 y 落在顶部 `header_band` 内 → header；底部 `footer_band` 外 → footer；其余 → table。
    - **关键字辅助**：底半部出现页脚关键字（审核 / 检验者 / 打印…）→ footer（兜住贴在表格下方、
      还没到最底的签字行）；顶部 40% 内出现抬头关键字（报告单 / 姓名…）→ header。
    - `page_height` 给定则按其归一化；否则用本页 OCR 的 y 极值自动定标。

    返回 `{"header": [...], "table": [...], "footer": [...]}`；三桶并集 = 输入，每行恰好归一类。
    """
    out: dict[str, list[dict]] = {"header": [], "table": [], "footer": []}
    if not ocr_lines:
        return out

    ys = [_y_center(line) for line in ocr_lines]
    lo = 0.0 if page_height else min(ys)
    hi = float(page_height) if page_height else max(ys)
    span = (hi - lo) or 1.0

    for line, y in zip(ocr_lines, ys, strict=True):
        norm = (y - lo) / span
        text = line.get("text", "")
        if norm >= footer_band or (_has_kw(text, _FOOTER_KW) and norm >= 0.55):
            region = "footer"
        elif norm <= header_band or (_has_kw(text, _HEADER_KW) and norm <= 0.40):
            region = "header"
        else:
            region = "table"
        out[region].append(line)
    return out
