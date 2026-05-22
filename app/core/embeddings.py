"""BGE Embedding + Cross-Encoder Reranker — 懒加载，本地缓存。"""
from __future__ import annotations

from functools import lru_cache
from typing import Sequence

from loguru import logger

from app.config import get_settings


@lru_cache(maxsize=1)
def _embedder():
    from sentence_transformers import SentenceTransformer

    s = get_settings()
    logger.info("loading embedding model {} ...", s.embedding_model)
    return SentenceTransformer(s.embedding_model, cache_folder=s.model_cache_dir, device="cpu")


@lru_cache(maxsize=1)
def _reranker():
    from FlagEmbedding import FlagReranker

    s = get_settings()
    logger.info("loading reranker {} ...", s.reranker_model)
    return FlagReranker(s.reranker_model, use_fp16=False)


def embed_texts(texts: Sequence[str]) -> list[list[float]]:
    if not texts:
        return []
    vecs = _embedder().encode(
        list(texts), batch_size=32, normalize_embeddings=True, show_progress_bar=False,
    )
    return [v.tolist() for v in vecs]


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]


def rerank(query: str, candidates: list[dict], top_k: int = 8) -> list[dict]:
    if not candidates:
        return []
    pairs = [(query, c["text"]) for c in candidates]
    scores = _reranker().compute_score(pairs)
    if isinstance(scores, float):
        scores = [scores]
    out = [{**c, "rerank_score": float(s)} for c, s in zip(candidates, scores)]
    out.sort(key=lambda x: x["rerank_score"], reverse=True)
    return out[:top_k]
