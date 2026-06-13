"""检索/精排评测指标单测 —— 纯函数(stub retriever),CI 可跑。"""
from __future__ import annotations

from app.evaluation.retrieval_eval import mrr, recall_at_k, top1_accuracy

# 模拟两套检索顺序:rrf(未精排,相关文档靠后)vs rerank(精排,相关文档提前)
_GOLD = [("q1", {"A"}), ("q2", {"B"})]
_RRF = {"q1": ["X", "Y", "A", "Z"], "q2": ["B", "X", "Y"]}
_RERANK = {"q1": ["A", "X", "Y", "Z"], "q2": ["B", "X", "Y"]}


def _retr(table):
    return lambda q: table[q]


def test_recall_at_k_cutoff() -> None:
    # k=2:q1 的 A 在第 3 位(漏),q2 的 B 在第 1 位(中)→ (0+1)/2 = 0.5
    assert recall_at_k(_GOLD, _retr(_RRF), k=2) == 0.5
    # k=3:A 进来了 → 1.0
    assert recall_at_k(_GOLD, _retr(_RRF), k=3) == 1.0


def test_recall_multi_relevant_partial() -> None:
    gold = [("q", {"A", "B"})]
    assert recall_at_k(gold, lambda _q: ["A", "X", "Y"], k=3) == 0.5  # 命中 1/2


def test_recall_skips_empty_relevant() -> None:
    gold = [("q1", set()), ("q2", {"B"})]
    assert recall_at_k(gold, lambda _q: ["B"], k=5) == 1.0  # 空相关集跳过


def test_top1_accuracy_distinguishes_rerank_gain() -> None:
    # rrf:q1 top-1=X(错)、q2 top-1=B(对)→ 0.5;rerank:两者 top-1 都对 → 1.0
    assert top1_accuracy(_GOLD, _retr(_RRF)) == 0.5
    assert top1_accuracy(_GOLD, _retr(_RERANK)) == 1.0


def test_mrr_rewards_higher_rank() -> None:
    # rrf:q1 A 在第3位(1/3)、q2 B 第1位(1)→ (1/3+1)/2 = 0.667;rerank 两者第1 → 1.0
    assert mrr(_GOLD, _retr(_RRF)) == (1 / 3 + 1) / 2
    assert mrr(_GOLD, _retr(_RERANK)) == 1.0


def test_mrr_zero_when_outside_k() -> None:
    assert mrr([("q", {"A"})], lambda _q: ["X", "Y", "A"], k=2) == 0.0  # A 在 k 外


def test_empty_gold_returns_zero() -> None:
    assert recall_at_k([], lambda _q: ["A"]) == 0.0
    assert top1_accuracy([], lambda _q: ["A"]) == 0.0
    assert mrr([], lambda _q: ["A"]) == 0.0
