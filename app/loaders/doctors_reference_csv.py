from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import pandas as pd

def norm_fa(s: str) -> str:
    s = (s or "").strip()
    s = s.replace("ي", "ی").replace("ك", "ک").replace("\u200c", " ")
    s = s.replace("'", "").replace('"', "")
    s = " ".join(s.split())
    if s.startswith("دکتر "):
        s = s[5:].strip()
    elif s.startswith("د "):
        s = s[2:].strip()
    return s

@dataclass(frozen=True)
class DoctorRef:
    doctor_id: int
    doctor_name_display: str
    doctor_name_norm: str
    specialty: str

def load_doctors_reference_csv(data_dir: str | Path) -> list[DoctorRef]:
    p = Path(data_dir) / "inputs" / "reference" / "doctors_reference.csv"
    if not p.exists():
        raise FileNotFoundError(f"doctors_reference.csv not found: {p}")

    df = pd.read_csv(p, encoding="utf-8-sig")

    out: list[DoctorRef] = []
    for _, r in df.iterrows():
        out.append(
            DoctorRef(
                int(r["doctor_id"]),
                str(r["doctor_name_display"]).strip(),
                norm_fa(str(r["doctor_name_norm"])),
                "" if pd.isna(r["specialty"]) else str(r["specialty"]).strip(),
            )
        )
    return out
