"""BM25 分词与检索单测。

中文 BM25 此前按单字切词,常见字淹没判别性术语 → 召回跑偏(实测「肌酐偏高」
召回到肝功能而非肾功能)。改用 CJK 二元组后,这里把「判别性术语应胜出」固化为
回归测试。bm25_search 走真实 ``_index`` 路径(读 jsonl),用 tmp 目录 + monkeypatch
``model_cache_dir`` 离线构造合成库,无需 Milvus / 网络。
"""
from __future__ import annotations

import json

import pytest

from app.rag import bm25
from app.rag.bm25 import bm25_search, tokenize


# ---------- tokenize ----------
def test_tokenize_cjk_bigrams():
    assert tokenize("肌酐偏高") == ["肌酐", "酐偏", "偏高"]


def test_tokenize_keeps_alnum_whole():
    assert tokenize("ALT 升高 35U") == ["alt", "升高", "35u"]


def test_tokenize_single_cjk_char_stays_unigram():
    # 孤立单字(被非中文隔开)退化为单字,短查询仍可命中
    assert tokenize("钾 K") == ["钾", "k"]


def test_tokenize_lowercases():
    assert tokenize("BNP") == ["bnp"]


# ---------- bm25_search end-to-end (synthetic offline index) ----------
@pytest.fixture
def synthetic_index(tmp_path, monkeypatch):
    """写一个合成 KB jsonl 并指向它;返回 collection 名。"""
    bm25_dir = tmp_path / "bm25"
    bm25_dir.mkdir()
    docs = [
        {"doc_id": "kidney", "chunk_id": "kidney#0",
         "text": "血肌酐是评估肾小球滤过功能的核心指标,肌酐偏高提示肾功能下降。", "metadata": {}},
        {"doc_id": "liver", "chunk_id": "liver#0",
         "text": "ALT 丙氨酸氨基转移酶升高说明肝细胞损伤,常见于脂肪肝。", "metadata": {}},
        {"doc_id": "urine", "chunk_id": "urine#0",
         "text": "尿蛋白阳性提示肾小球或肾小管病变,需结合 24 小时尿蛋白定量。", "metadata": {}},
    ]
    (bm25_dir / "medical_kb.jsonl").write_text(
        "\n".join(json.dumps(d, ensure_ascii=False) for d in docs), encoding="utf-8"
    )

    class _S:
        model_cache_dir = str(tmp_path / "models")  # parent → tmp_path, sibling bm25/

    def _get_settings():
        return _S()

    monkeypatch.setattr(bm25, "get_settings", _get_settings)
    bm25.reload_indices()  # 清 lru_cache,强制重读
    yield "medical_kb"
    bm25.reload_indices()


def test_bm25_creatinine_ranks_kidney_first(synthetic_index):
    # 回归核心:判别性术语「肌酐」必须把肾功能文档排到第一,而非肝功能
    hits = bm25_search(synthetic_index, "肌酐偏高说明什么", top_k=3)
    assert hits, "BM25 应有命中"
    assert hits[0]["doc_id"] == "kidney"


def test_bm25_urine_protein_ranks_urine_first(synthetic_index):
    hits = bm25_search(synthetic_index, "尿蛋白阳性是什么原因", top_k=3)
    assert hits and hits[0]["doc_id"] == "urine"


def test_bm25_missing_index_returns_empty(tmp_path, monkeypatch):
    class _S:
        model_cache_dir = str(tmp_path / "nope" / "models")

    def _get_settings():
        return _S()

    monkeypatch.setattr(bm25, "get_settings", _get_settings)
    bm25.reload_indices()
    assert bm25_search("medical_kb", "肌酐", top_k=5) == []
    bm25.reload_indices()
