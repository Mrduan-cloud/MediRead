"""混合检索：BM25 + BGE + RRF。"""
from __future__ import annotations

import time
from collections import defaultdict

from loguru import logger

from app.clients.milvus import search_vectors
from app.core.embeddings import embed_query
from app.rag.bm25 import bm25_search


def rrf_fuse(runs: list[list[dict]], k: int = 60, top_k: int = 20) -> list[dict]:
    scores: dict[str, float] = defaultdict(float)
    doc_map: dict[str, dict] = {}
    for run in runs:
        for rank, doc in enumerate(run):
            key = f"{doc['doc_id']}:{doc['chunk_id']}"
            scores[key] += 1.0 / (k + rank + 1)
            doc_map[key] = doc
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
    return [{**doc_map[k], "rrf_score": s} for k, s in ranked]


async def hybrid_search(collection: str, query: str, top_k: int = 20,
                       filters: dict | None = None) -> list[dict]:
    t0 = time.perf_counter()
    qvec = embed_query(query)
    bm25_run = bm25_search(collection, query, top_k=50)
    vec_run = search_vectors(collection, qvec, top_k=50, expr=None)
    fused = rrf_fuse([bm25_run, vec_run], top_k=top_k)
    logger.debug(
        "hybrid {} q='{}' bm25={} vec={} fused={} cost={:.2f}s",
        collection, query[:30], len(bm25_run), len(vec_run), len(fused),
        time.perf_counter() - t0,
    )
    return fused
