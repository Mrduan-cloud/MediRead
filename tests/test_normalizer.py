"""指标归一化单测样例。"""
from app.agents.parser.normalizer import normalize_indicator_name, parse_ref_range


def test_alias_mapping():
    assert normalize_indicator_name("GGT") == "γ-谷氨酰转移酶"
    assert normalize_indicator_name("HDL-C") == "高密度脂蛋白胆固醇"
    # 未命中 → 返回原文
    assert normalize_indicator_name("未知指标X") == "未知指标X"


def test_ref_range_parse():
    assert parse_ref_range("3.5-5.5") == (3.5, 5.5)
    assert parse_ref_range("3.5~5.5") == (3.5, 5.5)
    assert parse_ref_range("<5") == (None, 5.0)
    assert parse_ref_range("≥40") == (40.0, None)
    assert parse_ref_range(None) == (None, None)
