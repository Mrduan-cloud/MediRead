"""interpreter 医学知识检索的真实管线评测(需 Milvus + KB + BGE/重排权重)。

固化 6/19(BM25+BGE 多路召回 + RRF)与 6/20(Cross-Encoder 精排 top-20→top-5):
- **召回完整性**:hybrid_search 的 recall@5 ≥ 0.8(多路召回把对的面板捞进来);
- **精排不丢窗口**:Cross-Encoder 重排到 top-5 后 recall@5 仍 ≥ 0.8 —— interpreter 取
  重排 top-4 当证据,只要相关面板仍在窗口内,解读就拿得到。

**实测发现(诚实记录,故不断言"精排提升 top-1")**:在当前 **6 文档**种子 KB 上,
RRF 已把 6 个粗粒度面板分得很开,Cross-Encoder 反而把 top-1 文档准确率从 0.909
拉到 0.727(`甘油三酯高`→误判 liver、`CEA 升高`→误判 blood)。即:**小而粗的 KB 上
精排是负增益**,其价值要等 KB 规模化(同面板多 chunk、需细粒度排序)才体现。
本测试因此只固化「召回完整 + 精排不丢相关文档」,top-1 增益留待 KB 扩充后复评
(见 spawn 的跟进任务)。不在 CI allowlist;Milvus 不可用/库未灌时自动 skip。
跑法:栈起好 + 灌过 medical_kb 后 `pytest tests/test_interpreter_retrieval_live.py -v`。
"""
from __future__ import annotations

import asyncio

import pytest

from app.evaluation.retrieval_eval import recall_at_k

# gold:指标/症状查询 → 应命中的检验面板文档。覆盖全部 6 个面板。
GOLD: list[tuple[str, set[str]]] = [
    ("尿蛋白阳性是什么原因", {"urinalysis"}),
    ("尿潜血阳性怎么回事", {"urinalysis"}),
    ("血肌酐升高说明什么", {"kidney_function_panel"}),
    ("eGFR 下降是慢性肾病吗", {"kidney_function_panel"}),
    ("ALT 丙氨酸氨基转移酶偏高", {"liver_function_panel"}),
    ("GGT 升高的意义", {"liver_function_panel"}),
    ("白细胞计数偏高提示什么", {"blood_routine"}),
    ("血红蛋白偏低是贫血吗", {"blood_routine"}),
    ("空腹血糖偏高", {"lipid_glucose_panel"}),
    ("甘油三酯高需要注意什么", {"lipid_glucose_panel"}),
    ("CEA 癌胚抗原升高", {"tumor_markers_panel"}),
]


def _guide_ready() -> bool:
    try:
        from pymilvus import Collection, utility

        from app.clients.milvus import _alias, connect_milvus
        from app.config import get_settings

        connect_milvus()
        name = get_settings().milvus_collection_medical
        if not utility.has_collection(name, using=_alias()):
            return False
        col = Collection(name, using=_alias())
        col.load()
        return col.num_entities >= 6
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _guide_ready(), reason="需要在线 Milvus + 已灌 medical_kb"
)


def _hybrid_docs(query: str) -> list[str]:
    """多路召回(BM25+BGE+RRF)的排序 doc_id —— 精排**前**。"""
    from app.config import get_settings
    from app.rag.hybrid_retrieval import hybrid_search

    s = get_settings()
    chunks = asyncio.run(hybrid_search(collection=s.milvus_collection_medical,
                                       query=query, top_k=20))
    return [c["doc_id"] for c in chunks]


def _reranked_docs(query: str) -> list[str]:
    """Cross-Encoder 精排(top-20 → top-5)后的排序 doc_id —— 精排**后**。"""
    from app.config import get_settings
    from app.rag.hybrid_retrieval import hybrid_search
    from app.rag.reranker import cross_encoder_rerank

    s = get_settings()
    chunks = asyncio.run(hybrid_search(collection=s.milvus_collection_medical,
                                       query=query, top_k=20))
    return [c["doc_id"] for c in cross_encoder_rerank(query, chunks, top_k=5)]


def test_hybrid_recall_at_5_meets_bar():
    """6/19:多路召回(BM25+BGE+RRF)recall@5 ≥ 0.8。"""
    recall = recall_at_k(GOLD, _hybrid_docs, k=5)
    assert recall >= 0.8, f"hybrid recall@5={recall:.3f} < 0.8"


def test_rerank_preserves_recall_at_5():
    """6/20:Cross-Encoder 精排到 top-5 后,相关面板仍在窗口内(recall@5 ≥ 0.8)。

    interpreter 用精排 top-4 当证据 —— 精排可以重排次序,但不能把相关面板挤出窗口。
    (top-1 增益不在此断言:见模块 docstring 的实测说明,小种子 KB 上精排负增益。)
    """
    recall = recall_at_k(GOLD, _reranked_docs, k=5)
    assert recall >= 0.8, f"post-rerank recall@5={recall:.3f} < 0.8"
