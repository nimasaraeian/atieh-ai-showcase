from pathlib import Path
import json

root = Path(".")
src = root / "data" / "outputs" / "insurance_priority.json"
out = root / "frontend" / "src" / "data" / "insuranceCatalog.js"
out.parent.mkdir(parents=True, exist_ok=True)

if not src.exists():
    raise SystemExit(f"Missing file: {src}")

data = json.loads(src.read_text(encoding="utf-8"))
items = data.get("items", [])

rows = []
for item in items:
    name = str(item.get("insurance_name", "")).strip()
    if not name:
        continue
    rows.append({
        "id": name,
        "value": name,
        "label": name,
        "name": name
    })

rows.sort(key=lambda x: x["label"])

js = "const insuranceCatalog = " + json.dumps(rows, ensure_ascii=False, indent=2) + ";\n\nexport default insuranceCatalog;\n"
out.write_text(js, encoding="utf-8")
print(f"Wrote: {out}")
print(f"Items: {len(rows)}")
