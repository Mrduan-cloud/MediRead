"""指标归一化与同义词映射。

中英文别名 → 标准名（贯穿后续 RAG 检索与多指标联合分析）。
词典源：公开医学词典 + 自建别名词典 (`app/data/synonyms.json`)。
"""
from __future__ import annotations

import json
import unicodedata
from functools import lru_cache
from pathlib import Path

_SYNONYMS_PATH = Path(__file__).resolve().parents[2] / "data" / "synonyms.json"

# 各种连字符 / 破折号 / 减号统一成 ASCII '-'(OCR / 报告里写法五花八门)
_DASHES = "‐‑‒–—―−﹣－"


def _norm_key(s: str) -> str:
    """归一化匹配键:NFKC(全角→半角)+ 去全部空白 + 连字符统一 + casefold。

    casefold 同时折叠拉丁与希腊大小写(``Γ``↔``γ``),故 ``γ-GT`` / ``Γ-ＧＴ`` /
    ``ｇｇｔ`` 等脏写法都能命中同一条。
    """
    s = unicodedata.normalize("NFKC", s or "").strip()
    s = "".join(s.split())
    for d in _DASHES:
        s = s.replace(d, "-")
    return s.casefold()


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


@lru_cache
def _normalized_lookup() -> dict[str, str]:
    """{归一化键 → 标准名}。键经 _norm_key,故大小写/全半角/连字符/空白都不敏感。"""
    return {_norm_key(k): v for k, v in _load_synonyms().items()}


def normalize_indicator_name(raw_name: str) -> str:
    """把别名(中/英、缩写、旧称、脏 OCR 变体)映射为标准名;匹配失败返回原字符串。

    例:``GGT`` / ``γ-GT`` / ``ｇｇｔ`` / ``谷氨酰转肽酶`` 都 → ``γ-谷氨酰转移酶``。
    """
    if not raw_name:
        return ""
    return _normalized_lookup().get(_norm_key(raw_name), raw_name.strip())


@lru_cache
def _reverse_lookup() -> dict[str, list[str]]:
    rev: dict[str, list[str]] = {}
    for alias, standard in _load_synonyms().items():
        rev.setdefault(standard, []).append(alias)
    return rev


def aliases_for(standard_name: str) -> list[str]:
    """反查一个标准名已知的全部别名(供展示 / KB 检索查询扩展)。无则空列表。"""
    return list(_reverse_lookup().get((standard_name or "").strip(), []))


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


# ============ 血糖单位归一化 ============
# 葡萄糖 1 mmol/L ≈ 18 mg/dL(分子量 ~180,临床取 18.0)。系统以 mmol/L 为标准单位
# (KB 的参考范围 / 风险分级阈值均按 mmol/L),故把 mg/dL 的血糖值统一换算到 mmol/L。
_GLUCOSE_MG_DL_PER_MMOL_L = 18.0
# 血糖指标名(标准名优先,raw 英文别名兜底)。在 normalize_indicator_name 之后判定。
_GLUCOSE_NAMES = ("葡萄糖", "血糖", "glucose", "glu", "fpg", "fbg")
# mg/dL 的各种写法(归一为去空格小写后比对)
_GLUCOSE_MG_DL_UNITS = {"mg/dl", "mgdl", "mg/100ml"}


def glucose_mg_dl_to_mmol_l(value: float) -> float:
    """葡萄糖 mg/dL → mmol/L(保留 2 位小数)。"""
    return round(value / _GLUCOSE_MG_DL_PER_MMOL_L, 2)


def glucose_mmol_l_to_mg_dl(value: float) -> float:
    """葡萄糖 mmol/L → mg/dL(保留 1 位小数)。"""
    return round(value * _GLUCOSE_MG_DL_PER_MMOL_L, 1)


def is_glucose_indicator(name: str | None) -> bool:
    """指标名是否为血糖类(空腹/餐后血糖、葡萄糖、GLU、FPG…)。"""
    n = (name or "").strip().lower()
    return any(g in n for g in _GLUCOSE_NAMES)


def normalize_glucose_value(
    name: str | None, value: float | str, unit: str | None
) -> tuple[float | str, str | None]:
    """血糖指标若单位为 mg/dL → 把数值换算为 mmol/L、单位改 ``mmol/L``。

    纯函数,返回 ``(value, unit)``。非血糖指标、定性值、或单位已是 mmol/L /
    无法识别 → 原样返回(只动血糖的 mg/dL,绝不误改其他指标的同名单位)。
    """
    if not is_glucose_indicator(name) or not isinstance(value, (int, float)):
        return (value, unit)
    u = (unit or "").strip().lower().replace(" ", "")
    if u in _GLUCOSE_MG_DL_UNITS:
        return (glucose_mg_dl_to_mmol_l(float(value)), "mmol/L")
    return (value, unit)
