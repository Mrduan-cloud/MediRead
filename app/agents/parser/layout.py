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
