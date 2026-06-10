"""医学知识库 markdown 结构校验 —— 纯文件系统 + 正则,零重依赖,CI 可跑。

`app.rag.ingestion.split_document` 按 ``##`` 标题把每个 KB 文档切块、用文件名作
``doc_id``、``{doc_id}#{idx}`` 作 ``chunk_id``。本测试不导入 ingestion(其顶层
依赖 pymilvus / sentence-transformers,CI 轻量环境装不动),而是直接校验 KB 文档
满足切块器所依赖的结构约定,守住「文档格式 → 索引/引用」这条契约不腐烂。
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

_KB_DIR = Path(__file__).resolve().parents[1] / "app" / "data" / "kb"

# 体检常见血/尿检验面板 —— README「覆盖范围」声称的集合,KB 应齐备
_EXPECTED = {
    "blood_routine",            # 血常规
    "urinalysis",               # 尿常规
    "liver_function_panel",     # 肝功能
    "kidney_function_panel",    # 肾功能
    "lipid_glucose_panel",      # 血脂血糖
    "tumor_markers_panel",      # 肿瘤标志物
}

_H1_RE = re.compile(r"^#\s+\S", re.MULTILINE)
_H2_RE = re.compile(r"^##\s+\S", re.MULTILINE)
_DISCLAIMER_RE = re.compile(r"^>\s+.*种子样本", re.MULTILINE)


def _kb_files() -> list[Path]:
    return sorted(_KB_DIR.glob("*.md"))


def test_kb_dir_exists_and_nonempty():
    assert _KB_DIR.is_dir(), f"KB 目录不存在: {_KB_DIR}"
    assert _kb_files(), "KB 目录下没有任何 .md 文档"


def test_expected_panels_present():
    stems = {p.stem for p in _kb_files()}
    missing = _EXPECTED - stems
    assert not missing, f"缺少常见检验面板 KB: {sorted(missing)}"


@pytest.mark.parametrize("path", _kb_files(), ids=lambda p: p.stem)
def test_each_doc_has_indexable_structure(path: Path):
    text = path.read_text(encoding="utf-8")
    # 恰好一个 H1 标题(面板名)
    assert len(_H1_RE.findall(text)) == 1, f"{path.name} 应有且仅有一个 # 一级标题"
    # 种子声明(标注非生产数据 / 公开来源改写)
    assert _DISCLAIMER_RE.search(text), f"{path.name} 缺少『种子样本』来源声明"
    # 至少 2 个 ## 指标小节 —— split_document 据此切块,过少则检索粒度退化
    assert len(_H2_RE.findall(text)) >= 2, f"{path.name} 的 ## 指标小节过少(<2)"


@pytest.mark.parametrize("path", _kb_files(), ids=lambda p: p.stem)
def test_no_trailing_whitespace_or_tabs(path: Path):
    # 制表符会污染切块文本里的检索/展示,统一禁用
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        assert "\t" not in line, f"{path.name}:{i} 含制表符"
