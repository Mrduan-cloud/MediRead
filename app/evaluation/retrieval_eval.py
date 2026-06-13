"""检索/精排评测指标 —— 注入式纯函数(无重依赖,可单测 / 进 CI)。

真实管线(BM25 + BGE + RRF + Cross-Encoder)依赖 Milvus / sentence-transformers /
FlagReranker,故指标实现为**注入式**:传入 ``retriever(query) -> 排序后的 doc_id 列表``
即可。CI 用确定性 stub 验证指标算法;真实召回/精排增益由集成测试用真 retriever 跑
(见 tests/test_interpreter_retrieval_live.py)。

- ``recall_at_k``:相关文档落在 top-k 的比例(衡量多路召回的**完整性**)。
- ``top1_accuracy``:top-1 命中相关文档的比例(衡量排序/精排的**准确性**)。
- ``mrr``:平均倒数排名(综合排序质量,精排增益看得见)。
"""
from __future__ import annotations

from collections.abc import Callable

Retriever = Callable[[str], list[str]]
Gold = list[tuple[str, set[str]]]


def recall_at_k(gold: Gold, retriever: Retriever, k: int = 5) -> float:
    """recall@k = 各 query 的 |top-k ∩ 相关| / |相关| 的均值。"""
    scores: list[float] = []
    for query, relevant in gold:
        if not relevant:
            continue
        topk = set(retriever(query)[:k])
        scores.append(len(topk & relevant) / len(relevant))
    return sum(scores) / len(scores) if scores else 0.0


def top1_accuracy(gold: Gold, retriever: Retriever) -> float:
    """top-1 doc 命中相关集合的 query 占比。"""
    if not gold:
        return 0.0
    hit = 0
    for query, relevant in gold:
        ranked = retriever(query)
        if ranked and ranked[0] in relevant:
            hit += 1
    return hit / len(gold)


def mrr(gold: Gold, retriever: Retriever, k: int = 10) -> float:
    """Mean Reciprocal Rank:第一个相关文档排名的倒数,top-k 内无相关记 0。"""
    if not gold:
        return 0.0
    total = 0.0
    for query, relevant in gold:
        ranked = retriever(query)[:k]
        rr = 0.0
        for rank, doc in enumerate(ranked, start=1):
            if doc in relevant:
                rr = 1.0 / rank
                break
        total += rr
    return total / len(gold)
