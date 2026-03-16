import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { PageHeader } from '../components/layout/PageHeader'
import { SectionCard } from '../components/ui/SectionCard'
import { SearchBar } from '../components/ui/SearchBar'
import { EmptyState } from '../components/ui/EmptyState'
import { RecommendationCard } from '../components/ui/RecommendationCard'
import { Loader2 } from 'lucide-react'
import { atiehApi } from '../services/atiehApi'
import { DAYS_EN } from '../data/mockData'
import { formatCurrency, formatCurrencyRial, gregorianToShamsi } from '../utils/formatters'

const LOADING = 'در حال بارگذاری'
const DASH = '—'

function isNumericRecordNo(value) {
  const v = String(value ?? '').trim()
  if (v === '' || v === '-') return false
  return /^[0-9]+$/.test(v)
}

/** V2: patient has valid identity from master_patient_profile_v2 (no record_no required) */
function hasV2Identity(p) {
  return p && (p.link_tier != null || (p.crm_patient_code != null && String(p.crm_patient_code).trim() !== ''))
}

/**
 * Structured profile status code (from backend or computed). Never use vague "نیاز به بررسی" as default.
 * Returns one of: ok, initial, incomplete, multi_identity, needs_history, temporary
 */
function getPatientDisplayStatus(row) {
  if (!row) return 'ok'
  if (row.profile_status_code != null && String(row.profile_status_code).trim() !== '') {
    const code = String(row.profile_status_code).trim()
    if (['ok', 'initial', 'incomplete', 'multi_identity', 'needs_history', 'needs_insurance', 'temporary'].includes(code)) return code
  }
  const hasId = !!(row.crm_patient_code ?? row.primary_phone_norm ?? row.primary_phone ?? row.mobile)
  const hasValue = !!((row.payment_rows_count ?? 0) > 0 || row.total_net_received || row.link_tier)
  if (!hasId || !hasValue) return 'incomplete'
  const reviewFlag = row.review_flag
  const reason = (row.review_reason != null && String(row.review_reason).trim() !== '') ? String(row.review_reason).trim() : ''
  const hasReview = reviewFlag === 1 || !!reason
  if (hasReview) {
    if (reason === 'tier_d_review') return 'needs_history'
    if (reason === 'multiple_candidates_same_tier') return 'multi_identity'
    return 'temporary'
  }
  if (!row.link_tier && ((row.payment_rows_count ?? 0) === 0)) return 'initial'
  return 'ok'
}

/** Display label for status code; no generic "نیاز به بررسی". */
function getStatusLabel(code, t) {
  if (!code || code === 'ok') return t('reception.status.ok')
  const key = `reception.status.${code}`
  const label = t(key)
  return (label && label !== key) ? label : t('reception.status.temporary')
}

/** Badge CSS class by status code. */
function getStatusBadgeClass(code) {
  switch (code) {
    case 'ok': return 'bg-emerald-500/20 text-emerald-400'
    case 'initial':
    case 'incomplete': return 'bg-slate-500/20 text-slate-400'
    case 'multi_identity': return 'bg-slate-500/20 text-slate-400'
    case 'needs_history':
    case 'temporary': return 'bg-amber-500/20 text-amber-400'
    case 'needs_insurance': return 'bg-amber-500/20 text-amber-400'
    default: return 'bg-slate-500/20 text-slate-400'
  }
}

/** Semantic display: insurance score → receptionist-friendly class (internal score kept in tooltip). */
function getInsuranceClassLabel(score, t) {
  if (score == null || score === '') return null
  const n = Number(score)
  if (Number.isNaN(n)) return null
  if (n >= 70) return t('reception.summary.insuranceClassHigh')
  if (n >= 40) return t('reception.summary.insuranceClassMedium')
  return t('reception.summary.insuranceClassLow')
}

/** Visit count → visit history level. */
function getVisitHistoryLevel(count, t) {
  const n = Number(count ?? 0)
  if (n === 0) return t('reception.summary.visitNew')
  if (n <= 3) return t('reception.summary.visitRegular')
  return t('reception.summary.visitLoyal')
}

/** Relationship years → maturity. */
function getRelationshipMaturity(years, t) {
  const n = Number(years ?? 0)
  if (n < 1) return t('reception.summary.relationshipNew')
  if (n < 4) return t('reception.summary.relationshipEstablished')
  return t('reception.summary.relationshipLongTerm')
}

/** Priority score/tier → level label; optional secondary numeric. */
function getPriorityLevelLabel(scoreOrTier, t) {
  if (scoreOrTier == null || scoreOrTier === '') return null
  const s = String(scoreOrTier).toUpperCase()
  if (s === 'HIGH' || s === 'A' || s === 'بالا') return t('reception.summary.priorityHigh')
  if (s === 'MEDIUM' || s === 'B' || s === 'متوسط') return t('reception.summary.priorityMedium')
  const n = Number(scoreOrTier)
  if (!Number.isNaN(n)) {
    if (n >= 70) return t('reception.summary.priorityHigh')
    if (n >= 40) return t('reception.summary.priorityMedium')
    return t('reception.summary.priorityNormal')
  }
  return t('reception.summary.priorityNormal')
}

/** Convert ISO Gregorian YYYY-MM-DD to Jalali for display; leave other formats unchanged. */
function formatJalaliDate(value) {
  const v = String(value ?? '').trim()
  if (!v) return ''
  // Already looks like Jalali (uses '/')
  if (/^\d{4}\/\d{1,2}\/\d{1,2}$/.test(v)) return v
  // ISO-like Gregorian date
  if (/^\d{4}-\d{2}-\d{2}$/.test(v)) {
    const sh = gregorianToShamsi(v)
    return sh || v
  }
  return v
}

/** Compute preferred vs allowed scheduling windows (in days ahead).
 * Backend is the single source of truth; frontend only reads fields.
 */
function getPreferredWindow(patientPriorityProfile) {
  if (!patientPriorityProfile) return null
  const minDays = Number(patientPriorityProfile.scheduling_window_min_days ?? 0) || 0
  const maxDaysRaw =
    Number(patientPriorityProfile.scheduling_window_max_days ??
      patientPriorityProfile.scheduling_window_days ??
      0) || 0
  const preferredMinFromApi = patientPriorityProfile.scheduling_preferred_min_days
  const preferredMaxFromApi = patientPriorityProfile.scheduling_preferred_max_days

  if (!Number.isFinite(maxDaysRaw) || maxDaysRaw <= minDays) {
    return null
  }

  const allowedEnd = maxDaysRaw

  // If backend provides preferred window (authoritative), use it as-is (clamped inside allowed).
  if (preferredMinFromApi != null && preferredMaxFromApi != null) {
    const p0 = Math.max(minDays, Number(preferredMinFromApi) || 0)
    const p1 = Math.min(allowedEnd, Number(preferredMaxFromApi) || allowedEnd)
    if (Number.isFinite(p0) && Number.isFinite(p1) && p1 >= p0) {
      return {
        preferredStartDays: p0,
        preferredEndDays: p1,
        allowedStartDays: minDays,
        allowedEndDays: allowedEnd,
      }
    }
  }

  // If preferred window is not available, only expose allowed window.
  return {
    preferredStartDays: minDays,
    preferredEndDays: allowedEnd,
    allowedStartDays: minDays,
    allowedEndDays: allowedEnd,
  }
}

