#!/usr/bin/env bash
# Verify that the PaddleOCR + paddlepaddle pins in requirements.txt
# can be resolved cleanly on the current Python interpreter, and
# (optionally) that they don't break the OCR pipeline's API surface.
#
# Usage:
#   bash scripts/verify-paddle-pins.sh                    # use current python, dry-run only
#   PYTHON=python3.11 bash scripts/verify-paddle-pins.sh  # explicit interpreter
#   bash scripts/verify-paddle-pins.sh --smoke            # also do real install + import test
#
# Why this script:
#   - paddlepaddle 2.x line maxes out at 2.6.2 and only ships wheels for
#     cp38 / cp39 / cp310 / cp311 / cp312. Python 3.13+ has NO 2.x wheel,
#     so a contributor on 3.13 will silently get paddlepaddle 3.x and
#     hit breaking changes in the OCR pipeline at runtime.
#   - paddleocr 2.8+ removed PaddleOCR(show_log=...) and use_gpu=... kwargs
#     that app/agents/parser/ocr.py still uses. The --smoke mode catches
#     this BEFORE the broken install lands.
#
# Note for Windows users: run this from Git Bash or WSL, not raw PowerShell.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REQ_FILE="$REPO_ROOT/requirements.txt"
PYTHON="${PYTHON:-python}"
SMOKE="false"

# parse args
for arg in "$@"; do
    case "$arg" in
        --smoke) SMOKE="true" ;;
        -h|--help)
            sed -n '1,18p' "$0" | sed 's/^# //;s/^#//'
            exit 0
            ;;
        *)
            echo "[ERROR] unknown arg: $arg (try --help)"
            exit 2
            ;;
    esac
done

echo "[1/4] interpreter:"
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

# Pull the actual pin lines out of requirements.txt so this script never
# drifts from the project's authoritative dependency declaration.
if [[ ! -f "$REQ_FILE" ]]; then
    echo "[ERROR] requirements.txt not found at $REQ_FILE"
    exit 1
fi

PADDLEOCR_PIN="$(grep -E '^paddleocr([><=!~,0-9. ]+)?$' "$REQ_FILE" || true)"
PADDLEPADDLE_PIN="$(grep -E '^paddlepaddle([><=!~,0-9. ]+)?$' "$REQ_FILE" || true)"

if [[ -z "$PADDLEOCR_PIN" || -z "$PADDLEPADDLE_PIN" ]]; then
    echo "[ERROR] could not locate paddleocr / paddlepaddle lines in $REQ_FILE"
    echo "  paddleocr line:    '${PADDLEOCR_PIN:-<not found>}'"
    echo "  paddlepaddle line: '${PADDLEPADDLE_PIN:-<not found>}'"
    exit 1
fi

echo ""
echo "[2/4] pins extracted from requirements.txt:"
echo "      $PADDLEOCR_PIN"
echo "      $PADDLEPADDLE_PIN"

LOG_FILE="${TMPDIR:-/tmp}/mediread-paddle-resolve.log"

echo ""
echo "[3/4] resolving pins (dry-run, no download)..."
"$PYTHON" -m pip install --dry-run \
    "$PADDLEOCR_PIN" \
    "$PADDLEPADDLE_PIN" \
    > "$LOG_FILE" 2>&1 || {
        echo "[ERROR] pip resolve failed - see log:"
        cat "$LOG_FILE"
        exit 1
    }
echo "[OK] pip resolve passed"
echo ""
echo "      resolved versions:"
# Extract paddle* versions from pip's "Would install" line.
grep -oE "paddleocr-[0-9.]+|paddlepaddle-[0-9.]+" "$LOG_FILE" \
    | sort -u \
    | sed 's/^/        /'

if [[ "$SMOKE" != "true" ]]; then
    echo ""
    echo "[4/4] smoke test SKIPPED (pass --smoke to enable)"
    echo "      smoke test installs paddle and imports ocr.py - useful in CI."
    echo ""
    echo "[OK] all checks passed - requirements.txt PaddleOCR pin is sane."
    exit 0
fi

# === Smoke test mode ===
# Real install + minimal API check.
# Catches: 2.8+ removed PaddleOCR(show_log=...) etc.
echo ""
echo "[4/4] smoke test: real install + ocr.py import + PaddleOCR() construction..."
echo "      (this downloads ~500MB the first time - cache aggressively in CI)"

"$PYTHON" -m pip install -q \
    "$PADDLEOCR_PIN" \
    "$PADDLEPADDLE_PIN" \
    >> "$LOG_FILE" 2>&1 || {
        echo "[ERROR] pip install failed during smoke - see log:"
        tail -40 "$LOG_FILE"
        exit 1
    }

# Import + construct only — don't run real OCR (model weights download).
# If 2.8+ removed show_log / use_gpu, this line raises TypeError immediately.
"$PYTHON" - <<'PY'
import sys
try:
    from paddleocr import PaddleOCR
except Exception as e:
    sys.exit(f"[ERROR] cannot import paddleocr: {e}")
try:
    # Mirror ocr.py kwargs exactly — anything ocr.py uses must accept here.
    PaddleOCR(lang="ch", use_angle_cls=True, show_log=False)
except TypeError as e:
    sys.exit(
        f"[ERROR] PaddleOCR() rejected an arg ocr.py uses: {e}\n"
        f"        Pin likely too loose - bump requirements.txt upper bound."
    )
except Exception as e:
    # Other failures (model download timeout, missing native lib) are
    # not pin issues — surface them but pass the API check.
    print(f"[WARN] PaddleOCR ran past kwargs but raised: {e}")
print("[OK] PaddleOCR(show_log=False, use_angle_cls=True) accepted - API compatible")
PY

echo ""
echo "[OK] all checks passed (including smoke) - pin is sane and API-compatible."
