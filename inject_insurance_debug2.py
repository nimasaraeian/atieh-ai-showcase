from pathlib import Path

path = Path(r".\frontend\src\pages\ReceptionistPage.jsx")
text = path.read_text(encoding="utf-8")

marker = """<label className="mb-1 block text-xs text-slate-500">{t('reception.insurance')}</label>"""

inject = """<label className="mb-1 block text-xs text-slate-500">{t('reception.insurance')}</label>
              <p className="mb-1 text-[11px] text-red-400">
                insuranceOptions: {insuranceOptions.length} | insurances: {insurances.length}
              </p>
              <pre className="mb-2 max-h-32 overflow-auto rounded bg-slate-900 p-2 text-[10px] text-slate-300">
                {JSON.stringify(insuranceOptions.slice(0, 5), null, 2)}
              </pre>"""

if marker not in text:
    raise SystemExit("Insurance label marker not found.")

text = text.replace(marker, inject, 1)
path.write_text(text, encoding="utf-8", newline="\n")
print("Insurance debug injected.")
