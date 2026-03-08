"""
Financial payments ingestion pipeline.

Reads payments_<YEAR>_full.xlsx files from data/inputs/payments/ and loads
every row into stg_payments with both raw and normalised fields.

Column layout (103-column report from the clinic billing system):
  'نام بيمار'               – patient name  (may include record ID in parens)
  'موبايل'                   – phone
  'نام خدمت'                 – service name
  'سازمان |بيمه گر بيمار'   – insurer / payer  (may include pct and code)
  'تاريخ پذيرش'              – Shamsi date of admission / appointment
  'سهم بيمار'                – patient share amount
  'سهم سازمان'               – insurer share amount
  'خالص دريافتي'             – net received

Insurer field format examples:
  'البرز(30 %)(19)'   → insurer_name_norm='البرز', payer_source='insurance', pct=30  (detected)
  'آزاد(1)'          → insurer_name_norm='آزاد',   payer_source='cash',      pct=100
  'تامين اجتماعي(30 %)' → insurer_name_norm='تامین اجتماعی', payer_source='insurance', pct=30

Rules:
  - insurer_name_norm  = text before the first '('  (stripped, Arabic→Persian)
  - payer_source_norm:
      'آزاد' / 'ازاد'  → 'cash'
      non-empty name    → 'insurance'
      empty             → 'unknown'
  - patient_share_pct:
      explicit (NN %)   → NN          (pct_detected=1)
      insurance default → 30          (pct_detected=0)
      cash              → 100         (pct_detected=0)
  - Numeric-only codes like (1) or (19) are ignored.
"""

import json
import logging
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from app.importers.common.normalize import normalize_text, normalize_digits

logger = logging.getLogger(__name__)

# ── paths ──────────────────────────────────────────────────────────────────────
PAYMENTS_DIR  = Path(__file__).parent.parent.parent / "data" / "inputs" / "payments"
FILE_PATTERN  = re.compile(r"^payments_(\d{4})_full\.xlsx$", re.IGNORECASE)
BATCH_SIZE    = 500


# ── header normalisation ───────────────────────────────────────────────────────

def _norm_header(s: Any) -> str:
    """
    Normalise an Excel column header for fuzzy matching:
      1. Convert to string, strip outer whitespace
      2. Strip a single layer of wrapping single-quotes
      3. Replace pipe '|' (used as line-break in the report) with space
      4. Arabic  ي/ك  →  Persian  ی/ک;  strip ZWNJ / tatweel
      5. Collapse runs of whitespace
    """
    if s is None:
        return ""
    t = str(s).strip()
    if len(t) >= 2 and t[0] == "'" and t[-1] == "'":
        t = t[1:-1].strip()
    t = t.replace("|", " ")
    t = t.replace("ي", "ی").replace("ك", "ک").replace("ة", "ه")
    t = t.replace("\u200c", " ").replace("\u200f", "").replace("ـ", "")
    t = " ".join(t.split())
    return t


def _build_col_index(df: pd.DataFrame) -> Dict[str, str]:
    """
    Return {normalised_header: original_column_name} for every column in *df*.
    """
    return {_norm_header(c): c for c in df.columns}


def _find_col(col_index: Dict[str, str], candidates: List[str]) -> Optional[str]:
    """
    Return the first original column name whose normalised form matches any candidate.
    Candidates are tried in order; substring matching is used as a fallback.
    """
    for candidate in candidates:
        norm = _norm_header(candidate)
        if norm in col_index:
            return col_index[norm]
    # substring fallback
    for candidate in candidates:
        norm = _norm_header(candidate)
        for k, v in col_index.items():
            if norm in k or k in norm:
                return v
    return None


def _safe_str(val: Any) -> Optional[str]:
    """Return None for NaN / None / empty; otherwise a stripped string."""
    if val is None:
        return None
    s = str(val).strip()
    if s == "" or s.lower() in ("nan", "none", "nat"):
        return None
    return s


# ── insurer parsing ────────────────────────────────────────────────────────────

# Primary: explicit percentage token wrapped in parens, e.g. '(30 %)' or '(5%)'
_PCT_RE = re.compile(r"\(\s*(\d{1,3})\s*%\s*\)")
# Secondary: percentage embedded in the name string without formal parens,
# e.g. 'ایران 30 %' or 'دانا10%' — only used when primary doesn't match.
_PCT_INLINE_RE = re.compile(r"\b(\d{1,3})\s*%")

