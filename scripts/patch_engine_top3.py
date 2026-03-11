from pathlib import Path
import re

p = Path(r".\engine\scheduling_engine.py")
text = p.read_text(encoding="utf-8")

if "recommendations = recommendations[:3]" in text:
    print("Already patched.")
    raise SystemExit(0)

pattern = re.compile(r"(?P<indent>^[ \t]*)return\s+recommendations\b", re.M)

replacement = r'''recommendations = sorted(
\g<indent>    recommendations,
\g<indent>    key=lambda x: x.get("final_score", x.get("score", 0)),
\g<indent>    reverse=True
\g<indent>)
\g<indent>recommendations = recommendations[:3]
\g<indent>return recommendations'''

new_text, count = pattern.subn(replacement, text, count=1)

if count == 0:
    print("No 'return recommendations' pattern found.")
    raise SystemExit(1)

p.write_text(new_text, encoding="utf-8")
print("Patched .\\engine\\scheduling_engine.py")
