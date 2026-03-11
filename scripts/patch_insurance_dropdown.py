from pathlib import Path
import re

root = Path(".")
api_file = root / "frontend" / "src" / "services" / "atiehApi.js"
page_file = root / "frontend" / "src" / "pages" / "ReceptionistPage.jsx"

api = api_file.read_text(encoding="utf-8")
page = page_file.read_text(encoding="utf-8")

# ---------------------------
# Patch atiehApi.js
# ---------------------------

if "import insuranceCatalog from '../data/insuranceCatalog'" not in api:
    api = "import insuranceCatalog from '../data/insuranceCatalog'\n" + api

api = api.replace(
    "async function request(path, options = {}) {",
    "async function request(path, options = {}, timeoutMs = REQUEST_TIMEOUT_MS) {"
)

api = api.replace(
    "const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)",
    "const timeoutId = setTimeout(() => controller.abort(), timeoutMs)"
)

if "function normalizeInsuranceResponse(response)" not in api:
    anchor = "const REQUEST_TIMEOUT_MS = 15000\n"
    helper = """
const INSURANCE_CACHE_KEY = 'atieh_insurance_catalog'

function normalizeInsuranceResponse(response) {
  const raw = Array.isArray(response)
    ? response
    : Array.isArray(response?.items)
      ? response.items
      : []

  return raw
    .map((i) => {
      const val = i?.value ?? i?.name ?? i?.label ?? i?.id ?? ''
      const lbl = i?.label ?? i?.name ?? i?.value ?? i?.id ?? ''
      const s = String(val).trim()
      if (!s) return null
      const upper = s.toUpperCase()
      if (upper === 'CASH' || s === 'نقد' || s === 'نقدی') return null

      return {
        id: String(i?.id ?? val),
        value: String(val),
        label: String(lbl),
        name: String(i?.name ?? lbl),
      }
    })
    .filter(Boolean)
}

"""
    api = api.replace(anchor, anchor + helper)

api = re.sub(
    r"getInsurances:\s*\(\)\s*=>\s*request\('/ai/engine/catalog/insurances'\),",
    """getInsurances: async () => {
    try {
      const response = await request('/ai/engine/catalog/insurances', {}, 30000)
      const normalized = normalizeInsuranceResponse(response)
      if (normalized.length) {
        localStorage.setItem(INSURANCE_CACHE_KEY, JSON.stringify(normalized))
        return normalized
      }
    } catch (e) {
      console.warn('getInsurances failed, using cache/fallback:', e?.message || e)
    }

    try {
      const cached = JSON.parse(localStorage.getItem(INSURANCE_CACHE_KEY) || '[]')
      const normalizedCached = normalizeInsuranceResponse(cached)
      if (normalizedCached.length) return normalizedCached
    } catch {}

    return normalizeInsuranceResponse(insuranceCatalog)
  },""",
    api
)

api_file.write_text(api, encoding="utf-8")

# ---------------------------
# Patch ReceptionistPage.jsx
# ---------------------------

page = page.replace("Ù†Ù‚Ø¯", "نقد").replace("Ù†Ù‚Ø¯ÛŒ", "نقدی")

insurance_block_pattern = re.compile(
    r"const insuranceOptions = \[(.*?)\]\n\n\s*const selectedInsuranceObj = .*?\n",
    re.S
)

insurance_block_replacement = """const insuranceOptions = [
    {
      id: 'CASH',
      value: 'CASH',
      label: t('reception.paymentType.cash'),
      name: t('reception.paymentType.cash'),
    },
    ...[...(insurances || [])]
      .filter((i) => {
        const val = typeof i === 'object' ? (i.value ?? i.name ?? i.label ?? i.id ?? '') : String(i ?? '')
        const s = String(val).trim()
        if (!s) return false
        const upper = s.toUpperCase()
        if (upper === 'CASH' || s === 'نقد' || s === 'نقدی') return false
        return true
      })
      .map((i) => {
        const val = i?.value ?? i?.name ?? i?.label ?? i?.id ?? ''
        const lbl = i?.label ?? i?.name ?? i?.value ?? i?.id ?? ''
        return {
          id: String(i?.id ?? val),
          value: String(val),
          label: String(lbl),
          name: String(i?.name ?? lbl),
        }
      }),
  ]
"""

page = insurance_block_pattern.sub(insurance_block_replacement + "\n", page)

# حذف نمایش score زیر dropdown
page = re.sub(
    r"\n\s*\{selectedInsuranceObj && selectedInsuranceObj\.priority_score != null && \(\n.*?\n\s*\)\}\n",
    "\n",
    page,
    flags=re.S
)

# اگر هنوز selectedInsuranceObj جایی مانده بود، حذف شود
page = re.sub(r"^\s*const selectedInsuranceObj = .*?$", "", page, flags=re.M)

page_file.write_text(page, encoding="utf-8")

print("Patched:")
print(f" - {api_file}")
print(f" - {page_file}")
