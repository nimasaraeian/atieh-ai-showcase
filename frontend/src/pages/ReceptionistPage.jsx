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
import { formatCurrency } from '../utils/formatters'

const NOT_RECORDED = 'ثبت نشده'
const IN_PROGRESS = 'در حال تکمیل'
const LOADING = 'در حال بارگذاری'
const NOT_AVAILABLE = 'موجود نیست'

function isNumericRecordNo(value) {
  const v = String(value ?? '').trim()
  if (v === '' || v === '-') return false
  return /^[0-9]+$/.test(v)
}

function formatFieldValue(value, mode) {
  if (value === null || value === undefined || value === '') {
    return mode === 'progress' ? IN_PROGRESS : NOT_RECORDED
  }
  return String(value)
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
  const [recommendations, setRecommendations] = useState(null)
  const [loadingRec, setLoadingRec] = useState(false)

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
        setInsuranceError(NOT_AVAILABLE)
      })
      .finally(() => setInsuranceLoading(false))
  }, [])

  function handleSearch() {
    const q = String(searchQ ?? '').trim()
    if (!q) {
      setSearchResults([])
      setSearchCount(0)
      setSearchError(null)
      return
    }
    setSearchLoading(true)
    setSearchError(null)
    atiehApi
      .searchPatients(q)
      .then((r) => {
        const raw = Array.isArray(r?.data) ? r.data : []
        const count = typeof r?.count === 'number' ? r.count : raw.length
        setSearchResults(raw)
        setSearchCount(count)
      })
      .catch((err) => {
        setSearchResults([])
        setSearchCount(0)
        setSearchError(err?.message || t('error') || 'Search failed')
      })
      .finally(() => setSearchLoading(false))
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
      })
      .catch((err) => {
        setSelectedProfile(null)
        setSelectedFinancialProfile(null)
        setProfileError(err?.message || t('error') || 'Failed to load profile')
      })
      .finally(() => setProfileLoading(false))
  }

  function handleSelectPatient(row) {
    const rn = row?.record_no ?? row?.recordNo
    if (!row || !isNumericRecordNo(rn)) {
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
  }

  function handleRecommend() {
    const rec = selectedPatient?.record_no ?? ''
    if (!selectedPatient || !isNumericRecordNo(rec)) return
    setLoadingRec(true)
    setRecommendations(null)
    atiehApi
      .recommendSlot({
        record_no: rec,
        service: service || 'TREATMENT_1',
        insurance: insurance || 'CASH',
        preferred_day: preferredDay || null,
      })
      .then((r) => {
        const list = (r && r.ok) ? (Array.isArray(r.recommendations) ? r.recommendations : []) : []
        setRecommendations(list)
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

  const patients = searchResults ?? []
  const slots = recommendations ?? []
  const recNo = selectedPatient?.record_no ?? ''
  const canRecommend = selectedPatient && isNumericRecordNo(recNo)

  return (
    <div className="space-y-6" dir={lng === 'fa' ? 'rtl' : 'ltr'}>
      <PageHeader
        title={t('reception.title')}
        subtitle={t('reception.subtitle')}
      />
      <SectionCard title="Status" subtitle="Search + Profile + Service & Insurance + Slots">
        <p className="text-slate-200">Receptionist Page Loaded</p>
      </SectionCard>
      <div className="grid gap-6 lg:grid-cols-2">
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
              {searchCount === 0 ? t('reception.noPatientsFound') : `${t('chart.count') || 'Count'}: ${searchCount}`}
            </p>
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
                    <th className="px-4 py-3">{t('reception.tier')}</th>
                  </tr>
                </thead>
                <tbody>
                  {(patients ?? []).filter(Boolean).map((p, idx) => {
                    const rn = p?.record_no ?? p?.recordNo
                    const isSelected = selectedPatient && (selectedPatient?.record_no === rn || selectedPatient?.record_no === p?.record_no)
                    return (
                      <tr
                        key={`${rn ?? idx}-${p?.mobile ?? idx}`}
                        onClick={() => handleSelectPatient({ ...p, record_no: rn })}
                        className={`cursor-pointer border-t border-slate-800 transition-colors hover:bg-slate-800/50 ${isSelected ? 'bg-cyan-500/10' : ''}`}
                      >
                        <td className="px-4 py-2.5 font-medium text-slate-200">{p?.patient_name ?? p?.name ?? '-'}</td>
                        <td className="px-4 py-2.5 text-slate-400">{rn ?? '-'}</td>
                        <td className="px-4 py-2.5 text-slate-400">{p?.mobile ?? p?.mobile_canonical ?? p?.phone ?? '-'}</td>
                        <td className="px-4 py-2.5 text-slate-400">{p?.financial_tier ?? p?.tier ?? '-'}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
          </div>
        </SectionCard>
        <SectionCard title={t('reception.selectedPatientProfile')} subtitle="">
          <div className="rounded-lg border border-slate-700 bg-slate-800/50 p-3">
            {profileLoading && <p className="text-xs text-slate-500">{t('reception.loadingProfile')}</p>}
            {!profileLoading && profileError && <p className="text-xs text-red-400">{profileError}</p>}
            {!profileLoading && !profileError && !selectedPatient && (
              <p className="text-xs text-slate-500">{t('reception.noPatientSelected')}</p>
            )}
            {!profileLoading && !profileError && selectedPatient && (
              <div className="space-y-1 text-xs text-slate-300">
                <p><span className="text-slate-500">{t('reception.profileFields.name')}:</span> {selectedProfile?.name ?? selectedProfile?.patient_name ?? selectedPatient?.patient_name ?? selectedPatient?.name ?? NOT_RECORDED}</p>
                <p><span className="text-slate-500">{t('reception.profileFields.recordNo')}:</span> {selectedPatient?.record_no ?? selectedProfile?.record_no ?? NOT_RECORDED}</p>
                <p><span className="text-slate-500">{t('reception.profileFields.mobile')}:</span> {selectedProfile?.phone ?? selectedProfile?.mobile ?? selectedPatient?.mobile ?? selectedPatient?.mobile_canonical ?? NOT_RECORDED}</p>
                <p><span className="text-slate-500">{t('reception.profileFields.internalId')}:</span> {formatFieldValue(selectedProfile?.id, 'progress')}</p>
                <p><span className="text-slate-500">{t('reception.profileFields.firstVisitDate')}:</span> {formatFieldValue(selectedProfile?.first_visit_date, 'progress')}</p>
                <p><span className="text-slate-500">{t('reception.profileFields.paymentType')}:</span> {getPaymentTypeLabel(selectedFinancialProfile?.financial_profile) ?? NOT_RECORDED}</p>
                <p><span className="text-slate-500">{t('reception.profileFields.patientValueScore')}:</span> {selectedFinancialProfile?.financial_profile?.financial_value_score != null ? String(selectedFinancialProfile?.financial_profile?.financial_value_score) : NOT_RECORDED}</p>
                <p><span className="text-slate-500">{t('reception.profileFields.financialTier')}:</span> {selectedFinancialProfile?.financial_profile?.financial_tier ?? NOT_RECORDED}</p>
                <p><span className="text-slate-500">{t('reception.profileFields.totalReceived')}:</span> {selectedFinancialProfile?.financial_profile?.lifetime_net_received != null ? formatCurrency(selectedFinancialProfile?.financial_profile?.lifetime_net_received, lng) : NOT_RECORDED}</p>
                <p><span className="text-slate-500">{t('reception.profileFields.lastPayment')}:</span> {selectedFinancialProfile?.financial_profile?.last_payment_date_raw ?? NOT_RECORDED}</p>
                <p><span className="text-slate-500">{t('reception.profileFields.inFollowupQueue')}:</span> {selectedFinancialProfile?.operational_status?.in_followup_queue === true ? (t('reception.yes') || 'بله') : (t('reception.no') || 'خیر')}</p>
                <p><span className="text-slate-500">{t('reception.profileFields.followupType')}:</span> {selectedFinancialProfile?.operational_status?.followup_action_type ?? NOT_RECORDED}</p>
                <p><span className="text-slate-500">{t('reception.profileFields.inTop300')}:</span> {selectedFinancialProfile?.operational_status?.in_scheduling_top300 === true ? (t('reception.yes') || 'بله') : (t('reception.no') || 'خیر')}</p>
                <p><span className="text-slate-500">{t('reception.profileFields.priorityBand')}:</span> {selectedFinancialProfile?.operational_status?.scheduling_band ?? NOT_RECORDED}</p>
                <p><span className="text-slate-500">{t('reception.profileFields.schedulingPriorityScore')}:</span> {selectedFinancialProfile?.operational_status?.scheduling_priority_score != null ? String(selectedFinancialProfile?.operational_status?.scheduling_priority_score) : NOT_RECORDED}</p>
              </div>
            )}
          </div>
        </SectionCard>
      </div>
      <SectionCard title={t('reception.aiRecommendation')} subtitle={t('reception.aiRecommendationSubtitle')}>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-xs text-slate-500">{t('reception.service')}</label>
            <select
              value={service}
              onChange={(e) => setService(e.target.value)}
              className="w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-sm text-slate-100"
            >
              <option value="">{t('reception.selectService')}</option>
              {(services ?? []).map((s) => (
                <option key={String(s ?? '')} value={s ?? ''}>{String(s ?? NOT_AVAILABLE)}</option>
              ))}
              {((services ?? []).length === 0) && <option value="" disabled>{NOT_AVAILABLE}</option>}
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
                <option key={opt?.id ?? opt?.value ?? 'opt'} value={opt?.value ?? ''}>{opt?.label ?? opt?.value ?? NOT_AVAILABLE}</option>
              ))}
            </select>
          </div>
        </div>
        <div className="mt-4">
          <label className="mb-1 block text-xs text-slate-500">{t('reception.preferredDay')}</label>
          <select
            value={preferredDay}
            onChange={(e) => setPreferredDay(e.target.value)}
            className="w-full max-w-xs rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-sm text-slate-100"
          >
            <option value="">{t('reception.aiDecision')}</option>
            {(DAYS_EN ?? []).map((d) => (
              <option key={d ?? ''} value={d ?? ''}>{t(`reception.days.${d}`)}</option>
            ))}
          </select>
        </div>
        {selectedPatient && !canRecommend && (
          <p className="mt-4 text-xs text-amber-400">{t('reception.invalidRecordNo') || 'لطفاً بیمار با شماره پرونده معتبر انتخاب کنید.'}</p>
        )}
        <button
          onClick={handleRecommend}
          disabled={loadingRec || !canRecommend}
          className="mt-4 flex w-full max-w-xs items-center justify-center gap-2 rounded-lg bg-cyan-500 py-2.5 text-sm font-medium text-slate-950 transition-colors hover:bg-cyan-400 disabled:opacity-60 disabled:cursor-not-allowed"
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
        <div className="mt-4 max-h-72 space-y-2 overflow-y-auto">
          {slots.length === 0 && !loadingRec && (
            <EmptyState title={t('reception.noSlots')} message={t('reception.tryDifferentFilters')} />
          )}
          {(slots ?? []).filter(Boolean).map((s, i) => (
            <RecommendationCard
              key={s?.slot_id ?? `slot-${i}`}
              slot={safeSlot(s)}
              onBook={() => {}}
            />
          ))}
        </div>
      </SectionCard>
    </div>
  )
}
