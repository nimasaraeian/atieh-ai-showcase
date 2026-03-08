# scripts/smoke_scoring.py

import sys
from pathlib import Path
import traceback

# -------------------------------------------------
# Ensure project root is in PYTHONPATH
# -------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]  # atieh/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# -------------------------------------------------
# Import scoring function
# -------------------------------------------------
try:
    from app.engine.scoring import calculate_total_score
except Exception:
    print("[IMPORT FAIL] Could not import calculate_total_score")
    traceback.print_exc()
    sys.exit(1)


def main():
    print("Running smoke test for calculate_total_score...\n")

    # ✅ All 4 inputs are required by current signature
    urgency_score = 0.80
    financial_score = 0.70
    availability_score = 0.90
    complexity_fit_score = 0.60

    try:
        total = calculate_total_score(
            urgency_score=urgency_score,
            financial_score=financial_score,
            availability_score=availability_score,
            complexity_fit_score=complexity_fit_score,
        )

        print("[OK] calculate_total_score executed successfully.\n")
        print("Inputs (all clamped to 0..1):")
        print("urgency_score        =", urgency_score)
        print("financial_score      =", financial_score)
        print("availability_score   =", availability_score)
        print("complexity_fit_score =", complexity_fit_score)
        print("\nOutput:")
        print("total_score          =", total)

        # sanity check
        if not (0.0 <= float(total) <= 1.0):
            raise ValueError(f"total_score out of range: {total}")

    except Exception:
        print("\n[FAIL] calculate_total_score crashed.")
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()