"""OCR 端到端 smoke test —— 用真实 PaddleOCR 跑一张 mock 体检报告图，证明链路跑得通。

标记 `@pytest.mark.ocr`，**默认 deselect**（见 pyproject `addopts = -m 'not ocr'`），
因为它需要真实 paddleocr + paddlepaddle 栈（Python 3.11/3.12，约 500MB 权重）。
显式开启：`pytest -m ocr`（在 paddle 能正常导入的环境）。

历史问题（已修）：`import paddle` 曾在镜像里直接段错误（`free(): invalid pointer`
/ SIGSEGV）。根因是未 pin 的 Cython 漂到 3.x，与 paddlepaddle 2.6.2 的 C++ 初始化
不兼容；已在 requirements.txt pin `Cython==0.29.37` 修复，paddle 现可正常导入 + 实例化。

仍需联网：PaddleOCR 首次运行要下载 PP-OCR 模型（det/rec/cls，约数十 MB）。模型
下载失败（网络受限 / CDN 不可达）≠ 代码缺陷，本测试会 `skip` 而非 fail（与 arxiv
live 测试遇限流 skip 同理）。生产应在镜像构建期预置模型。

fixture 图：`tests/fixtures/sample_report.png`，由 `scripts/make_sample_report.py`
生成，数据完全虚构（无任何真实个人 / 医院信息）。
"""
from pathlib import Path

import pytest

pytestmark = pytest.mark.ocr

_FIXTURE = Path(__file__).parent / "fixtures" / "sample_report.png"


def test_fixture_image_exists():
    assert _FIXTURE.exists(), "缺少 fixture，请先跑 python scripts/make_sample_report.py"


_DOWNLOAD_ERR_HINTS = (
    "connection", "max retries", "timed out", "timeout", "failed to establish",
    "ssl", "temporary failure", "name resolution", "download",
)


def test_ocr_image_extracts_known_text():
    from app.agents.parser.ocr import ocr_image

    # 首次运行需联网下载 PP-OCR 模型；下载失败(网络/CDN)≠ 代码缺陷 → skip 而非 fail。
    try:
        results = ocr_image(_FIXTURE.read_bytes())
    except Exception as e:
        msg = str(e).lower()
        if any(h in msg for h in _DOWNLOAD_ERR_HINTS):
            pytest.skip(f"PP-OCR 模型下载失败(网络受限),跳过真实 OCR：{type(e).__name__}: {e}")
        raise
    assert results, "OCR 应至少识别出若干文本块"

    joined = "".join(r["text"] for r in results)
    # OCR 不保证逐字精确，命中关键 token 之一即视为链路通。
    hits = [t for t in ("白细胞", "WBC", "血红蛋白", "血常规", "ALT", "报告") if t in joined]
    assert hits, f"应识别出体检报告关键字，实际识别前 200 字：{joined[:200]}"

    # 每个结果块结构正确（text / confidence / bbox）。
    for r in results:
        assert {"text", "confidence", "bbox"} <= set(r)
        assert 0.0 <= r["confidence"] <= 1.0
        assert len(r["bbox"]) == 4
