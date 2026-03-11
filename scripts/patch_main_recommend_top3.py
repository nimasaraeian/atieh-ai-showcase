from pathlib import Path
import re

p = Path(r".\main.py")
text = p.read_text(encoding="utf-8")

original = text

# فقط endpoint /ai/recommend-slot را بگیر
pattern = re.compile(
    r'(@app\.post\("/ai/recommend-slot"\)\s*.*?def .*?:\s*)(?P<body>.*?)(?=\n@app\.|\Z)',
    re.S
)

m = pattern.search(text)
if not m:
    print("recommend-slot endpoint not found")
    raise SystemExit(1)

body = m.group("body")

if 'recommendations = sorted(' in body and 'recommendations = recommendations[:3]' in body:
    print("Endpoint already patched.")
    raise SystemExit(0)

# قبل از اولین return که response دیکشنری را برمی‌گرداند، patch را تزریق کن
body_new, n = re.subn(
    r'(?P<indent>^[ \t]*)return\s*\{',
    r'''recommendations = sorted(
\g<indent>    recommendations,
\g<indent>    key=lambda x: x.get("final_score", x.get("score", 0)),
\g<indent>    reverse=True
\g<indent>)
\g<indent>recommendations = recommendations[:3]

\g<indent>return {''',
    body,
    count=1,
    flags=re.M
)

if n == 0:
    print("Could not find return { inside endpoint")
    raise SystemExit(1)

# count را اگر وجود دارد، به len(recommendations) تغییر بده
body_new = re.sub(
    r'"count"\s*:\s*[^,\n]+',
    '"count": len(recommendations)',
    body_new
)

# اگر score_formula نبود، اضافه‌اش کن بعد از patient_context یا preferred_day_mapped
if '"score_formula"' not in body_new:
    body_new = re.sub(
        r'("patient_context"\s*:\s*patient_context\s*,)',
        r'\1\n        "score_formula": "0.50*financial + 0.30*payment + 0.20*time",',
        body_new,
        count=1
    )

new_text = text[:m.start("body")] + body_new + text[m.end("body"):]

p.write_text(new_text, encoding="utf-8")
print("Patched .\\main.py endpoint /ai/recommend-slot")
