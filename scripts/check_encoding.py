#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scan frontend/src for mojibake/encoding corruption patterns.
Exit with non-zero code if any pattern is found.
"""
import os
import re
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

REPO = Path(__file__).resolve().parent.parent
FRONTEND_SRC = REPO / "frontend" / "src"

# Common mojibake patterns (UTF-8 misinterpreted as Latin-1/Windows-1252)
MOJIBAKE_PATTERNS = [
    r"Ø",
    r"Ù",
    r"â€",
    r"â€""",
    r"Ã",
    r"\uFFFD",  # replacement character
]

COMPILED = [re.compile(p) for p in MOJIBAKE_PATTERNS]

EXTENSIONS = {".js", ".jsx", ".ts", ".tsx", ".json", ".css"}


def scan_file(path: Path) -> list[tuple[int, str]]:
    """Return list of (line_no, line) where mojibake was found."""
    issues = []
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f, 1):
                for pat in COMPILED:
                    if pat.search(line):
                        issues.append((i, line.rstrip()))
                        break
    except Exception as e:
        issues.append((0, f"ERROR reading file: {e}"))
    return issues


def main() -> int:
    if not FRONTEND_SRC.exists():
        print(f"[WARN] frontend/src not found: {FRONTEND_SRC}")
        return 0

    found_any = False
    for fpath in sorted(FRONTEND_SRC.rglob("*")):
        if fpath.suffix not in EXTENSIONS or not fpath.is_file():
            continue
        if "_backup" in fpath.name or ".bak" in fpath.suffix:
            continue
        rel = fpath.relative_to(REPO)
        issues = scan_file(fpath)
        if issues:
            found_any = True
            print(f"\n{rel}")
            for line_no, content in issues[:10]:  # cap per file
                preview = content[:80].replace("\n", " ")
                try:
                    print(f"  L{line_no}: {preview}")
                except UnicodeEncodeError:
                    print(f"  L{line_no}: [encoding error in preview]")
            if len(issues) > 10:
                print(f"  ... and {len(issues) - 10} more")

    if found_any:
        print("\n[FAIL] Mojibake/encoding issues detected. Fix encoding and re-run.")
        return 1
    print("[OK] No mojibake patterns found in frontend/src")
    return 0


if __name__ == "__main__":
    sys.exit(main())
