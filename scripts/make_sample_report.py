"""生成一张脱敏 mock 体检报告 PNG，作 OCR smoke test 的 fixture。

数据完全虚构（无任何真实个人 / 医院信息），仅用于验证 PaddleOCR 链路能跑通。

用法：
    python scripts/make_sample_report.py [输出路径]
默认输出到 tests/fixtures/sample_report.png。

提交进仓库的 PNG 已在 Windows（含微软雅黑）上渲染好中文；脚本同时保留，便于
任何人在装有 CJK 字体的环境里复现。
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# 常见 CJK 字体候选（Windows / Linux / macOS）—— 取第一个存在的。
_FONT_CANDIDATES = (
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/simsun.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/System/Library/Fonts/PingFang.ttc",
)

# 完全虚构的体检数据（含一条 ALT 偏高，便于后续演示风险分级）。
_ROWS = (
    ("项目", "结果", "单位", "参考范围", "提示"),
    ("白细胞 WBC", "6.5", "10^9/L", "3.5-9.5", "正常"),
    ("红细胞 RBC", "4.8", "10^12/L", "4.3-5.8", "正常"),
    ("血红蛋白 Hb", "150", "g/L", "130-175", "正常"),
    ("血小板 PLT", "210", "10^9/L", "125-350", "正常"),
    ("谷丙转氨酶 ALT", "56", "U/L", "9-50", "偏高 ↑"),
    ("空腹血糖 GLU", "5.2", "mmol/L", "3.9-6.1", "正常"),
)


def _load_font(size: int):
    for path in _FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def make_report(out_path: Path) -> Path:
    width, height = 1240, 780
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    title_font = _load_font(42)
    body_font = _load_font(26)

    draw.text((40, 30), "血常规检验报告单（示例 · MOCK）", fill="black", font=title_font)
    draw.text((40, 100), "姓名：张三（测试）   性别：男   年龄：35", fill="black", font=body_font)
    draw.text((40, 140), "医院：示例市人民医院（MOCK）   采样日期：2026-05-20",
              fill="black", font=body_font)

    col_x = (40, 360, 560, 760, 1040)
    top = 210
    row_h = 70
    for r, row in enumerate(_ROWS):
        y = top + r * row_h
        for c, cell in enumerate(row):
            draw.text((col_x[c], y), cell, fill="black", font=body_font)
        line_y = y + row_h - 14
        draw.line([(40, line_y), (width - 40, line_y)], fill=(200, 200, 200), width=1)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="PNG")
    return out_path


def main() -> None:
    default = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "sample_report.png"
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else default
    saved = make_report(out)
    print(f"wrote {saved} ({saved.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
