"""RRF 融合单测 —— 纯函数,零重依赖,CI 可跑。

重点回归:run 内重复 chunk(检索结果含重复数据时)不得被多次累加导致分数虚高 ——
这正是「Milvus collection 反复灌库堆积重复 chunk → RRF 把重复项顶到前面 →
召回污染」那个 bug 的纯逻辑防线。
"""
from __future__ import annotations

from app.rag.fusion import rrf_fuse


def _doc(d: str, c: int) -> dict:
    return {"doc_id": d, "chunk_id": f"{d}#{c}", "text": f"{d}-{c}"}


def test_basic_fusion_prefers_cross_run_agreement():
    # A#0 两路都靠前 → 应排第一
    bm25 = [_doc("A", 0), _doc("B", 0), _doc("C", 0)]
    vec = [_doc("A", 0), _doc("D", 0)]
    out = rrf_fuse([bm25, vec], top_k=10)
    assert out[0]["doc_id"] == "A"
    assert {o["chunk_id"] for o in out} == {"A#0", "B#0", "C#0", "D#0"}


def test_duplicate_chunk_in_one_run_counted_once():
    """同一 run 里 A#0 出现 3 次(重复数据)不得被累加成 3 倍分数。"""
    dup_run = [_doc("A", 0), _doc("A", 0), _doc("A", 0), _doc("B", 0)]
    clean_run = [_doc("B", 0), _doc("C", 0)]
    out = rrf_fuse([dup_run, clean_run], top_k=10)
    # B 跨两路(dup 里 rank3 + clean 里 rank0),A 仅单路一次 → B 必须压过 A
    score = {o["chunk_id"]: o["rrf_score"] for o in out}
    assert score["B#0"] > score["A#0"], score
    # A 的分数等于单次 rank0 贡献 1/61(没有被 ×3)
    assert abs(score["A#0"] - 1.0 / 61) < 1e-9


def test_duplicate_takes_best_rank():
    # A 在 run 里既出现在 rank0 也 rank5 → 取最优 rank0
    run = [_doc("A", 0), _doc("X", 0), _doc("Y", 0), _doc("Z", 0), _doc("W", 0), _doc("A", 0)]
    out = rrf_fuse([run], top_k=10)
    score = {o["chunk_id"]: o["rrf_score"] for o in out}
    assert abs(score["A#0"] - 1.0 / 61) < 1e-9  # rank0,而非 rank5 的 1/66


def test_top_k_truncation():
    run = [_doc("A", i) for i in range(10)]
    assert len(rrf_fuse([run], top_k=3)) == 3


def test_empty_runs():
    assert rrf_fuse([]) == []
    assert rrf_fuse([[], []]) == []