# Cash insurer names (after Arabic→Persian normalisation)
_CASH_NAMES = {"آزاد", "ازاد"}


def parse_insurer(raw: Optional[str]) -> Tuple[str, str, Optional[int], bool]:
    """
    Parse the insurer/payer field.

    Returns:
        insurer_name_norm  – cleaned name before first '('
        payer_source_norm  – 'cash' | 'insurance' | 'unknown'
        patient_share_pct  – integer 0-100 or None
        pct_detected       – True if an explicit '(NN %)' token was found
    """
    if not raw:
        return ("", "unknown", None, False)

    s = normalize_text(str(raw))  # Arabic→Persian, strip ZWNJ, etc.
    s = s.replace("|", " ")
    s = " ".join(s.split())

    # Text before the first '(' is the insurer name
    name = s[: s.index("(")] .strip() if "(" in s else s.strip()

    # ── payer source ─────────────────────────────────────────────────────────
    if name in _CASH_NAMES:
        payer_source = "cash"
    elif name:
        payer_source = "insurance"
    else:
        payer_source = "unknown"

    # ── patient share percentage ──────────────────────────────────────────────
    pct_match = _PCT_RE.search(s)          # primary: (NN %) form
    if pct_match:
        patient_share_pct = int(pct_match.group(1))
        pct_detected = True
    else:
        # secondary: percentage embedded in the name without formal parens
        inline = _PCT_INLINE_RE.search(s)
        if inline:
            patient_share_pct = int(inline.group(1))
            pct_detected = True
        elif payer_source == "insurance":
            patient_share_pct = 30     # standard default for insurance
            pct_detected = False
        elif payer_source == "cash":
            patient_share_pct = 100
            pct_detected = False
        else:
            patient_share_pct = None
            pct_detected = False

    return (name, payer_source, patient_share_pct, pct_detected)


# ── column candidates ──────────────────────────────────────────────────────────

_C_PATIENT  = ["نام بيمار", "نام بیمار", "نام بیمار(تشکیل پرونده شده)"]
_C_PHONE    = ["موبايل", "موبایل", "تلفن", "شماره تماس"]
_C_SERVICE  = ["نام خدمت", "خدمت", "نام خدمات"]
_C_INSURER  = [
    "سازمان بيمه گر بيمار",    # after pipe-strip
    "سازمان بیمه گر بیمار",
    "سازمان بيمه گر محاسباتي",
    "سازمان بیمه گر محاسباتی",
    "سازمان بيمه گر اوليه",
    "سازمان بیمه گر اولیه",
]
_C_DATE     = ["تاريخ پذيرش", "تاریخ پذیرش", "تاريخ", "تاریخ"]
_C_AMT_PAT  = ["سهم بيمار", "سهم بیمار"]
_C_AMT_INS  = ["سهم سازمان"]
_C_NET      = ["خالص دريافتي", "خالص دریافتی", "ب.ب.ق"]


# ── core ingestion ─────────────────────────────────────────────────────────────