/** Map internal patient_priority_tier (P1–P7) to receptionist-friendly Persian label. */
function getPatientTierDisplay(tier, t) {
  const code = String(tier || '').toUpperCase()
  switch (code) {
    case 'P1': return t('reception.tierLabels.P1')    // ویژه / خیلی بالا
    case 'P2': return t('reception.tierLabels.P2')    // ارزش بالا
    case 'P3': return t('reception.tierLabels.P3')    // خوب
    case 'P4': return t('reception.tierLabels.P4')    // متوسط رو به بالا
    case 'P5': return t('reception.tierLabels.P5')    // معمولی
    case 'P6': return t('reception.tierLabels.P6')    // پایه
    case 'P7': return t('reception.tierLabels.P7')    // کم
    default: return t('reception.tierLabels.default')
  }
}

/** Scheduling window days → human-readable. */
function getSchedulingWindowLabel(days, t) {
  if (days == null || days === '') return null
  const n = Number(days)
  if (Number.isNaN(n)) return null
  if (n <= 14) return t('reception.summary.windowShort')
  if (n <= 30) return t('reception.summary.windowMedium')
  return t('reception.summary.windowLong')
}

/** Multi-CRM flag → CRM profile status. */
function getCrmProfileStatus(multiCrm, t) {
  return multiCrm ? t('reception.summary.crmMultiple') : t('reception.summary.crmSingle')
}

/** Follow-up queue → state. */
function getFollowUpState(inQueue, t) {
  return inQueue ? t('reception.summary.followUpInQueue') : t('reception.summary.followUpNone')
}

/** Clean empty-state labels: avoid repetitive "ثبت نشده". Use context-appropriate placeholder. */
function emptyLabel(value, t, kind = 'unknown') {
  if (value !== null && value !== undefined && value !== '') return String(value)
  if (kind === 'dash') return DASH
  if (kind === 'notAvailable') return t('reception.notAvailable') || 'موجود نیست'
  if (kind === 'notYetRecorded') return t('reception.notYetRecorded') || 'هنوز ثبت نشده'
  return t('reception.unknown') || 'نامشخص'
}

function getPaymentTypeLabel(fp) {
  if (!fp || typeof fp !== 'object') return null
  const cash = Number(fp?.cash_txn_count ?? 0) || 0
  const ins = Number(fp?.insurance_txn_count ?? 0) || 0
  if (cash > 0 && ins === 0) return 'نقد'
  if (ins > 0 && cash === 0) return 'بیمه'
  if (cash > 0 && ins > 0) return 'ترکیبی'
  return null
}

function normalizeServices(response) {
  if (Array.isArray(response)) {
    return response.map((s) => (s?.value ?? s?.name ?? s?.label ?? s?.id ?? s)?.toString?.() ?? String(s)).filter(Boolean)
  }
  if (response && typeof response === 'object' && Array.isArray(response?.items)) {
    return response.items.map((s) => (s?.value ?? s?.name ?? s?.label ?? s?.id ?? s)?.toString?.() ?? String(s)).filter(Boolean)
  }
  return []
}

function normalizeInsurances(response) {
  const raw = Array.isArray(response) ? response : (Array.isArray(response?.items) ? response.items : [])
  return (raw ?? [])
    .map((i) => {
      const val = i?.value ?? i?.name ?? i?.label ?? i?.id ?? ''
      const lbl = i?.label ?? i?.name ?? i?.value ?? i?.id ?? ''
      const s = String(val ?? '').trim()
      if (!s) return null
      const upper = s.toUpperCase()
      if (upper === 'CASH' || s === 'نقد' || s === 'نقدی') return null
      return { id: String(i?.id ?? val ?? ''), value: String(val), label: String(lbl || val) }
    })
    .filter(Boolean)
}

