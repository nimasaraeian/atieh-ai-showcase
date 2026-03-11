from pathlib import Path

path = Path(r".\frontend\src\pages\ReceptionistPage.jsx")
text = path.read_text(encoding="utf-8")

old = """              <label className="mb-1 block text-xs text-slate-500">{t('reception.insurance')}</label>
              <select
                value={insurance}
                onChange={(e) => setInsurance(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-sm text-slate-100"
              >
                {insuranceOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>"""

new = """              <label className="mb-1 block text-xs text-slate-500">{t('reception.insurance')}</label>
              <p className="mb-1 text-[11px] text-red-400">
                insuranceOptions: {insuranceOptions.length} | insurances: {insurances.length}
              </p>
              <pre className="mb-2 max-h-32 overflow-auto rounded bg-slate-900 p-2 text-[10px] text-slate-300">
                {JSON.stringify(insuranceOptions.slice(0, 5), null, 2)}
              </pre>
              <select
                value={insurance}
                onChange={(e) => setInsurance(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-sm text-slate-100"
              >
                {insuranceOptions.length === 0 ? (
                  <option value="CASH">نقد</option>
                ) : (
                  insuranceOptions.map((opt) => (
                    <option key={opt.value || opt.id} value={opt.value || opt.id}>
                      {opt.label || opt.name || opt.value || opt.id}
                    </option>
                  ))
                )}
              </select>"""

if old not in text:
    raise SystemExit("Target block not found. No changes made.")

text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8", newline="\n")
print("Insurance debug block inserted.")
