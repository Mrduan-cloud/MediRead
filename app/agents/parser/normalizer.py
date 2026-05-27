"""指标归一化与同义词映射。

中英文别名 → 标准名（贯穿后续 RAG 检索与多指标联合分析）。
词典源：公开医学词典 + 自建别名词典 (`app/data/synonyms.json`)。
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_SYNONYMS_PATH = Path(__file__).resolve().parents[2] / "data" / "synonyms.json"


@lru_cache
def _load_synonyms() -> dict[str, str]:
    """加载别名 → 标准名词典。"""
    if _SYNONYMS_PATH.exists():
        return json.loads(_SYNONYMS_PATH.read_text(encoding="utf-8"))
    return {
        # 兜底示例
        "GGT": "γ-谷氨酰转移酶",
        "γ-GT": "γ-谷氨酰转移酶",
        "HDL-C": "高密度脂蛋白胆固醇",
        "LDL-C": "低密度脂蛋白胆固醇",
        "ALT": "丙氨酸氨基转移酶",
        "GPT": "丙氨酸氨基转移酶",
        "AST": "天门冬氨酸氨基转移酶",
        "GOT": "天门冬氨酸氨基转移酶",
        "HGB": "血红蛋白",
        "WBC": "白细胞计数",
        "PLT": "血小板计数",
    }


def normalize_indicator_name(raw_name: str) -> str:
    """根据词典把别名映射为标准名。匹配失败则返回原字符串。"""
    syn = _load_synonyms()
    key = raw_name.strip().upper().replace(" ", "")
    return syn.get(key) or syn.get(raw_name.strip()) or raw_name.strip()


def parse_ref_range(text: str | None) -> tuple[float | None, float | None]:
    """把参考范围字符串解析为 (low, high)。支持「3.5-5.5」「<5」「≥40」等格式。"""
    if not text:
        return (None, None)
    t = text.strip().replace("–", "-").replace("~", "-")
    if t.startswith("<") or t.startswith("≤"):
        try:
            return (None, float(t[1:]))
        except ValueError:
            return (None, None)
    if t.startswith(">") or t.startswith("≥"):
        try:
            return (float(t[1:]), None)
        except ValueError:
            return (None, None)
    parts = t.split("-")
    if len(parts) == 2:
        try:
            return (float(parts[0]), float(parts[1]))
        except ValueError:
            return (None, None)
    return (None, None)