export function ReceptionistPage() {
  const { t, i18n } = useTranslation()
  const lng = i18n?.language || 'en'
  const [searchQ, setSearchQ] = useState('')
  const [searchResults, setSearchResults] = useState(null)
  const [searchCount, setSearchCount] = useState(null)
  const [searchLoading, setSearchLoading] = useState(false)
  const [searchError, setSearchError] = useState(null)
  const [selectedPatient, setSelectedPatient] = useState(null)
  const [selectedProfile, setSelectedProfile] = useState(null)
  const [selectedFinancialProfile, setSelectedFinancialProfile] = useState(null)
  const [profileLoading, setProfileLoading] = useState(false)
  const [profileError, setProfileError] = useState(null)
  const [selectionError, setSelectionError] = useState(null)
  const [services, setServices] = useState([])
  const [insurances, setInsurances] = useState([])
  const [service, setService] = useState('')
  const [insurance, setInsurance] = useState('CASH')
  const [insuranceLoading, setInsuranceLoading] = useState(false)
  const [insuranceError, setInsuranceError] = useState(null)
  const [preferredDay, setPreferredDay] = useState('')
  const [selectedDoctor, setSelectedDoctor] = useState('')
  const [recommendations, setRecommendations] = useState(null)
  const [recommendationMeta, setRecommendationMeta] = useState(null)
  const [selectedSlot, setSelectedSlot] = useState(null)
  const [finalizedBooking, setFinalizedBooking] = useState(null)
  const [finalizedList, setFinalizedList] = useState([])
  const [loadingRec, setLoadingRec] = useState(false)
  const [bookingLoading, setBookingLoading] = useState(false)
  const [bookingMessage, setBookingMessage] = useState(null)
  const [searchPage, setSearchPage] = useState(1)
  const [searchTotalPages, setSearchTotalPages] = useState(0)
  const [searchLoadMore, setSearchLoadMore] = useState(false)

  function parseActiveUser() {
    try {
      const raw = localStorage.getItem('atieh_user')
      if (!raw) return null
      const data = JSON.parse(raw)
      return {
        username: data.username ?? data.name ?? '',
        full_name: data.full_name ?? data.name ?? data.username ?? '',
        role: data.role ?? '',
      }
    } catch {
      return null
    }
  }

  const activeUser = parseActiveUser()

  useEffect(() => {
    atiehApi.getServices()
      .then((r) => setServices(normalizeServices(r ?? null)))
      .catch(() => setServices([]))
  }, [])

  useEffect(() => {
    setInsuranceLoading(true)
    setInsuranceError(null)
    atiehApi.getInsurances()
      .then((r) => {
        const list = normalizeInsurances(r ?? null)
        setInsurances(list)
        setInsuranceError(null)
      })
      .catch(() => {
        setInsurances([])
        setInsuranceError('')
      })
      .finally(() => setInsuranceLoading(false))
  }, [])

  const PAGE_SIZE = 50

  useEffect(() => {
    // Load recently finalized bookings for top summary box
    atiehApi
      .getFinalizedBookings(20)
      .then((r) => {
        const items = Array.isArray(r?.data) ? r.data : []
        setFinalizedList(items)
      })
      .catch(() => {
        setFinalizedList([])
      })
  }, [])

  const selectedRecordKey = (() => {
    if (!selectedPatient) return ''
    if (hasV2Identity(selectedPatient)) {
      const key = selectedPatient.crm_patient_code ?? selectedPatient.patient_id
      return key != null ? String(key).trim() : ''
    }
    const rn = selectedPatient?.record_no ?? selectedPatient?.recordNo
    return rn != null ? String(rn).trim() : ''
  })()

  const finalizedForSelected = (finalizedList || []).filter((b) => {
    const k = String(b?.record_no ?? '').trim()
    return !!selectedRecordKey && k === selectedRecordKey
  })

  function handleSearch(page = 1) {
    const q = String(searchQ ?? '').trim()
    if (!q) {
      setSearchResults([])
      setSearchCount(0)
      setSearchTotalPages(0)
      setSearchError(null)
      return
    }
    setSearchLoading(true)
    setSearchError(null)
    if (page === 1) setSearchLoadMore(false)
    atiehApi
      .receptionSearchPatient(q, page, PAGE_SIZE)
      .then((r) => {
        const raw = Array.isArray(r?.data) ? r.data : []
        const count = typeof r?.count === 'number' ? r.count : 0
        const totalPages = typeof r?.total_pages === 'number' ? r.total_pages : 0
        if (page === 1) {
          setSearchResults(raw)
        } else {
          setSearchResults((prev) => [...(prev ?? []), ...raw])
        }
        setSearchCount(count)
        setSearchPage(page)
        setSearchTotalPages(totalPages)
      })
      .catch((err) => {
        if (page === 1) {
          setSearchResults([])
          setSearchCount(0)
          setSearchTotalPages(0)
        }
        setSearchError(err?.message || t('error') || 'Search failed')
      })
      .finally(() => {
        setSearchLoading(false)
        setSearchLoadMore(false)
      })
  }

  function handleLoadMore() {
    if (searchPage >= searchTotalPages || searchLoading) return
    setSearchLoadMore(true)
    handleSearch(searchPage + 1)
  }

  function loadSelectedProfile(recordNo) {
    const rn = String(recordNo ?? '').trim()
    if (!isNumericRecordNo(rn)) {
      setSelectedProfile(null)
      setSelectedFinancialProfile(null)
      setProfileError(t('reception.invalidRecordNo') || 'Invalid record number')
      return
    }
    setProfileLoading(true)
    setProfileError(null)
    Promise.allSettled([
      atiehApi.getPatientByRecordNo(rn),
      atiehApi.getFinancialPatientDetail(rn),
    ])
      .then(([baseRes, finRes]) => {
        setSelectedProfile(baseRes?.status === 'fulfilled' ? (baseRes.value ?? null) : null)
        setSelectedFinancialProfile(finRes?.status === 'fulfilled' ? (finRes.value ?? null) : null)
        if (baseRes?.status !== 'fulfilled') {
          setProfileError(baseRes?.reason?.message || t('error') || 'Failed to load profile')
        }
        atiehApi.receptionGetByCrmCode(rn)
          .then((receptionRes) => {
            if (!receptionRes?.found || !receptionRes?.profile) return
            const first = receptionRes.first_visit_date ?? receptionRes.profile?.first_visit_date
            const last = receptionRes.last_payment_date ?? receptionRes.profile?.last_payment_date
            const insurancePrimary = receptionRes.insurance_primary ?? receptionRes.profile?.insurance_primary
            const insuranceRecent = receptionRes.insurance_recent ?? receptionRes.profile?.insurance_recent
            const insuranceVariantsCount = receptionRes.insurance_variants_count ?? receptionRes.profile?.insurance_variants_count
            if (first != null || last != null) {
              setSelectedProfile((prev) => (prev ? { ...prev, first_visit_date: first ?? prev.first_visit_date } : prev))
              setSelectedFinancialProfile((prev) => ({
                ...prev,
                financial_profile: {
                  ...prev?.financial_profile,
                  first_visit_date: first ?? prev?.financial_profile?.first_visit_date,
                  last_payment_date_raw: last ?? prev?.financial_profile?.last_payment_date_raw,
                  last_payment_date: last ?? prev?.financial_profile?.last_payment_date,
                },
              }))
            }
            if (insurancePrimary != null || insuranceRecent != null || insuranceVariantsCount != null) {
              setSelectedPatient((prev) => prev ? {
                ...prev,
                insurance_primary: insurancePrimary ?? prev.insurance_primary,
                insurance_recent: insuranceRecent ?? prev.insurance_recent,
                insurance_variants_count: insuranceVariantsCount ?? prev.insurance_variants_count,
                display_insurer: insuranceRecent ?? insurancePrimary ?? prev.display_insurer,
                multiple_insurers: (insuranceVariantsCount ?? prev.insurance_variants_count ?? 0) > 1,
              } : prev)
            }
            if (receptionRes?.patient_priority_profile) {
              setSelectedPatient((prev) => prev ? { ...prev, patient_priority_profile: receptionRes.patient_priority_profile } : prev)
            }
            if (receptionRes?.profile?.profile_status_code != null) {
              setSelectedPatient((prev) => prev ? { ...prev, profile_status_code: receptionRes.profile.profile_status_code } : prev)
            }
          })
          .catch(() => {})
      })
      .catch((err) => {
        setSelectedProfile(null)
        setSelectedFinancialProfile(null)
        setProfileError(err?.message || t('error') || 'Failed to load profile')
      })
      .finally(() => setProfileLoading(false))
  }

  function handleSelectPatient(row) {
    if (!row) {
      setSelectedPatient(null)
      setSelectedProfile(null)
      setSelectedFinancialProfile(null)
      setSelectedSlot(null)
      setRecommendations(null)
      setRecommendationMeta(null)
      setFinalizedBooking(null)
      setSelectionError(null)
      setProfileError(null)
      return
    }
    // Reset patient-specific state when switching to a new patient
    setSelectedSlot(null)
    setRecommendations(null)
    setRecommendationMeta(null)
    setBookingMessage(null)
    setFinalizedBooking(null)

    // Compute a stable record key used when saving finalized bookings (record_no we send to backend)
    const recordKeyForRow = (() => {
      if (hasV2Identity(row)) {
        const key = row.crm_patient_code ?? row.patient_id
        return key != null ? String(key).trim() : ''
      }
      const rn = row?.record_no ?? row?.recordNo
      return rn != null ? String(rn).trim() : ''
    })()
    if (hasV2Identity(row)) {
      setSelectionError(null)
      setProfileError(null)
      setSelectedPatient(row)
      const id = row.identity_summary || {}
      const fin = row.financial_summary || {}
      setSelectedProfile({
        name: id.name ?? row.canonical_patient_name ?? row.patient_name_canonical,
        patient_name: id.name ?? row.canonical_patient_name ?? row.patient_name_canonical,
        phone: id.primary_phone ?? row.primary_phone_norm ?? row.primary_phone,
        mobile: id.primary_phone ?? row.primary_phone_norm ?? row.primary_phone,
        id: row.patient_id,
      })
      setSelectedFinancialProfile({
        financial_profile: {
          net_received_toman: fin.total_net_received,
          lifetime_net_received: fin.total_net_received,
          financial_tier: row.link_tier,
          financial_value_score: null,
          last_payment_date_raw: null,
        },
        operational_status: {},
      })
      atiehApi.receptionGetPatient(row.patient_id)
        .then((r) => {
          const first = r?.first_visit_date ?? r?.financial_summary?.first_visit_date
          const last = r?.last_payment_date ?? r?.financial_summary?.last_payment_date
          const insurancePrimary = r?.insurance_primary
          const insuranceRecent = r?.insurance_recent
          const insuranceVariantsCount = r?.insurance_variants_count
          if (first != null || last != null) {
            setSelectedProfile((prev) => (prev ? { ...prev, first_visit_date: first ?? prev.first_visit_date } : prev))
            setSelectedFinancialProfile((prev) => ({
              ...prev,
              financial_profile: {
                ...prev?.financial_profile,
                first_visit_date: first ?? prev?.financial_profile?.first_visit_date,
                last_payment_date_raw: last ?? prev?.financial_profile?.last_payment_date_raw,
                last_payment_date: last ?? prev?.financial_profile?.last_payment_date,
              },
            }))
          }
          if (insurancePrimary != null || insuranceRecent != null || insuranceVariantsCount != null) {
            setSelectedPatient((prev) => prev ? {
              ...prev,
              insurance_primary: insurancePrimary ?? prev.insurance_primary,
              insurance_recent: insuranceRecent ?? prev.insurance_recent,
              insurance_variants_count: insuranceVariantsCount ?? prev.insurance_variants_count,
              display_insurer: insuranceRecent ?? insurancePrimary ?? prev.display_insurer,
              multiple_insurers: (insuranceVariantsCount ?? prev.insurance_variants_count ?? 0) > 1,
            } : prev)
          }
          if (r?.patient_priority_profile) {
            setSelectedPatient((prev) => prev ? { ...prev, patient_priority_profile: r.patient_priority_profile } : prev)
          }
          if (r?.review_status?.profile_status_code != null) {
            setSelectedPatient((prev) => prev ? { ...prev, profile_status_code: r.review_status.profile_status_code } : prev)
          }
        })
        .catch(() => {})
      // Attach any existing finalized booking for this patient (by record key) from history
      if (recordKeyForRow) {
        const fb = (finalizedList || []).find(
          (b) => String(b?.record_no ?? '').trim() === recordKeyForRow,
        )
        if (fb) setFinalizedBooking(fb)
      }
      return
    }
    const rn = row?.record_no ?? row?.recordNo
    if (!isNumericRecordNo(rn)) {
      setSelectedPatient(null)
      setSelectedProfile(null)
      setSelectedFinancialProfile(null)
      setSelectionError(t('reception.invalidRecordNo') || 'Invalid record number')
      setProfileError(null)
      return
    }
    setSelectionError(null)
    setSelectedPatient({ ...row, record_no: rn })
    loadSelectedProfile(rn)
    if (recordKeyForRow) {
      const fb = (finalizedList || []).find(
        (b) => String(b?.record_no ?? '').trim() === recordKeyForRow,
      )
      if (fb) setFinalizedBooking(fb)
    }
  }

  function handleRecommend() {
    const rec = selectedPatient?.record_no ?? selectedPatient?.crm_patient_code ?? selectedPatient?.patient_id ?? ''
    if (!selectedPatient || (!hasV2Identity(selectedPatient) && !isNumericRecordNo(rec))) return
    setLoadingRec(true)
    setRecommendations(null)
    setSelectedSlot(null)
    const recordNoOrCode = hasV2Identity(selectedPatient)
      ? (selectedPatient.crm_patient_code ?? String(selectedPatient.patient_id ?? ''))
      : rec
    const payload = {
      record_no: recordNoOrCode || null,
      crm_patient_code: hasV2Identity(selectedPatient) ? (selectedPatient.crm_patient_code ?? recordNoOrCode) : (selectedPatient?.crm_patient_code || null),
      service: service || 'TREATMENT_1',
      insurance: insurance || 'CASH',
      preferred_day: preferredDay || null,
    }
    if (selectedDoctor && selectedDoctor !== '') {
      payload.doctor_id = parseInt(selectedDoctor, 10)
    }
    atiehApi
      .recommendSlot(payload)
      .then((r) => {
        const list = (r && r.ok) ? (Array.isArray(r.recommendations) ? r.recommendations : []) : []
        // Always keep top 5 for UI; backend already sorts by score
        const topFive = list.slice(0, 5)
        setRecommendations(topFive)
        setRecommendationMeta({
          patient_priority_profile: r?.patient_priority_profile,
          patient_context: r?.patient_context,
          preferred_doctor_filter: r?.preferred_doctor_filter,
        })
      })
      .catch(() => setRecommendations([]))
      .finally(() => setLoadingRec(false))
  }

  function safeSlot(s) {
    if (!s || typeof s !== 'object') return { doctor_name: '—', date: '', time: '', floor: '', unit: '', reasons: [] }
    return {
      ...s,
      doctor_name: s?.doctor_name ?? '—',
      date: s?.date ?? '',
      time: s?.time ?? '—',
      floor: s?.floor ?? '',
      unit: s?.unit ?? '',
      reasons: Array.isArray(s?.reasons) ? s.reasons : [],
    }
  }

  function handleBookSlot(slot) {
    if (!slot || !selectedPatient) return
    const patientName = selectedPatient?.canonical_patient_name ?? selectedPatient?.patient_name_canonical ?? selectedPatient?.patient_name ?? selectedPatient?.name ?? ''
    const recordNo = selectedPatient?.record_no ?? selectedPatient?.crm_patient_code ?? selectedPatient?.patient_id ?? ''
    const dateVal = slot.date ?? ''
    const timeVal = slot.time ?? ''
    const doctorName = (slot.doctor_name != null && String(slot.doctor_name).trim() !== '') ? String(slot.doctor_name).trim() : '—'
    const serviceVal = service || 'TREATMENT_1'
    if (!recordNo || !patientName || !dateVal || !timeVal) {
      setBookingMessage(t('reception.missingFields'))
      return
    }
    setBookingLoading(true)
    setBookingMessage(null)
    atiehApi
      .finalizeBooking({
        record_no: String(recordNo),
        patient_name: patientName,
        doctor_name: doctorName,
        service: serviceVal,
        date: dateVal,
        time: timeVal,
        receptionist_user: activeUser?.username || activeUser?.full_name || '',
      })
      .then((res) => {
        setBookingMessage(t('reception.bookingSuccess'))
        if (res) {
          setFinalizedBooking(res)
          setFinalizedList((prev) => {
            const next = [res, ...(Array.isArray(prev) ? prev : [])]
            return next.slice(0, 20)
          })
        }
      })
      .catch((err) => {
        const detail = err?.response?.data?.detail ?? err?.message ?? 'Request failed'
        setBookingMessage(typeof detail === 'string' ? detail : JSON.stringify(detail))
      })
      .finally(() => setBookingLoading(false))
  }

  const patients = searchResults ?? []
  const slots = recommendations ?? []
  const canRecommend = selectedPatient && (hasV2Identity(selectedPatient) || isNumericRecordNo(selectedPatient?.record_no ?? ''))

  return (
    <div className="space-y-6" dir={lng === 'fa' ? 'rtl' : 'ltr'}>
      <PageHeader
        title={t('reception.title')}
        subtitle={t('reception.subtitle')}
      />
      {activeUser && (
        <div className="text-xs text-slate-400">
          رسپشن فعال: <span className="font-medium text-slate-200">{activeUser.full_name || activeUser.username}</span>
          {activeUser.username && activeUser.full_name && (
            <span className="ms-1 text-slate-500">({activeUser.username})</span>
          )}
        </div>
      )}
      {/* VERTICAL WORKFLOW (all sections stacked); each section is horizontal/full-width */}

      {/* 1) Full-width horizontal search */}
      <SectionCard title={t('reception.patientSearch')} subtitle={t('reception.patientSearchSubtitle')}>
          <SearchBar
            value={searchQ}
            onChange={setSearchQ}
            onSearch={handleSearch}
            placeholder={t('reception.searchPlaceholder')}
          />
          {searchLoading && <p className="mt-2 text-xs text-slate-500">{t('loading')}</p>}
          {!searchLoading && searchCount != null && (
            <p className="mt-2 text-xs text-slate-500">
              {searchCount === 0
                ? t('reception.noPatientsFound')
                : searchTotalPages > 1
                  ? `${searchCount} ${t('chart.count') || 'نتیجه'} (${(searchResults ?? []).length} ${t('reception.showing') || 'نمایش داده‌شده'})`
                  : `${searchCount} ${t('chart.count') || 'نتیجه'}`}
            </p>
          )}
          {!searchLoading && searchTotalPages > 1 && searchPage < searchTotalPages && (
            <button
              type="button"
              onClick={() => { setSearchLoadMore(true); handleLoadMore() }}
              disabled={searchLoadMore}
              className="mt-2 rounded border border-slate-600 bg-slate-800 px-2 py-1 text-xs text-slate-300 hover:bg-slate-700 disabled:opacity-50"
            >
              {searchLoadMore ? t('loading') : (t('reception.loadMore') || 'بارگذاری بیشتر')}
            </button>
          )}
          {searchError && <p className="mt-2 text-xs text-red-400">{searchError}</p>}
          {selectionError && <p className="mt-2 text-xs text-red-400">{selectionError}</p>}
          <div className="mt-4 max-h-64 overflow-y-auto rounded-lg border border-slate-800">
            {patients.length === 0 ? (
              <EmptyState
                title={searchQ.trim() ? t('reception.noPatientsFound') : t('empty')}
                message={searchQ.trim() ? t('reception.tryDifferentSearch') : t('reception.patientSearchSubtitle')}
              />
            ) : (
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-slate-900/95 text-start text-xs text-slate-500">
                  <tr>
                    <th className="px-4 py-3">{t('reception.name')}</th>
                    <th className="px-4 py-3">{t('reception.recordNo')}</th>
                    <th className="px-4 py-3">{t('reception.mobile')}</th>
                    <th className="px-4 py-3" title={t('reception.profileFields.identityTier')}>{t('reception.tier')}</th>
                  </tr>
                </thead>
                <tbody>
                  {(patients ?? []).filter(Boolean).map((p, idx) => {
                    const key = p?.crm_patient_code ?? p?.patient_id ?? p?.record_no ?? idx
                    const isSelected = selectedPatient && (selectedPatient?.crm_patient_code === p?.crm_patient_code || selectedPatient?.patient_id === p?.patient_id || (selectedPatient?.record_no != null && selectedPatient?.record_no === (p?.record_no ?? p?.recordNo)))
                    const name = p?.canonical_patient_name ?? p?.patient_name_canonical ?? p?.patient_name ?? p?.name
                    const phone = p?.primary_phone_norm ?? p?.primary_phone ?? p?.mobile ?? p?.mobile_canonical ?? p?.phone
                    const codeOrRecord = p?.crm_patient_code ?? p?.record_no ?? p?.recordNo
                    const tier = p?.link_tier ?? p?.financial_tier ?? p?.tier
                    return (
                      <tr
                        key={`${key}-${phone ?? idx}`}
                        onClick={() => handleSelectPatient(p)}
                        className={`cursor-pointer border-t border-slate-800 transition-colors hover:bg-slate-800/50 ${isSelected ? 'bg-cyan-500/8' : ''}`}
                      >
                        <td className="px-4 py-2.5 font-medium text-slate-200">
                          {name ?? '-'}
                          {getPatientDisplayStatus(p) !== 'ok' && getPatientDisplayStatus(p) !== 'multi_identity' && (() => {
                            const code = getPatientDisplayStatus(p)
                            return (
                              <span key={code} className={`mr-1 rounded px-1.5 py-0.5 text-[10px] ${getStatusBadgeClass(code)}`} title={getStatusLabel(code, t)}>{getStatusLabel(code, t)}</span>
                            )
                          })()}
                          {/* Multi-CRM وضعیت فقط در پروفایل جزئیات استفاده می‌شود؛ در لیست نمایش داده نمی‌شود */}
                        </td>
                        <td className="px-4 py-2.5 text-slate-400">{codeOrRecord ?? '-'}</td>
                        <td className="px-4 py-2.5 text-slate-400">{phone ?? '-'}</td>
                        <td className="px-4 py-2.5 text-slate-400">{tier ?? '-'}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
          </div>
        </SectionCard>

      {/* 2) Selected patient profile (FULL WIDTH; no page scroll required for basics) */}
      <SectionCard title={t('reception.selectedPatientProfile')} subtitle="">
        <div className="rounded-lg border border-slate-700 bg-slate-800/50 overflow-hidden">
          {profileLoading && <div className="p-4 text-center text-sm text-slate-500">{t('reception.loadingProfile')}</div>}
          {!profileLoading && profileError && <div className="p-3 text-sm text-red-400">{profileError}</div>}
          {!profileLoading && !profileError && !selectedPatient && (
            <div className="p-6 text-center">
              <p className="text-slate-400 font-medium">{t('reception.profileEmptyTitle')}</p>
              <p className="mt-1 text-xs text-slate-500">{t('reception.profileEmptyHint')}</p>
            </div>
          )}
          {!profileLoading && !profileError && selectedPatient && (hasV2Identity(selectedPatient) || selectedPatient?.record_no) && (
            <div className="p-4">
              {/* Compact, horizontal, full-width header */}
              <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-700/60 bg-slate-900/40 p-4">
                <div className="min-w-[240px]">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-base font-semibold text-slate-100">
                      {emptyLabel(selectedProfile?.name ?? selectedPatient?.canonical_patient_name ?? selectedPatient?.patient_name_canonical ?? selectedPatient?.patient_name ?? selectedPatient?.name, t, 'dash')}
                    </span>
                    {selectedPatient?.patient_priority_profile?.patient_priority_tier && (
                      <span className="rounded bg-cyan-500/20 px-2 py-0.5 text-xs text-cyan-300">
                        {getPatientTierDisplay(
                          selectedPatient.patient_priority_profile.patient_priority_tier,
                          t,
                        )}
                      </span>
                    )}
                    {getPatientDisplayStatus(selectedPatient) !== 'ok' && (() => {
                      const code = getPatientDisplayStatus(selectedPatient)
                      return <span key={code} className={`rounded px-2 py-0.5 text-xs ${getStatusBadgeClass(code)}`}>{getStatusLabel(code, t)}</span>
                    })()}
                  </div>
                  <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-sm text-slate-400">
                    <span>{t('reception.profileFields.recordNo')}: {emptyLabel(selectedPatient?.crm_patient_code ?? selectedPatient?.record_no ?? selectedProfile?.record_no, t, 'dash')}</span>
                    <span>{t('reception.profileFields.mobile')}: {emptyLabel(selectedProfile?.phone ?? selectedPatient?.primary_phone_norm ?? selectedPatient?.primary_phone ?? selectedPatient?.mobile, t, 'dash')}</span>
                    <span>{t('reception.profileFields.internalId')}: {emptyLabel(selectedProfile?.id ?? selectedPatient?.patient_id, t, 'dash')}</span>
                  </div>
                </div>

                {/* Always-visible “at a glance” chips (no scroll) */}
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  <span className="rounded bg-slate-600/40 px-2 py-1 text-slate-300">{t('reception.profileFields.identityTier')}: {emptyLabel(selectedPatient?.link_tier ?? selectedPatient?.identity_strength_tier, t, 'unknown')}</span>
                  <span className="rounded bg-slate-600/40 px-2 py-1 text-slate-300">{t('reception.profileFields.financialTier')}: {emptyLabel(selectedPatient?.link_tier ?? selectedFinancialProfile?.financial_profile?.financial_tier, t, 'unknown')}</span>
                  {(selectedPatient?.payment_rows_count ?? selectedFinancialProfile?.financial_profile?.payment_rows_count) != null && (
                    <span className="rounded bg-slate-600/40 px-2 py-1 text-slate-300">{t('reception.profileFields.paymentRowsCount')}: {selectedPatient?.payment_rows_count ?? selectedFinancialProfile?.financial_profile?.payment_rows_count}</span>
                  )}
                  <span className="rounded bg-slate-600/40 px-2 py-1 text-slate-300">{t('reception.summary.firstVisit')}: {emptyLabel(formatJalaliDate(selectedProfile?.first_visit_date ?? selectedPatient?.first_visit_date), t, 'notYetRecorded')}</span>
                  <span className="rounded bg-slate-600/40 px-2 py-1 text-slate-300">{t('reception.summary.lastActivity')}: {emptyLabel(formatJalaliDate(selectedFinancialProfile?.financial_profile?.last_payment_date ?? selectedFinancialProfile?.financial_profile?.last_payment_date_raw ?? selectedPatient?.last_payment_date), t, 'notYetRecorded')}</span>
                </div>
              </div>

              {/* Optional deeper details (below fold); keep basics visible without scrolling */}
              <div className="mt-3 rounded-lg border border-slate-700/60 bg-slate-900/60 p-4">
                <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">{t('reception.patientPrioritySection')}</h4>
                <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                  <div>
                    <p className="text-xs text-slate-500">{t('reception.summary.financialContributionClass')}</p>
                    <p className="mt-1 text-lg font-semibold tabular-nums text-cyan-100" title={t('reception.amountsInRial')}>
                      {formatCurrencyRial(selectedPatient?.total_net_received ?? selectedFinancialProfile?.financial_profile?.net_received_toman ?? selectedFinancialProfile?.financial_profile?.lifetime_net_received, lng)}
                    </p>
                    <p className="mt-0.5 text-[11px] text-slate-500">{t('reception.positiveSum')} / {t('reception.negativeSum')}: {formatCurrencyRial(selectedPatient?.positive_net_received_sum ?? selectedFinancialProfile?.financial_profile?.positive_sum, lng)} / {formatCurrencyRial(selectedPatient?.negative_net_received_sum ?? selectedFinancialProfile?.financial_profile?.negative_sum, lng)}</p>
                  </div>
                  <div>
                    <p className="text-[11px] font-medium uppercase text-slate-500">{t('reception.summary.insuranceSummary')}</p>
                    <p className="mt-0.5 text-sm text-slate-200">
                      {emptyLabel(selectedPatient?.insurance_recent ?? selectedPatient?.insurance_primary ?? selectedPatient?.display_insurer, t, 'unknown')}
                      {(selectedPatient?.insurance_variants_count ?? 0) > 1 && ` · ${t('reception.multipleInsurersRecorded')}`}
                      {getInsuranceClassLabel(selectedPatient?.patient_priority_profile?.insurance_score, t) && (
                        <span className="mr-1 text-cyan-400"> · {getInsuranceClassLabel(selectedPatient.patient_priority_profile.insurance_score, t)}</span>
                      )}
                    </p>
                    <p className="mt-1 text-[11px] text-slate-500">{t('reception.summary.crmProfileStatus')}: {getCrmProfileStatus(selectedPatient?.multi_crm_for_same_patient_flag, t)}</p>
                  </div>
                  <div>
                    <p className="text-[11px] font-medium uppercase text-slate-500">{t('reception.summary.appointmentWindowRecommendation')}</p>
                    {(() => {
                      const pref = getPreferredWindow(selectedPatient?.patient_priority_profile)
                      if (!pref) {
                        return (
                          <p className="mt-0.5 text-sm text-slate-200">
                            {emptyLabel(
                              selectedPatient?.patient_priority_profile?.scheduling_window_days,
                              t,
                              'dash',
                            )}
                          </p>
                        )
                      }
                      const { preferredStartDays, preferredEndDays, allowedEndDays } = pref
                      return (
                        <div className="mt-0.5 space-y-0.5 text-[13px] text-slate-200">
                          <div>
                            <span className="text-slate-400">بهترین بازه پیشنهادی:</span>{' '}
                            <span className="font-medium">
                              {preferredStartDays} تا {preferredEndDays} روز آینده
                            </span>
                          </div>
                          <div>
                            <span className="text-slate-400">بازه قابل‌قبول:</span>{' '}
                            <span className="font-medium">
                              از امروز تا {allowedEndDays} روز آینده
                            </span>
                          </div>
                        </div>
                      )
                    })()}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </SectionCard>

      {/* 3) Horizontal controls row (menus + AI button) */}
      <SectionCard title={t('reception.aiRecommendation')} subtitle={t('reception.aiRecommendationSubtitle')}>
        <div className="grid gap-4 md:grid-cols-4">
          <div>
            <label className="mb-1 block text-xs text-slate-500">{t('reception.service')}</label>
            <select
              value={service}
              onChange={(e) => setService(e.target.value)}
              className="w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-sm text-slate-100"
            >
              <option value="">{t('reception.selectService')}</option>
              {(services ?? []).map((s) => (
                <option key={String(s ?? '')} value={s ?? ''}>{String(s ?? t('reception.notAvailable'))}</option>
              ))}
              {((services ?? []).length === 0) && <option value="" disabled>{t('reception.notAvailable')}</option>}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs text-slate-500">
              {t('reception.insurance')}
              {insuranceLoading && <span className="ml-1 text-slate-400">({LOADING})</span>}
              {insuranceError && !insuranceLoading && <span className="ml-1 text-slate-500 text-[10px]">({insuranceError})</span>}
            </label>
            <select
              value={insurance}
              onChange={(e) => setInsurance(e.target.value)}
              className="w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-sm text-slate-100"
            >
              <option value="CASH">نقد</option>
              {(insurances ?? []).map((opt) => (
                <option key={opt?.id ?? opt?.value ?? 'opt'} value={opt?.value ?? ''}>{opt?.label ?? opt?.value ?? t('reception.notAvailable')}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs text-slate-500">{t('reception.preferredDay')}</label>
            <select
              value={preferredDay}
              onChange={(e) => setPreferredDay(e.target.value)}
              className="w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-sm text-slate-100"
            >
              <option value="">{t('reception.aiDecision')}</option>
              {(DAYS_EN ?? []).map((d) => (
                <option key={d ?? ''} value={d ?? ''}>{t(`reception.days.${d}`)}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs text-slate-500">{t('reception.doctorOptional')}</label>
            <select
              value={selectedDoctor}
              onChange={(e) => setSelectedDoctor(e.target.value)}
              className="w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-sm text-slate-100"
            >
              <option value="">{t('reception.allDoctors')}</option>
            </select>
          </div>
        </div>

        {selectedPatient && !canRecommend && !hasV2Identity(selectedPatient) && (
          <p className="mt-4 text-xs text-amber-400">{t('reception.invalidRecordNo') || 'لطفاً بیمار با شماره پرونده معتبر انتخاب کنید.'}</p>
        )}

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            onClick={handleRecommend}
            disabled={loadingRec || !canRecommend}
            className="flex w-full max-w-xs items-center justify-center gap-2 rounded-lg bg-cyan-500 px-4 py-2.5 text-sm font-medium text-slate-950 transition-colors hover:bg-cyan-400 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {loadingRec ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                {t('loading')}
              </>
            ) : (
              t('reception.getSlots')
            )}
          </button>
          {(recommendationMeta?.patient_priority_profile || recommendationMeta?.preferred_doctor_filter != null) && (
            <p className="text-xs text-slate-500">
              {recommendationMeta.patient_priority_profile && (
                <span>{t('reception.priority.tier')}: {recommendationMeta.patient_priority_profile.patient_priority_tier_label ?? recommendationMeta.patient_priority_profile.patient_priority_tier} · {t('reception.priority.schedulingWindowDays')}: {recommendationMeta.patient_priority_profile.scheduling_window_days}</span>
              )}
              {recommendationMeta.patient_priority_profile && recommendationMeta.preferred_doctor_filter != null && ' · '}
              {recommendationMeta.preferred_doctor_filter != null && (
                <span>{t('reception.doctorFilter')}: {recommendationMeta.preferred_doctor_filter ? t('reception.yes') : t('reception.no')}</span>
              )}
            </p>
          )}
        </div>
      </SectionCard>

      {/* 4) Horizontal AI results (cards in a row) */}
      <SectionCard title={t('reception.aiRecommendation')} subtitle={t('reception.aiRecommendationSubtitle')}>
        {bookingMessage && (
          <p className={`mb-3 text-sm ${bookingMessage === t('reception.bookingSuccess') ? 'text-emerald-400' : 'text-amber-400'}`}>{bookingMessage}</p>
        )}
        {slots.length === 0 && !loadingRec && (
          <EmptyState title={t('reception.noSlots')} message={t('reception.tryDifferentFilters')} />
        )}
        {slots.length > 0 && (
          <div className="flex gap-3 overflow-x-auto pb-2">
            {(slots ?? []).filter(Boolean).map((s, i) => {
              const safe = safeSlot(s)
              const isBest = i === 0
              const isSelected = selectedSlot && safe.slot_id === selectedSlot.slot_id && safe.date === selectedSlot.date && safe.time === selectedSlot.time
              return (
                <div key={safe.slot_id ?? `slot-${i}`} className="min-w-[320px] max-w-[380px] flex-1">
                  <RecommendationCard
                    slot={safe}
                    onSelect={(slot) => setSelectedSlot(slot)}
                    isBest={isBest}
                    isSelected={!!isSelected}
                    showDoctor={recommendationMeta?.preferred_doctor_filter === true}
                    disabled={bookingLoading}
                    actionLabel={isSelected ? t('reception.summaryBox.selectedAction') : t('reception.saveRecommendedSlot')}
                  />
                </div>
              )
            })}
          </div>
        )}
      </SectionCard>

      {/* 5) Finalization row (selected summary + finalized list) */}
      <div className="grid gap-6 lg:grid-cols-2">
        <SectionCard title={t('reception.summaryBox.title')} subtitle={t('reception.summaryBox.subtitle')}>
          <div className="flex flex-col gap-3 rounded-lg border border-slate-800 bg-slate-900/60 p-4 text-sm">
            {!selectedPatient && !selectedSlot && !finalizedBooking && (
              <p className="text-slate-400">
                {t('reception.summaryBox.stateNoSelection')}
              </p>
            )}
            {selectedPatient && !selectedSlot && slots.length > 0 && !finalizedBooking && (
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="text-slate-200">
                  <p className="text-xs text-slate-400">{t('reception.summaryBox.bestReady')}</p>
                  <p className="mt-1 font-medium">
                    {formatJalaliDate(slots[0]?.date || '') || DASH} · {slots[0]?.time || DASH}
                  </p>
                </div>
                <button
                  type="button"
                  className="rounded-lg bg-cyan-500 px-3 py-2 text-xs font-medium text-slate-950 hover:bg-cyan-400"
                  onClick={() => {
                    if (slots[0]) setSelectedSlot(safeSlot(slots[0]))
                  }}
                >
                  {t('reception.summaryBox.selectBest')}
                </button>
              </div>
            )}
            {selectedPatient && selectedSlot && !bookingLoading && !finalizedBooking && (
              <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                <div>
                  <p className="text-xs text-slate-400">{t('reception.summaryBox.stateSelected')}</p>
                  <p className="mt-1 font-medium text-slate-100">
                    {formatJalaliDate(selectedSlot.date || '') || DASH} · {selectedSlot.time || DASH}
                    {selectedSlot.doctor_name && selectedSlot.doctor_name !== '—' && (
                      <span className="text-slate-400"> · {selectedSlot.doctor_name}</span>
                    )}
                  </p>
                  <p className="mt-0.5 text-xs text-slate-500">
                    {t('reception.patient')}: {selectedPatient?.canonical_patient_name ?? selectedPatient?.patient_name_canonical ?? selectedPatient?.patient_name ?? selectedPatient?.name}
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    className="rounded-lg border border-slate-700 px-3 py-2 text-xs text-slate-300 hover:bg-slate-800"
                    onClick={() => setSelectedSlot(null)}
                  >
                    {t('reception.summaryBox.clearSelection')}
                  </button>
                  <button
                    type="button"
                    className="rounded-lg bg-emerald-500 px-3 py-2 text-xs font-medium text-slate-950 hover:bg-emerald-400"
                    onClick={() => handleBookSlot(selectedSlot)}
                    disabled={bookingLoading}
                  >
                    {t('reception.finalBooking')}
                  </button>
                </div>
              </div>
            )}
            {bookingLoading && (
              <p className="text-xs text-slate-400">{t('loading')}</p>
            )}
            {finalizedBooking && (
              <div className="border-t border-slate-800 pt-3">
                <p className="text-xs text-emerald-400">{t('reception.summaryBox.stateFinalized')}</p>
                <p className="mt-1 text-sm text-slate-100">
                  {formatJalaliDate(finalizedBooking.date)} · {finalizedBooking.time}
                  {finalizedBooking.doctor_name && finalizedBooking.doctor_name !== '—' && (
                    <span className="text-slate-400"> · {finalizedBooking.doctor_name}</span>
                  )}
                </p>
                <p className="mt-0.5 text-xs text-slate-500">
                  {t('reception.patient')}: {finalizedBooking.patient_name} · ID #{finalizedBooking.id}
                </p>
                {finalizedBooking?.receptionist_user && (
                  <p className="mt-0.5 text-xs text-slate-500">
                    رسپشن: {finalizedBooking.receptionist_user}
                  </p>
                )}
              </div>
            )}
          </div>
        </SectionCard>

        <SectionCard title={t('reception.finalizedBookingsTitle')} subtitle={t('reception.finalizedBookingsSubtitle')}>
          <div className="space-y-3">
            {selectedRecordKey && finalizedForSelected.length > 0 ? (
              <div className="max-h-72 overflow-y-auto rounded-lg border border-slate-800">
                <table className="w-full text-xs">
                  <thead className="sticky top-0 bg-slate-900/95 text-slate-500">
                    <tr>
                      <th className="px-3 py-2 text-start">ID</th>
                      <th className="px-3 py-2 text-start">{t('reception.date')}</th>
                      <th className="px-3 py-2 text-start">{t('reception.time')}</th>
                      <th className="px-3 py-2 text-start">{t('reception.status')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {finalizedForSelected.map((b) => (
                      <tr key={b.id} className="border-t border-slate-800 text-slate-300">
                        <td className="px-3 py-2">#{b.id}</td>
                        <td className="px-3 py-2">{formatJalaliDate(b.date)}</td>
                        <td className="px-3 py-2">{b.time}</td>
                        <td className="px-3 py-2">{b.status || 'confirmed'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-xs text-slate-500">
                {selectedPatient ? (t('reception.noFinalizedBookings')) : (t('reception.summaryBox.stateNoSelection'))}
              </p>
            )}

            {finalizedList && finalizedList.length > 0 && (
              <div className="border-t border-slate-800 pt-3">
                <p className="mb-2 text-[11px] font-semibold text-slate-500">آخرین ثبت‌ها</p>
                <div className="max-h-40 overflow-y-auto space-y-1 text-[11px] text-slate-400">
                  {(finalizedList || []).slice(0, 10).map((b) => (
                    <div key={b.id} className="flex items-center justify-between gap-2 rounded border border-slate-800 bg-slate-900/40 px-2 py-1">
                      <span className="truncate">#{b.id} · {b.patient_name}</span>
                      <span className="shrink-0">{formatJalaliDate(b.date)} · {b.time}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </SectionCard>
      </div>
    </div>
  )
}
