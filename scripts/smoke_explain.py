"""
Smoke test for GET /ai/patient-explain/{patient_id}

Usage:
    python scripts/smoke_explain.py [--base-url http://127.0.0.1:8001] [--patient-id 17155]
"""
import argparse
import json
import sys
import urllib.request
import urllib.error

REQUIRED_KEYS = {
    "patient_id",
    "patient_name",
    "visits_count",
    "completed_count",
    "cancelled_count",
    "last_visit_at",
    "recency_days",
    "predominant_payment_type",
    "total_appointments_last_12_months",
    "history_score",
    "decision_label",
    "recommendation",
}
VALID_LABELS = {"VIP", "STANDARD", "RECALL", "RISK"}


def fetch(url: str) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def ok(msg: str) -> None:
    print(f"  [OK]   {msg}")


def fail(msg: str) -> None:
    print(f"  [FAIL] {msg}")
    sys.exit(1)


def check(condition: bool, msg: str) -> None:
    ok(msg) if condition else fail(msg)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--patient-id", type=int, default=17155)
    args = parser.parse_args()

    url = f"{args.base_url}/ai/patient-explain/{args.patient_id}"
    print(f"\nSmoke test: GET {url}\n")

    try:
        data = fetch(url)
    except urllib.error.HTTPError as exc:
        fail(f"HTTP {exc.code}: {exc.reason}")
    except Exception as exc:
        fail(f"Could not reach server: {exc}")

    print("Response:")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print()

    # structural
    missing = REQUIRED_KEYS - data.keys()
    check(not missing, f"all required keys present (missing: {missing or 'none'})")

    # no unexpected nested objects (response must be flat)
    nested = [k for k, v in data.items() if isinstance(v, dict)]
    check(not nested, f"response is flat — no nested objects (found: {nested or 'none'})")

    # values
    check(data["patient_id"] == args.patient_id, f"patient_id == {args.patient_id}")
    check(isinstance(data["patient_name"], str) and data["patient_name"], "patient_name is non-empty string")

    score = data["history_score"]
    check(isinstance(score, (int, float)) and 0 <= score <= 100, f"history_score in [0, 100] (got {score})")

    label = data["decision_label"]
    check(label in VALID_LABELS, f"decision_label in {VALID_LABELS} (got {label!r})")

    check(isinstance(data["recommendation"], str) and data["recommendation"], "recommendation is non-empty string")

    visits = data["visits_count"]
    completed = data["completed_count"]
    cancelled = data["cancelled_count"]
    check(isinstance(visits, int) and visits >= 0, f"visits_count >= 0 (got {visits})")
    check(isinstance(completed, int) and completed >= 0, f"completed_count >= 0 (got {completed})")
    check(isinstance(cancelled, int) and cancelled >= 0, f"cancelled_count >= 0 (got {cancelled})")
    check(completed + cancelled <= visits, f"completed + cancelled <= visits_count")

    last_12 = data["total_appointments_last_12_months"]
    check(isinstance(last_12, int) and 0 <= last_12 <= visits, f"total_appointments_last_12_months in [0, visits] (got {last_12})")

    # label consistency checks
    if score >= 80:
        check(label == "VIP", f"score={score} >= 80 implies label=VIP (got {label!r})")
    if 50 <= score < 80:
        check(label == "STANDARD", f"score={score} in [50,80) implies label=STANDARD (got {label!r})")

    print("\n[PASS] All checks passed.\n")


if __name__ == "__main__":
    main()
