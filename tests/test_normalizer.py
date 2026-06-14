"""指标归一化单测样例。"""
from app.agents.parser.normalizer import (
    aliases_for,
    glucose_mg_dl_to_mmol_l,
    glucose_mmol_l_to_mg_dl,
    is_glucose_indicator,
    normalize_glucose_value,
    normalize_indicator_name,
    parse_ref_range,
)


def test_alias_mapping():
    assert normalize_indicator_name("GGT") == "γ-谷氨酰转移酶"
    assert normalize_indicator_name("HDL-C") == "高密度脂蛋白胆固醇"
    # 未命中 → 返回原文
    assert normalize_indicator_name("未知指标X") == "未知指标X"


def test_alias_chinese_oldnames_to_standard():
    # 中文旧称 / 变体 → 标准名(↔ 的另一侧)
    assert normalize_indicator_name("谷丙转氨酶") == "丙氨酸氨基转移酶"
    assert normalize_indicator_name("谷草转氨酶") == "天门冬氨酸氨基转移酶"
    assert normalize_indicator_name("谷氨酰转肽酶") == "γ-谷氨酰转移酶"
    assert normalize_indicator_name("血色素") == "血红蛋白"
    assert normalize_indicator_name("三酰甘油") == "甘油三酯"


def test_alias_messy_ocr_variants():
    # 大小写 / 全角 / 空白 / 连字符与希腊字母变体,都应命中同一标准名
    assert normalize_indicator_name("ggt") == "γ-谷氨酰转移酶"
    assert normalize_indicator_name("ＧＧＴ") == "γ-谷氨酰转移酶"      # 全角
    assert normalize_indicator_name(" G G T ") == "γ-谷氨酰转移酶"     # 内嵌空白
    assert normalize_indicator_name("Γ-GT") == "γ-谷氨酰转移酶"        # 希腊大写 Γ
    assert normalize_indicator_name("HDL—C") == "高密度脂蛋白胆固醇"  # em-dash 连字符


def test_alias_standard_name_is_idempotent():
    # 已是标准名 → 原样返回(不被误改)
    for std in ("丙氨酸氨基转移酶", "γ-谷氨酰转移酶", "血红蛋白"):
        assert normalize_indicator_name(std) == std


def test_alias_empty_and_unknown():
    assert normalize_indicator_name("") == ""
    assert normalize_indicator_name("  ") == ""
    assert normalize_indicator_name("自定义项 Z") == "自定义项 Z"


def test_aliases_for_reverse_lookup():
    al = aliases_for("γ-谷氨酰转移酶")
    assert "GGT" in al and "γ-GT" in al and "谷氨酰转肽酶" in al
    assert aliases_for("丙氨酸氨基转移酶") == ["ALT", "GPT", "谷丙转氨酶", "谷氨酸丙酮酸转氨酶"] \
        or set(aliases_for("丙氨酸氨基转移酶")) >= {"ALT", "GPT", "谷丙转氨酶"}
    assert aliases_for("不存在的标准名") == []


def test_ref_range_parse():
    assert parse_ref_range("3.5-5.5") == (3.5, 5.5)
    assert parse_ref_range("3.5~5.5") == (3.5, 5.5)
    assert parse_ref_range("<5") == (None, 5.0)
    assert parse_ref_range("≥40") == (40.0, None)
    assert parse_ref_range(None) == (None, None)


# ---------- 血糖单位归一化 ----------
def test_glucose_unit_conversions():
    # 葡萄糖 1 mmol/L ≈ 18 mg/dL
    assert glucose_mg_dl_to_mmol_l(90) == 5.0
    assert glucose_mg_dl_to_mmol_l(180) == 10.0
    assert glucose_mmol_l_to_mg_dl(5.0) == 90.0
    assert glucose_mmol_l_to_mg_dl(6.1) == 109.8


def test_is_glucose_indicator():
    assert is_glucose_indicator("葡萄糖")
    assert is_glucose_indicator("空腹血糖")
    assert is_glucose_indicator("GLU")
    assert is_glucose_indicator("Glucose")
    assert not is_glucose_indicator("丙氨酸氨基转移酶")
    assert not is_glucose_indicator(None)


def test_normalize_glucose_mg_dl_to_mmol_l():
    # 血糖 + mg/dL → 换算 + 单位改 mmol/L
    assert normalize_glucose_value("葡萄糖", 90, "mg/dL") == (5.0, "mmol/L")
    assert normalize_glucose_value("空腹血糖", 126, "mg/dl") == (7.0, "mmol/L")
    # 大小写 / 空格变体也能识别
    assert normalize_glucose_value("血糖", 90, "MG / DL") == (5.0, "mmol/L")


def test_normalize_glucose_already_mmol_unchanged():
    assert normalize_glucose_value("血糖", 5.5, "mmol/L") == (5.5, "mmol/L")


def test_normalize_glucose_non_glucose_untouched():
    # 非血糖指标即便 mg/dL 也不动(胆固醇换算因子≠18,绝不能误用)
    assert normalize_glucose_value("总胆固醇", 200, "mg/dL") == (200, "mg/dL")


def test_normalize_glucose_qualitative_and_missing_unit():
    assert normalize_glucose_value("血糖", "阴性", "mg/dL") == ("阴性", "mg/dL")
    assert normalize_glucose_value("葡萄糖", 5.5, None) == (5.5, None)
