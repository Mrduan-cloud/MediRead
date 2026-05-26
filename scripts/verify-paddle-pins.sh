#!/usr/bin/env bash
# Verify that the PaddleOCR + paddlepaddle pins in requirements.txt
# can be resolved cleanly on the current Python interpreter.
#
# Usage:
#   bash scripts/verify-paddle-pins.sh                  # use current python
#   PYTHON=python3.11 bash scripts/verify-paddle-pins.sh # explicit interpreter
#
# Why this script:
#   - paddlepaddle 2.x line maxes out at 2.6.2 and only ships wheels for
#     cp38 / cp39 / cp310 / cp311 / cp312. Python 3.13+ has NO 2.x wheel,
#     so a contributor on 3.13 will silently get paddlepaddle 3.x and
#     hit breaking changes in the OCR pipeline at runtime.
#   - This script catches that mismatch BEFORE the broken install lands.

set -euo pipefail

PYTHON="${PYTHON:-python}"

echo "[1/3] interpreter:"
"$PYTHON" --version

# Bail out early if the interpreter is outside the supported range.
"$PYTHON" - <<'PY'
import sys
major, minor = sys.version_info[:2]
if (major, minor) < (3, 11):
    sys.exit(f"[ERROR] Python {major}.{minor} too old - MediRead requires >=3.11")
if (major, minor) >= (3, 13):
    sys.exit(
        f"[ERROR] Python {major}.{minor} not supported - paddlepaddle 2.x has no "
        f"wheel for cp{major}{minor}. Use 3.11 or 3.12, or wait for the "
        f"PaddleOCR 3.x migration."
    )
print(f"[OK] Python {major}.{minor} is in the supported range (3.11 / 3.12)")
PY

LOG_FILE="${TMPDIR:-/tmp}/mediread-paddle-resolve.log"

echo ""
echo "[2/3] resolving paddleocr / paddlepaddle pins (dry-run, no download)..."
# Pin 应当与 requirements.txt 保持一致。上限收紧在 <2.8.0:2.8+ 移除了
# PaddleOCR(show_log=...) / use_gpu / .ocr(cls=...) 等 ocr.py 当前在用的参数。
"$PYTHON" -m pip install --dry-run \
    "paddleocr>=2.7.3,<2.8.0" \
    "paddlepaddle>=2.6.2,<3.0.0" \
    > "$LOG_FILE" 2>&1 || {
        echo "[ERROR] pip resolve failed - see log:"
        cat "$LOG_FILE"
        exit 1
    }

echo "[OK] pip resolve passed"
echo ""
echo "[3/3] resolved versions:"
# pip 的 "Would install" 行把所有要安装的包合并成一行,从里面挑出 paddle* 的版本
grep -oE "paddleocr-[0-9.]+|paddlepaddle-[0-9.]+" "$LOG_FILE" \
    | sort -u \
    | sed 's/^/      /'

echo ""
echo "[OK] all checks passed - requirements.txt PaddleOCR pin is sane on this interpreter."