def ingest_file(
    file_path: Path,
    conn: sqlite3.Connection,
    year: int,
    *,
    skip_existing: bool = True,
) -> Dict[str, Any]:
    """
    Load one payments Excel file into stg_payments.

    Returns a stats dict with totals and per-source/pct breakdowns.
    """
    import_run_id = file_path.stem                  # 'payments_1404_full'
    file_name     = file_path.name
    sheet_name    = "MSExcel"

    stats: Dict[str, Any] = {
        "file": file_name,
        "year": year,
        "total_rows": 0,
        "inserted": 0,
        "skipped_duplicate": 0,
        "errors": 0,
        "payer_cash": 0,
        "payer_insurance": 0,
        "payer_unknown": 0,
        "pct_detected": 0,
        "pct_default_30": 0,
        "pct_default_100": 0,
    }

    cursor = conn.cursor()

    # ── skip if already fully loaded ─────────────────────────────────────────
    if skip_existing:
        cursor.execute(
            "SELECT COUNT(*) FROM stg_payments WHERE import_run_id = ?",
            (import_run_id,),
        )
        existing = cursor.fetchone()[0]
        if existing:
            logger.info(f"[{file_name}] Already loaded ({existing:,} rows) – skipping.")
            stats["skipped_duplicate"] = existing
            return stats

    logger.info(f"[{file_name}] Reading Excel …")

    try:
        df = pd.read_excel(
            file_path,
            sheet_name=sheet_name,
            engine="openpyxl",
            dtype=str,          # read everything as string to preserve raw values
        )
    except Exception as exc:
        logger.error(f"[{file_name}] Failed to read Excel: {exc}")
        stats["errors"] += 1
        return stats

    stats["total_rows"] = len(df)
    logger.info(f"[{file_name}] Loaded {len(df):,} rows, {len(df.columns)} columns.")

    # ── map columns ───────────────────────────────────────────────────────────
    col_idx = _build_col_index(df)

    c_patient = _find_col(col_idx, _C_PATIENT)
    c_phone   = _find_col(col_idx, _C_PHONE)
    c_service = _find_col(col_idx, _C_SERVICE)
    c_insurer = _find_col(col_idx, _C_INSURER)
    c_date    = _find_col(col_idx, _C_DATE)
    c_amt_pat = _find_col(col_idx, _C_AMT_PAT)
    c_amt_ins = _find_col(col_idx, _C_AMT_INS)
    c_net     = _find_col(col_idx, _C_NET)

    logger.debug(
        f"[{file_name}] Column map: patient={c_patient!r} phone={c_phone!r} "
        f"service={c_service!r} insurer={c_insurer!r} date={c_date!r} "
        f"amt_pat={c_amt_pat!r} amt_ins={c_amt_ins!r} net={c_net!r}"
    )

    # ── INSERT helpers ────────────────────────────────────────────────────────
    INSERT_SQL = """
        INSERT INTO stg_payments (
            import_run_id, file_name, sheet_name, row_number, shamsi_year,
            loaded_at, parse_status, parse_error,
            patient_name_raw, phone_raw, service_raw, insurer_raw,
            appointment_date_raw, amount_patient_raw, amount_insurer_raw, net_received_raw,
            row_json,
            insurer_name_norm, payer_source_norm, patient_share_pct, pct_detected
        ) VALUES (
            ?,?,?,?,?,
            ?,?,?,
            ?,?,?,?,
            ?,?,?,?,
            ?,
            ?,?,?,?
        )
    """

    loaded_at = datetime.now().isoformat()
    batch: List[tuple] = []

    def _flush(batch: List[tuple]) -> None:
        if batch:
            cursor.executemany(INSERT_SQL, batch)
            conn.commit()

    # ── row loop ──────────────────────────────────────────────────────────────
    for idx, row in df.iterrows():
        row_number = idx + 2   # 1-indexed + header row

        try:
            patient_name_raw     = _safe_str(row[c_patient]  if c_patient  else None)
            phone_raw            = _safe_str(row[c_phone]    if c_phone    else None)
            service_raw          = _safe_str(row[c_service]  if c_service  else None)
            insurer_raw          = _safe_str(row[c_insurer]  if c_insurer  else None)
            appointment_date_raw = _safe_str(row[c_date]     if c_date     else None)
            amount_patient_raw   = _safe_str(row[c_amt_pat]  if c_amt_pat  else None)
            amount_insurer_raw   = _safe_str(row[c_amt_ins]  if c_amt_ins  else None)
            net_received_raw     = _safe_str(row[c_net]      if c_net      else None)

            # normalise insurer
            insurer_name_norm, payer_source_norm, patient_share_pct, pct_detected = \
                parse_insurer(insurer_raw)

            # stats bookkeeping
            if payer_source_norm == "cash":
                stats["payer_cash"] += 1
            elif payer_source_norm == "insurance":
                stats["payer_insurance"] += 1
            else:
                stats["payer_unknown"] += 1

            if pct_detected:
                stats["pct_detected"] += 1
            elif payer_source_norm == "insurance":
                stats["pct_default_30"] += 1
            elif payer_source_norm == "cash":
                stats["pct_default_100"] += 1

            row_json = json.dumps(
                row.to_dict(), ensure_ascii=False, default=str
            )

            batch.append((
                import_run_id, file_name, sheet_name, row_number, year,
                loaded_at, "ok", None,
                patient_name_raw, phone_raw, service_raw, insurer_raw,
                appointment_date_raw, amount_patient_raw, amount_insurer_raw, net_received_raw,
                row_json,
                insurer_name_norm, payer_source_norm,
                patient_share_pct, 1 if pct_detected else 0,
            ))
            stats["inserted"] += 1

        except Exception as exc:
            stats["errors"] += 1
            row_json = json.dumps(row.to_dict(), ensure_ascii=False, default=str)
            batch.append((
                import_run_id, file_name, sheet_name, row_number, year,
                loaded_at, "error", str(exc)[:500],
                None, None, None, None,
                None, None, None, None,
                row_json,
                None, None, None, 0,
            ))

        if len(batch) >= BATCH_SIZE:
            _flush(batch)
            batch.clear()
            logger.debug(f"[{file_name}] … {stats['inserted']:,} rows inserted")

    _flush(batch)
    batch.clear()

    logger.info(
        f"[{file_name}] Done: inserted={stats['inserted']:,} errors={stats['errors']}"
    )
    return stats


