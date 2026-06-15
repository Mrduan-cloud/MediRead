"""引用守卫单测 —— 纯逻辑,进 CI。每条对应一个「带引用 ≠ 引用为真」的真实失效场景。"""
from app.agents.interpreter.citation_guard import (
    allowed_keys,
    check_field,
    extract_citations,
    guard,
)

_EV = [
    {"doc_id": "liver_function_panel", "chunk_id": "3", "text": "ALT 升高常见于..."},
    {"doc_id": "liver_function_panel", "chunk_id": "5", "text": "GGT 与胆道..."},
]


# ---------- extract_citations ----------
def test_extract_basic_dedup_and_order():
    text = "ALT 偏高 [liver_function_panel:3]，详见 [liver_function_panel:5]，再看 [liver_function_panel:3]。"
    assert extract_citations(text) == ["liver_function_panel:3", "liver_function_panel:5"]


def test_extract_ignores_brackets_without_colon():
    # 参考区间 [10-50] 不是引用(无冒号),不能误判
    assert extract_citations("参考区间 [10-50]，值 55") == []


def test_extract_handles_spacing_and_empty():
    assert extract_citations("[ doc_a : 7 ]") == ["doc_a:7"]
    assert extract_citations("") == []


# ---------- allowed_keys ----------
def test_allowed_keys_builds_set_and_skips_incomplete():
    ev = [*_EV, {"doc_id": "x", "text": "no chunk id"}, {"chunk_id": "9"}]
    assert allowed_keys(ev) == {"liver_function_panel:3", "liver_function_panel:5"}


# ---------- check_field ----------
def test_check_field_all_valid_is_grounded():
    fg = check_field("interpretation", "见 [liver_function_panel:3]", allowed_keys(_EV))
    assert fg.valid == ["liver_function_panel:3"]
    assert fg.hallucinated == []
    assert fg.has_citation and fg.grounded


def test_check_field_hallucinated_breaks_grounding():
    # 有一条真的 + 一条编造的 → 整体不接地(编造引用是医学场景的高危失效)
    fg = check_field(
        "interpretation",
        "见 [liver_function_panel:3] 和 [fabricated_doc:99]",
        allowed_keys(_EV),
    )
    assert fg.valid == ["liver_function_panel:3"]
    assert fg.hallucinated == ["fabricated_doc:99"]
    assert not fg.grounded


def test_check_field_no_citation_not_grounded():
    fg = check_field("interpretation", "ALT 偏高，提示肝细胞受损可能。", allowed_keys(_EV))
    assert not fg.has_citation and not fg.grounded


# ---------- guard ----------
def test_guard_passes_when_required_field_grounded():
    res = guard(
        {"interpretation": "见 [liver_function_panel:3]", "lifestyle": "少饮酒"},
        _EV,
    )
    assert res.grounded
    assert res.ungrounded_fields == []
    assert res.hallucinated == []


def test_guard_fails_on_ungrounded_required_field():
    res = guard({"interpretation": "ALT 偏高，建议复查。"}, _EV)  # 无引用
    assert not res.grounded
    assert res.ungrounded_fields == ["interpretation"]


def test_guard_reports_hallucinations_across_fields():
    res = guard(
        {"interpretation": "见 [liver_function_panel:3]", "lifestyle": "见 [made_up:1]"},
        _EV,
        required=("interpretation", "lifestyle"),
    )
    assert not res.grounded                       # lifestyle 用了编造引用
    assert "lifestyle" in res.ungrounded_fields
    assert res.hallucinated == ["made_up:1"]


def test_guard_missing_required_field_not_grounded():
    # interpretation 整个字段缺失(LLM 没产出该 key)必须判未接地——
    # 不能因 all([]) 把「必填字段缺失」误判为通过。
    res = guard({"lifestyle": "见 [liver_function_panel:3]"}, _EV)  # 无 interpretation
    assert not res.grounded


def test_guard_default_required_is_interpretation_only():
    # lifestyle 未接地不影响整体(默认只要求 interpretation)
    res = guard({"interpretation": "见 [liver_function_panel:5]", "lifestyle": "多运动"}, _EV)
    assert res.grounded
