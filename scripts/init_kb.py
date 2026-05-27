"""一键初始化医学知识库。"""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from app.rag.ingestion import embed_and_upsert, split_document


async def main(source_dir: Path, collection: str) -> None:
    chunks = []
    for p in source_dir.glob("**/*.md"):
        chunks.extend(split_document(doc_id=p.stem, content=p.read_text(encoding="utf-8")))
    n = await embed_and_upsert(chunks, collection=collection)
    print(f"upserted {n} chunks into {collection}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--collection", default="medical_kb")
    args = parser.parse_args()
    asyncio.run(main(args.source, args.collection))