def ingest_all(
    payments_dir: Path = PAYMENTS_DIR,
    *,
    db_path: Optional[Path] = None,
    skip_existing: bool = True,
    file_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Scan *payments_dir* for matching Excel files and ingest each one.

    Args:
        payments_dir:   directory to scan
        db_path:        SQLite DB path (defaults to repo-root atieh_clinic.db)
        skip_existing:  if True, skip files already fully loaded
        file_filter:    if given, only process files whose name contains this string

    Returns:
        list of per-file stats dicts
    """
    if db_path is None:
        db_path = Path(__file__).parent.parent.parent / "atieh_clinic.db"

    if not payments_dir.exists():
        raise FileNotFoundError(f"Payments directory not found: {payments_dir}")

    # ── discover files ────────────────────────────────────────────────────────
    candidates = sorted(payments_dir.glob("payments_*_full.xlsx"))
    files: List[Tuple[Path, int]] = []
    for fp in candidates:
        m = FILE_PATTERN.match(fp.name)
        if not m:
            logger.debug(f"Skipping {fp.name} – does not match pattern")
            continue
        if file_filter and file_filter not in fp.name:
            continue
        year = int(m.group(1))
        files.append((fp, year))

    if not files:
        logger.warning(f"No matching files found in {payments_dir}")
        return []

    logger.info(f"Found {len(files)} payment file(s): {[f.name for f, _ in files]}")

    # ── open DB ───────────────────────────────────────────────────────────────
    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=15000")
    conn.execute("PRAGMA synchronous=NORMAL")

    all_stats: List[Dict[str, Any]] = []
    try:
        for fp, year in files:
            stats = ingest_file(fp, conn, year, skip_existing=skip_existing)
            all_stats.append(stats)
    finally:
        conn.close()

    return all_stats


# ── summary printer ────────────────────────────────────────────────────────────

def print_summary(all_stats: List[Dict[str, Any]]) -> None:
    """Print a human-readable ingestion summary."""
    SEP = "=" * 68

    print(f"\n{SEP}")
    print("PAYMENTS INGESTION SUMMARY")
    print(SEP)

    grand = {
        "total_rows": 0, "inserted": 0, "errors": 0,
        "payer_cash": 0, "payer_insurance": 0, "payer_unknown": 0,
        "pct_detected": 0, "pct_default_30": 0, "pct_default_100": 0,
    }

    print(f"\n{'Year':<8}  {'Total':>10}  {'Inserted':>10}  {'Errors':>7}  "
          f"{'Cash':>8}  {'Insurance':>10}  {'Pct expl.':>10}  {'Def.30%':>8}")
    print("-" * 80)

    for s in all_stats:
        yr        = s["year"]
        total     = s["total_rows"]
        inserted  = s["inserted"]
        errors    = s["errors"]
        cash      = s["payer_cash"]
        insur     = s["payer_insurance"]
        pct_det   = s["pct_detected"]
        def30     = s["pct_default_30"]

        print(
            f"{yr:<8}  {total:>10,}  {inserted:>10,}  {errors:>7,}  "
            f"{cash:>8,}  {insur:>10,}  {pct_det:>10,}  {def30:>8,}"
        )

        for k in grand:
            grand[k] += s.get(k, 0)

    print("-" * 80)
    print(
        f"{'TOTAL':<8}  {grand['total_rows']:>10,}  {grand['inserted']:>10,}  "
        f"{grand['errors']:>7,}  {grand['payer_cash']:>8,}  "
        f"{grand['payer_insurance']:>10,}  {grand['pct_detected']:>10,}  "
        f"{grand['pct_default_30']:>8,}"
    )

    print(f"\n  Rows with explicit pct  : {grand['pct_detected']:,}")
    print(f"  Rows defaulted to 30%   : {grand['pct_default_30']:,}")
    print(f"  Rows defaulted to 100%  : {grand['pct_default_100']:,}")
    print(f"\n{SEP}\n")
