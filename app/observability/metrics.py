"""Prometheus 指标 — 暴露在 /metrics。"""
from __future__ import annotations

from fastapi import Request
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

llm_requests = Counter("mediread_llm_requests_total", "LLM 请求次数", ["model", "status"])
llm_latency = Histogram("mediread_llm_latency_seconds", "LLM 单次请求耗时", ["model"],
                       buckets=(0.5, 1, 2, 5, 10, 30, 60, 120))
ocr_latency = Histogram("mediread_ocr_latency_seconds", "OCR 单页耗时", ["format"],
                       buckets=(0.5, 1, 2, 5, 10, 30))
agent_invocations = Counter("mediread_agent_invocations_total", "Agent 调用次数", ["agent", "outcome"])


async def metrics_endpoint(request: Request) -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
