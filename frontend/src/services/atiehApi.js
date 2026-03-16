import insuranceCatalog from '../data/insuranceCatalog'
export const API_BASE = import.meta.env.VITE_API_BASE || ''

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
const PATIENT_SEARCH_TIMEOUT_MS = 300000  // 5 min — جستجوی بیمار بدون محدودیت عملی

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


const INSURANCE_TIMEOUT_MS = 30000

async function request(path, options = {}, timeoutMs = REQUEST_TIMEOUT_MS) {
  const url = path.startsWith('http') ? path : `${API_BASE}${path}`
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs)
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
    request(`/api/staff/patients/search?q=${encodeURIComponent(q || '')}&limit=${limit}&offset=${offset}`, {}, PATIENT_SEARCH_TIMEOUT_MS),

  getPatientByRecordNo: (recordNo) =>
    request(`/patients/${encodeURIComponent(String(recordNo || '').trim())}`),

  getFinancialPatientDetail: (recordNo) =>
    request(`/financial/patient/${encodeURIComponent(String(recordNo || '').trim())}`),

  /** V2 reception: search by name, phone, CRM code, or patient_id. page_size default 50. */
  receptionSearchPatient: (q, page = 1, pageSize = 50) =>
    request(`/api/reception/search-patient?q=${encodeURIComponent(q || '')}&page=${page}&page_size=${pageSize}`),

  /** V2 reception: all linked profiles for a patient_id */
  receptionGetPatient: (patientId) =>
    request(`/api/reception/patient/${encodeURIComponent(patientId)}`),

  /** V2 reception: profile by crm_patient_code */
  receptionGetByCrmCode: (crmCode) =>
    request(`/api/reception/crm-code/${encodeURIComponent(String(crmCode || '').trim())}`),

  getServices: () => request('/ai/engine/catalog/services'),
  getInsurances: () => request('/ai/engine/catalog/insurances', {}, INSURANCE_TIMEOUT_MS),

  createAppointment: (body) => request('/appointments', { method: 'POST', body: JSON.stringify(body) }),

  /** Finalize AI-recommended slot and persist to ai_finalized_bookings */
  finalizeBooking: (body) =>
    request('/api/receptionist/finalize-booking', { method: 'POST', body: JSON.stringify(body) }),

  getFinalizedBookings: (limit = 100) =>
    request(`/api/receptionist/finalized-bookings?limit=${limit}`),

  getAppointmentsToday: () => request('/appointments?limit=100'),

  getDashboardSummary: () => request('/api/manager/dashboard/summary'),
  getTopValuePatients: (limit = 20) => request(`/api/manager/patients/top-value?limit=${limit}`),
  getDecisionLogs: (limit = 20) => request(`/api/manager/decision-logs?limit=${limit}`),

  getFilterDoctors: () => request('/api/manager/filters/doctors'),
  getFilterServices: () => request('/api/manager/filters/services'),
  getFilterPaymentTypes: () => request('/api/manager/filters/payment-types'),
  getFilterPatientTiers: () => request('/api/manager/filters/patient-tiers'),

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

  uploadImportFile: async ({ file, file_type, source_system, period, import_mode, notes }) => {
    const url = `${API_BASE}/api/import/upload`
    const formData = new FormData()
    formData.append('file', file)
    formData.append('file_type', file_type)
    if (source_system) formData.append('source_system', source_system)
    if (period) formData.append('period', period)
    if (import_mode) formData.append('import_mode', import_mode)
    if (notes) formData.append('notes', notes)

    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)
    let res
    try {
      res = await fetch(url, {
        method: 'POST',
        body: formData,
        signal: controller.signal,
      })
    } catch (e) {
      clearTimeout(timeoutId)
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
      throw new Error('Network error: ' + (e?.message || 'Failed to upload'))
    }
    if (!res.ok) throw new Error(extractError(payload) || `Upload failed: ${res.status}`)
    return payload
  },
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
    date_range: null,
  }
  for (const [k, v] of Object.entries(filters)) {
    if (v == null || v === '') continue
    const param = map[k] || k
    if (param && v) q.set(param, String(v))
  }
  const qs = q.toString()
  return qs ? `${base}${base.includes('?') ? '&' : '?'}${qs}` : base
}

