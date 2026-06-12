"""混合检索：BM25 + BGE + RRF。"""
from __future__ import annotations

import time

from loguru import logger

from app.clients.milvus import search_vectors
from app.core.embeddings import embed_query
from app.rag.bm25 import bm25_search
from app.rag.fusion import rrf_fuse


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
