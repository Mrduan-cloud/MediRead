"""检索结果融合 —— Reciprocal Rank Fusion(纯函数,零重依赖,可单测/进 CI)。

从 ``hybrid_retrieval`` 抽出:RRF 与 Milvus / 向量库无关,独立后既可单测,
也能被多路召回(BM25 + 向量 + 未来更多路)复用。
"""
from __future__ import annotations

from collections import defaultdict


def rrf_fuse(runs: list[list[dict]], k: int = 60, top_k: int = 20) -> list[dict]:
    """Reciprocal Rank Fusion。

    每条 run 内对**同一 chunk**(``doc_id:chunk_id``)只记一次贡献,取其在该 run 中
    的最优(最小)排名 —— 否则一条 run 里重复出现的 chunk(检索结果含重复数据时)
    会被多次累加、分数虚高。跨 run 之间才相加(这正是 RRF 的融合本意)。

    Args:
        runs: 多路召回结果,每路是按相关性降序的 ``[{doc_id, chunk_id, ...}]``。
        k: RRF 阻尼常数(标准取 60)。
        top_k: 融合后保留条数。
    """
    scores: dict[str, float] = defaultdict(float)
    doc_map: dict[str, dict] = {}
    for run in runs:
        best_rank: dict[str, int] = {}
        for rank, doc in enumerate(run):
            key = f"{doc['doc_id']}:{doc['chunk_id']}"
            if key not in best_rank or rank < best_rank[key]:
                best_rank[key] = rank
            doc_map.setdefault(key, doc)
        for key, rank in best_rank.items():
            scores[key] += 1.0 / (k + rank + 1)
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
    return [{**doc_map[key], "rrf_score": s} for key, s in ranked]
