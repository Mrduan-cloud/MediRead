"""端到端 demo：颁发 JWT → 解读 Demo 报告 → 打印 4 级风险与就医建议。

用法（API 已起来）：
    python -m scripts.demo --base-url http://localhost:8000 --user demo-001
"""
from __future__ import annotations

import argparse
import asyncio
import json

import httpx

from app.auth.jwt import create_access_token


async def run(base_url: str, user: str, report_id: str) -> None:
    token = create_access_token(user)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(base_url=base_url, headers=headers, timeout=180) as client:
        print("== /ready ==")
        r = await client.get("/ready")
        print(r.status_code, r.text[:200])

        print("\n== /api/interpret/{report_id} (使用 seed 出的 demo 报告) ==")
        r = await client.post(f"/api/interpret/{report_id}")
        if r.status_code != 200:
            print(r.status_code, r.text[:500])
            return
        out = r.json()
        print(f"联合信号：{out.get('joint_signals')}")
        for it in out.get("interpretations", []):
            print(f"\n--- {it['indicator']} = {it['value']} ({it.get('ref_range')}) ---")
            print(f"  风险：{it['risk_level']} · 就医：{it['triage']} · 危急值：{it.get('is_critical')}")
            print(f"  解读：{it.get('interpretation', '')[:150]}")
            print(f"  生活：{it.get('lifestyle', '')[:150]}")
            print(f"  引用：{it.get('citations', [])[:3]}")

        print("\n== /api/history/series ==")
        r = await client.get("/api/history/series")
        s = r.json().get("series", {})
        print(json.dumps({k: len(v) for k, v in s.items()}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--user", default="demo-001")
    parser.add_argument("--report-id", default="demo-report-001")
    args = parser.parse_args()
    asyncio.run(run(args.base_url, args.user, args.report_id))
