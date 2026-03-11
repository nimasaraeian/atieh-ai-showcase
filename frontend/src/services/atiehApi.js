const API_BASE = import.meta.env.VITE_API_BASE || ''

function extractError(payload) {
  if (!payload) return 'Request failed'
  const d = payload.detail ?? payload.error ?? payload.message
  if (typeof d === 'string') return d
  if (Array.isArray(d)) {
    const msgs = d.map((x) => (x?.msg) || JSON.stringify(x)).filter(Boolean)
    return msgs.length ? msgs.join('; ') : 'Validation error'
  }
  if (d && typeof d === 'object') return d.msg ?? d.message ?? JSON.stringify(d)
  return `Request failed: ${payload.status ?? 'unknown'}`
}

const REQUEST_TIMEOUT_MS = 15000

async function request(path, options = {}) {
  const url = path.startsWith('http') ? path : `${API_BASE}${path}`
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)
  let res
  try {
    res = await fetch(url, {
      signal: controller.signal,
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    })
  } catch (e) {
    clearTimeout(timeoutId)
    if (e?.name === 'AbortError') throw new Error('زمان درخواست به پایان رسید')
    throw e
  }
  clearTimeout(timeoutId)
  let payload = null
  try {
    const text = await res.text()
    try {
      payload = text ? JSON.parse(text) : null
    } catch {
      payload = text
    }
  } catch (e) {
    throw new Error('Network error: ' + (e?.message || 'Failed to fetch'))
  }
  if (!res.ok) throw new Error(extractError(payload) || `Request failed: ${res.status}`)
  return payload
}

export const atiehApi = {
  recommendSlot: (body) => request('/ai/engine/recommend-slot', { method: 'POST', body: JSON.stringify(body) }),

  searchPatients: (q, limit = 50, offset = 0) =>
    request(`/api/staff/patients/search?q=${encodeURIComponent(q || '')}&limit=${limit}&offset=${offset}`),

  getServices: () => request('/ai/engine/catalog/services'),
  getInsurances: () => request('/ai/engine/catalog/insurances'),

  createAppointment: (body) => request('/appointments', { method: 'POST', body: JSON.stringify(body) }),

  getAppointmentsToday: () => request('/appointments?limit=100'),

  getDashboardSummary: () => request('/api/manager/dashboard/summary'),
  getTopValuePatients: (limit = 20) => request(`/api/manager/patients/top-value?limit=${limit}`),
  getDecisionLogs: (limit = 20) => request(`/api/manager/decision-logs?limit=${limit}`),

  // Filter options
  getFilterDoctors: () => request('/api/manager/filters/doctors'),
  getFilterServices: () => request('/api/manager/filters/services'),
  getFilterPaymentTypes: () => request('/api/manager/filters/payment-types'),
  getFilterPatientTiers: () => request('/api/manager/filters/patient-tiers'),

  // Real metrics from database (all accept optional filters)
  getTotalPatients: (filters = {}) => request(buildUrl('/api/manager/total-patients', filters)),
  getTotalTransactions: (filters = {}) => request(buildUrl('/api/manager/total-transactions', filters)),
  getTotalRevenue: (filters = {}) => request(buildUrl('/api/manager/total-revenue', filters)),
  getVipPatientsCount: () => request('/api/manager/vip-patients'),
  getActiveDoctors: (filters = {}) => request(buildUrl('/api/manager/active-doctors', filters)),
  getNoShowRate: (filters = {}) => request(buildUrl('/api/manager/no-show-rate', filters)),
  getDoctorUtilization: (filters = {}) => request(buildUrl('/api/manager/doctor-utilization', filters)),
  getPaymentDistribution: (filters = {}) => request(buildUrl('/api/manager/payment-distribution', filters)),
  getRevenueTrend: (limit = 90, filters = {}) => request(buildUrl(`/api/manager/revenue-trend?limit=${limit}`, filters)),
  getFinancialSummary: (filters = {}) => request(buildUrl('/api/manager/financial-summary', filters)),
  getTransactionStats: (filters = {}) => request(buildUrl('/api/manager/transaction-stats', filters)),
  getTierDistribution: (filters = {}) => request(buildUrl('/api/manager/tier-distribution', filters)),
  getTransactionTrend: (limit = 30, filters = {}) => request(buildUrl(`/api/manager/transaction-trend?limit=${limit}`, filters)),
  getTopValuePatients: (limit = 20, filters = {}) => request(buildUrl(`/api/manager/patients/top-value?limit=${limit}`, filters)),
  getTopServices: (limit = 15, filters = {}) => request(buildUrl(`/api/manager/top-services?limit=${limit}`, filters)),
  getRevenueByService: (limit = 15, filters = {}) => request(buildUrl(`/api/manager/revenue-by-service?limit=${limit}`, filters)),
  getRevenueByDoctor: (limit = 15, filters = {}) => request(buildUrl(`/api/manager/revenue-by-doctor?limit=${limit}`, filters)),
  getDoctorWorkload: (limit = 15, filters = {}) => request(buildUrl(`/api/manager/doctor-workload?limit=${limit}`, filters)),
  getServiceNormalizationReport: (limit = 100) => request(`/api/manager/service-normalization-report?limit=${limit}`),
}

function buildUrl(base, filters = {}) {
  if (!filters || typeof filters !== 'object') return base
  const q = new URLSearchParams()
  const map = {
    start_date: 'start_date',
    end_date: 'end_date',
    doctor: 'doctor',
    service: 'service',
    payment: 'payment',
    tier: 'tier',
    date_range: null, // handled as start_date/end_date
  }
  for (const [k, v] of Object.entries(filters)) {
    if (v == null || v === '') continue
    const param = map[k] || k
    if (param && v) q.set(param, String(v))
  }
  const qs = q.toString()
  return qs ? `${base}${base.includes('?') ? '&' : '?'}${qs}` : base
}
