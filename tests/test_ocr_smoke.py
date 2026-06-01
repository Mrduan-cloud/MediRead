"""OCR 端到端 smoke test —— 用真实 PaddleOCR 跑一张 mock 体检报告图，证明链路跑得通。

标记 `@pytest.mark.ocr`，**默认 deselect**（见 pyproject `addopts = -m 'not ocr'`），
因为它需要真实 paddleocr + paddlepaddle 栈（Python 3.11/3.12，约 500MB 权重）。
显式开启：`pytest -m ocr`（在 paddle 能正常导入的环境）。

已知限制：当前 `mediread:test` 镜像虽能 build 成功，但 `import paddle` 在该运行时
会 core dump（`free(): invalid pointer`，非 AVX 缺失——CPU 支持 avx512）。这是
paddlepaddle 2.6.2 wheel 的运行时不兼容，留待 W11 OCR/部署收尾时换可导入的 paddle
构建（或升 3.x / GPU）。在此之前真实 OCR 验证需在 paddle 可导入的机器上跑。

fixture 图：`tests/fixtures/sample_report.png`，由 `scripts/make_sample_report.py`
生成，数据完全虚构（无任何真实个人 / 医院信息）。
"""
from pathlib import Path

import pytest

pytestmark = pytest.mark.ocr

_FIXTURE = Path(__file__).parent / "fixtures" / "sample_report.png"


def test_fixture_image_exists():
    assert _FIXTURE.exists(), "缺少 fixture，请先跑 python scripts/make_sample_report.py"


def test_ocr_image_extracts_known_text():
    from app.agents.parser.ocr import ocr_image

    results = ocr_image(_FIXTURE.read_bytes())
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
