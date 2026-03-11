from pathlib import Path

path = Path(r".\frontend\src\pages\ReceptionistPage.jsx")
text = path.read_text(encoding="utf-8")

bad = """              <select
                value={insurance}
                onChange={(e) => setInsurance(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-sm text-slate-100"
              >
                <p className="mb-1 text-[11px] text-red-400">
insuranceOptions: {insuranceOptions.length} | insurances: {insurances.length}
</p>

<pre className="mb-2 max-h-32 overflow-auto rounded bg-slate-900 p-2 text-[10px] text-slate-300">
{JSON.stringify(insuranceOptions.slice(0,5), null, 2)}
</pre>
{insuranceOptions.map((opt) => (
                  <option key={opt.id ?? opt.value} value={opt.value ?? opt.name ?? opt.label ?? opt.id}>
                    {opt.label ?? opt.name ?? opt.value ?? opt.id}
                  </option>
                ))}"""

good = """              <p className="mb-1 text-[11px] text-red-400">
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
                {insuranceOptions.map((opt) => (
                  <option key={opt.id ?? opt.value} value={opt.value ?? opt.name ?? opt.label ?? opt.id}>
                    {opt.label ?? opt.name ?? opt.value ?? opt.id}
                  </option>
                ))}"""

if bad not in text:
    raise SystemExit("Target select block not found.")

text = text.replace(bad, good, 1)
path.write_text(text, encoding="utf-8", newline="\n")
print("Insurance select fixed.")
