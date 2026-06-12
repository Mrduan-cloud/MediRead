"""轻量内存 BM25。"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from rank_bm25 import BM25Okapi

from app.config import get_settings

# 拆出「连续字母数字串」与「连续中文串」两类 run,分别成词
_RUN_RE = re.compile(r"[a-z0-9]+|[一-鿿]+")


def tokenize(text: str) -> list[str]:
    """分词:字母数字整体成词;中文按 **二元组(bigram)** 切。

    旧实现按单字切中文 —— "肌酐偏高说明什么" → 单字,常见字(的/是/说/明/什/么)
    在每篇文档都出现、淹没判别性字(肌/酐),导致 BM25 召回严重跑偏。
    改用 CJK 二元组(ES cjk_bigram 同款):连续中文按相邻两字重叠成词
    ("肌酐偏高" → 肌酐/酐偏/偏高),判别性术语("肌酐")成为强匹配信号;
    长度 1 的孤立中文 run 退化为单字,保证短查询仍可命中。零依赖、无需 jieba。
    """
    tokens: list[str] = []
    for m in _RUN_RE.finditer(text.lower()):
        run = m.group(0)
        if run[0].isascii():
            tokens.append(run)
        elif len(run) == 1:
            tokens.append(run)
        else:
            tokens.extend(run[i:i + 2] for i in range(len(run) - 1))
    return tokens


@lru_cache(maxsize=8)
def _index(collection: str) -> tuple[BM25Okapi, list[dict]]:
    s = get_settings()
    path = Path(s.model_cache_dir).parent / "bm25" / f"{collection}.jsonl"
    if not path.exists():
        return BM25Okapi([["__empty__"]]), []
    docs: list[dict] = []
    tokens: list[list[str]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            docs.append(d)
            tokens.append(tokenize(d["text"]))
    return BM25Okapi(tokens), docs


def bm25_search(collection: str, query: str, top_k: int = 50) -> list[dict]:
    bm25, docs = _index(collection)
    if not docs:
        return []
    scores = bm25.get_scores(tokenize(query))
    ranked = sorted(
        ((s, d) for s, d in zip(scores, docs, strict=True) if s > 0),
        key=lambda x: x[0], reverse=True,
    )[:top_k]
    return [
        {"doc_id": d["doc_id"], "chunk_id": d["chunk_id"], "text": d["text"],
         "metadata": d.get("metadata", {}), "bm25_score": float(s)}
        for s, d in ranked
    ]


def reload_indices() -> None:
    _index.cache_clear()
