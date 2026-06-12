"""一键初始化医学知识库。

走 ``ingest_markdown_dir`` 完整链路(而非裸 split+upsert):
- 每个 chunk 带 ``path`` 等 metadata(可溯源到具体 KB 文件);
- 同步落 BM25 倒排源 jsonl —— **混合检索(BM25+向量 RRF)的 BM25 路靠它**,
  漏掉的话 hybrid_search 会退化成纯向量检索。

用法(容器内):
    python scripts/init_kb.py --source app/data/kb
"""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from app.rag.ingestion import ingest_markdown_dir


async def main(source_dir: Path, collection: str) -> None:
    n = await ingest_markdown_dir(
        source_dir, collection=collection, base_metadata={"source": "seed_kb"}
    )
    print(f"upserted {n} chunks into {collection} (with metadata + BM25 jsonl)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--collection", default="medical_kb")
    args = parser.parse_args()
    asyncio.run(main(args.source, args.collection))
