import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { PageHeader } from '../components/layout/PageHeader'
import { SectionCard } from '../components/ui/SectionCard'
import { SearchBar } from '../components/ui/SearchBar'
import { StatCard } from '../components/ui/StatCard'
import { EmptyState } from '../components/ui/EmptyState'
import { StatusBadge } from '../components/ui/StatusBadge'
import { RecommendationCard } from '../components/ui/RecommendationCard'
import { atiehApi, API_BASE } from '../services/atiehApi'
import { DAYS_EN } from '../data/mockData'
import { Users, Calendar, Loader2, User } from 'lucide-react'

const TIER_COLORS = { VIP: 'text-amber-400', HIGH: 'text-emerald-400', MEDIUM: 'text-slate-300', LOW: 'text-slate-500' }

export function ReceptionistPage() {
  const { t, i18n } = useTranslation()
  const lng = i18n.language || 'en'
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
  const [preferredDay, setPreferredDay] = useState('Monday')
  const [recommendations, setRecommendations] = useState(null)
  const [loadingRec, setLoadingRec] = useState(false)
  const [todayAppts, setTodayAppts] = useState([])

  useEffect(() => {
    atiehApi
      .getServices()
      .then((r) => setServices(Array.isArray(r) ? r : []))
      .catch(() => setServices([]))
    atiehApi
      .getInsurances()
      .then((r) => {
        if (!Array.isArray(r)) {
          setInsurances([])
          return
        }
        // Normalize to objects with at least a name so we can later
        // show both label and (optionally) financial value if present.
        if (r.length > 0 && typeof r[0] === 'object') {
          setInsurances(
            r.map((item) => ({
              name: item.name ?? item.label ?? item.value ?? String(item.id ?? ''),
              label: item.label ?? item.name ?? item.value ?? String(item.id ?? ''),
              priority_score: typeof item.priority_score === 'number' ? item.priority_score : null,
            }))
          )
        } else {
          setInsurances(r.map((name) => ({ name: String(name), label: String(name), priority_score: null })))
        }
      })
      .catch(() => setInsurances([]))
  }, [])

  useEffect(() => {
    // Load today's appointments from real backend; empty list means no appointments.
    atiehApi
      .getAppointmentsToday()
      .then((r) => {
        if (Array.isArray(r)) {
          setTodayAppts(r)
        } else if (Array.isArray(r.data)) {
          setTodayAppts(r.data)
        } else {
          setTodayAppts([])
        }
      })
      .catch(() => {
        // Backend currently returns an empty list by design; on error, stay empty but UI remains honest.
        setTodayAppts([])
      })
  }, [])

  function isNumericRecordNo(value) {
    const v = String(value ?? '').trim()
    return v !== '' && /^[0-9]+$/.test(v)
  }

  function formatFieldValue(value, mode) {
    if (value === null || value === undefined || value === '') {
      return mode === 'progress' ? 'Ø¯Ø± Ø­Ø§Ù„ ØªÚ©Ù…ÛŒÙ„' : 'Ø«Ø¨Øª Ù†Ø´Ø¯Ù‡'
    }
    return String(value)
  }

  function dedupeAndOrderPatients(rows) {
    if (!Array.isArray(rows)) return []
    const byKey = new Map()
    for (const r of rows) {
      const name = r.patient_name ?? r.patient_name_canonical ?? r.name ?? ''
      const mobile = r.mobile ?? r.mobile_canonical ?? r.phone ?? ''
      const key = `${name}|${mobile}`
      const existing = byKey.get(key)
      const rn = r.record_no ?? r.recordNo ?? null
      const hasNumeric = rn && isNumericRecordNo(rn)
      if (!existing) {
        byKey.set(key, r)
        continue
      }
      const existingRn = existing.record_no ?? existing.recordNo ?? null
      const existingHasNumeric = existingRn && isNumericRecordNo(existingRn)
      if (!existingHasNumeric && hasNumeric) {
        byKey.set(key, r)
      }
    }
    const list = Array.from(byKey.values())
    list.sort((a, b) => {
      const ra = a.record_no ?? a.recordNo ?? ''
      const rb = b.record_no ?? b.recordNo ?? ''
      const na = isNumericRecordNo(ra) ? 1 : 0
      const nb = isNumericRecordNo(rb) ? 1 : 0
      return nb - na
    })
    return list
  }

  function loadSelectedProfile(recordNo) {
    const rn = String(recordNo ?? '').trim()
    if (!isNumericRecordNo(rn)) {
      setSelectedProfile(null)
      setSelectedFinancialProfile(null)
      setProfileError('شماره پرونده معتبر برای این بیمار ثبت نشده است')
      return
    }
    setProfileLoading(true)
    setProfileError(null)

    Promise.allSettled([
      atiehApi.getPatientByRecordNo(rn),
      atiehApi.getFinancialPatientDetail(rn),
    ])
      .then(([baseRes, finRes]) => {
        if (baseRes.status === 'fulfilled') {
          setSelectedProfile(baseRes.value || null)
        } else {
          setSelectedProfile(null)
        }

        if (finRes.status === 'fulfilled') {
          setSelectedFinancialProfile(finRes.value || null)
        } else {
          setSelectedFinancialProfile(null)
        }

        if (baseRes.status !== 'fulfilled') {
          setProfileError((baseRes.reason?.message) || t('error'))
        }
      })
      .catch((err) => {
        setSelectedProfile(null)
        setSelectedFinancialProfile(null)
        setProfileError(err?.message || t('error'))
      })
      .finally(() => setProfileLoading(false))
  }

  function handleSelectPatient(row) {
    const rn = row?.record_no
    if (!isNumericRecordNo(rn)) {
      setSelectedPatient(null)
      setSelectedProfile(null)
    setSelectedFinancialProfile(null)
      setSelectionError('Ø´Ù…Ø§Ø±Ù‡ Ù¾Ø±ÙˆÙ†Ø¯Ù‡ Ù…Ø¹ØªØ¨Ø± Ø¨Ø±Ø§ÛŒ Ø§ÛŒÙ† Ø¨ÛŒÙ…Ø§Ø± Ø«Ø¨Øª Ù†Ø´Ø¯Ù‡ Ø§Ø³Øª')
      setProfileError(null)
      return
    }
    setSelectionError(null)
    setSelectedPatient(row)
    loadSelectedProfile(rn)
  }

  function handleSearch() {
    const q = searchQ.trim()
    if (!q) {
      // Empty query: clear results and keep UI in a neutral state.
      setSearchResults([])
      setSearchCount(0)
      setSearchError(null)
      return
    }

    setSearchLoading(true)
    setSearchError(null)
    setSelectionError(null)
    setSelectedPatient(null)
    setSelectedProfile(null)
    setSelectedFinancialProfile(null)

    atiehApi
      .searchPatients(q)
      .then((r) => {
        const raw = Array.isArray(r?.data) ? r.data : []
        const data = dedupeAndOrderPatients(raw)
        const count = typeof r?.count === 'number' ? r.count : data.length
        setSearchResults(data)
        setSearchCount(count)
      })
      .catch((err) => {
        setSearchResults([])
        setSearchCount(0)
        setSearchError(err?.message || t('error'))
      })
      .finally(() => {
        setSearchLoading(false)
      })
  }

  function handleRecommend() {
    if (!selectedPatient || !selectedPatient.record_no) {
      return
    }
    const rec = selectedPatient.record_no
    setLoadingRec(true)
    setRecommendations(null)
    atiehApi
      .recommendSlot({ record_no: rec, service: service || 'TREATMENT_1', insurance, preferred_day: preferredDay })
      .then((r) => setRecommendations(r.ok ? r.recommendations ?? [] : []))
      .catch(() => setRecommendations([]))
      .finally(() => setLoadingRec(false))
  }

  const patients = searchResults ?? []
  const stats = { today: todayAppts.length }

  const selectedInsuranceObj =
    Array.isArray(insurances) && insurances.length > 0 && typeof insurances[0] === 'object'
      ? insurances.find((i) => (i.name ?? i.label) === insurance)
      : null

  const insuranceOptions = [
    { value: 'CASH', label: t('paymentMethod.cash') },
    ...(
      Array.isArray(insurances)
        ? insurances.map((i) => {
            if (typeof i === 'string') {
              return { value: i, label: i }
            }
            const name = i.name ?? i.label ?? i.value ?? ''
            return { value: name, label: name }
          })
        : []
    ),
  ]

  return (
    <div className="space-y-6" dir={lng === 'fa' ? 'rtl' : 'ltr'}>
      <PageHeader
        title={t('reception.title')}
        subtitle={t('reception.subtitle')}
      />

      <p className="text-[10px] text-slate-500 text-right">
        REACT RECEPTION PATCH ACTIVE â€“ API_BASE: {API_BASE || '(relative / proxy)'}, profile endpoint: /patients/&#123;record_no&#125;
      </p>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title={t('reception.todayAppointments')} value={stats.today} icon={Calendar} accent="cyan" />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <SectionCard title={t('reception.patientSearch')} subtitle={t('reception.patientSearchSubtitle')}>
          <SearchBar
            value={searchQ}
            onChange={setSearchQ}
            onSearch={handleSearch}
            placeholder={t('reception.searchPlaceholder')}
          />
          {searchLoading && (
            <p className="mt-2 text-xs text-slate-500">{t('loading')}</p>
          )}
          {!searchLoading && searchCount != null && (
            <p className="mt-2 text-xs text-slate-500">
              {searchCount === 0
                ? t('reception.noPatientsFound')
                : t('chart.count') + ': ' + searchCount}
            </p>
          )}
          {searchError && (
            <p className="mt-2 text-xs text-red-400">{searchError}</p>
          )}
          {selectionError && (
            <p className="mt-2 text-xs text-red-400">{selectionError}</p>
          )}
          <div className="mt-4 max-h-64 overflow-y-auto rounded-lg border border-slate-800">
            {patients.length === 0 ? (
              <EmptyState
                title={
                  searchQ.trim()
                    ? t('reception.noPatientsFound')
                    : t('empty')
                }
                message={
                  searchQ.trim()
                    ? t('reception.tryDifferentSearch')
                    : t('reception.patientSearchSubtitle')
                }
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
                  {patients.map((p) => {
                    const rn = p.record_no ?? p.recordNo
                    const hasNumeric = isNumericRecordNo(rn)
                    const displayRecordNo = hasNumeric ? rn : 'Ø«Ø¨Øª Ù†Ø´Ø¯Ù‡'
                    const key = `${p.record_no ?? p.recordNo ?? p.patient_name ?? p.name}-${p.mobile ?? p.mobile_canonical ?? ''}`
                    return (
                      <tr
                        key={key}
                        onClick={() => handleSelectPatient({ ...p, record_no: rn })}
                        className={`cursor-pointer border-t border-slate-800 transition-colors hover:bg-slate-800/50 ${
                          selectedPatient?.record_no === p.record_no ? 'bg-cyan-500/10' : ''
                        }`}
                      >
                        <td className="px-4 py-2.5 font-medium text-slate-200">{p.patient_name ?? p.name}</td>
                        <td className="px-4 py-2.5 text-slate-400">{displayRecordNo}</td>
                        <td className="px-4 py-2.5 text-slate-400">{p.mobile ?? p.mobile_canonical}</td>
                        <td className="px-4 py-2.5">
                          <span className={TIER_COLORS[p.financial_tier ?? p.tier] ?? 'text-slate-400'}>
                            {p.financial_tier ?? p.tier ?? '-'}
                          </span>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
          </div>
        </SectionCard>

        <SectionCard title={t('reception.aiRecommendation')} subtitle={t('reception.aiRecommendationSubtitle')}>
          <div className="mb-4 rounded-lg border border-slate-700 bg-slate-800/50 p-3">
            <p className="mb-1 text-xs font-semibold text-slate-400">Ù¾Ø±ÙˆÙØ§ÛŒÙ„ Ø¨ÛŒÙ…Ø§Ø± Ø§Ù†ØªØ®Ø§Ø¨â€ŒØ´Ø¯Ù‡</p>
            {profileLoading && (
              <p className="text-xs text-slate-500">Ø¯Ø± Ø­Ø§Ù„ Ø¨Ø§Ø±Ú¯Ø°Ø§Ø±ÛŒ Ù¾Ø±ÙˆÙØ§ÛŒÙ„ Ø¨ÛŒÙ…Ø§Ø±...</p>
            )}
            {!profileLoading && profileError && (
              <p className="text-xs text-red-400">{profileError}</p>
            )}
            {!profileLoading && !profileError && !selectedProfile && (
              <p className="text-xs text-slate-500">Ù‡Ù†ÙˆØ² Ø¨ÛŒÙ…Ø§Ø±ÛŒ Ø§Ù†ØªØ®Ø§Ø¨ Ù†Ø´Ø¯Ù‡ Ø§Ø³Øª.</p>
            )}
            {!profileLoading && !profileError && selectedProfile && (
              <div className="space-y-1 text-xs text-slate-300">
                <p>
                  <span className="text-slate-500">Ù†Ø§Ù…:</span>{' '}
                  {formatFieldValue(selectedProfile.name ?? selectedProfile.patient_name)}
                </p>
                <p>
                  <span className="text-slate-500">Ø´Ù…Ø§Ø±Ù‡ Ù¾Ø±ÙˆÙ†Ø¯Ù‡:</span>{' '}
                  {formatFieldValue(selectedPatient?.record_no ?? selectedProfile.record_no)}
                </p>
                <p>
                  <span className="text-slate-500">Ù…ÙˆØ¨Ø§ÛŒÙ„:</span>{' '}
                  {formatFieldValue(selectedProfile.phone ?? selectedProfile.mobile)}
                </p>
                <p>
                  <span className="text-slate-500">ID Ø¯Ø§Ø®Ù„ÛŒ:</span>{' '}
                  {formatFieldValue(selectedProfile.id, 'progress')}
                </p>
                <p>
                  <span className="text-slate-500">ØªØ§Ø±ÛŒØ® Ø§ÙˆÙ„ÛŒÙ† Ù…Ø±Ø§Ø¬Ø¹Ù‡:</span>{' '}
                  {formatFieldValue(selectedProfile.first_visit_date, 'progress')}
                </p>
                <p>
                  <span className="text-slate-500">payment_type:</span>{' '}
                  {formatFieldValue(selectedProfile.payment_type, 'progress')}
                </p>
                <p>
                  <span className="text-slate-500">lifetime_value_score:</span>{' '}
                  {formatFieldValue(selectedProfile.lifetime_value_score, 'progress')}
                </p>
              </div>
            )}
          </div>
          <div className="space-y-3">
            <div>
              <label className="mb-1 block text-xs text-slate-500">{t('reception.service')}</label>
              <select
                value={service}
                onChange={(e) => setService(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-sm text-slate-100"
              >
                <option value="">{t('reception.selectService')}</option>
                {services.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs text-slate-500">{t('reception.insurance')}</label>
              <select
                value={insurance}
                onChange={(e) => setInsurance(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-sm text-slate-100"
              >
                <option value="">
                  {t('reception.insurance')}
                </option>
                {insuranceOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
              {selectedInsuranceObj && selectedInsuranceObj.priority_score != null && (
                <p className="mt-1 text-[11px] text-slate-500">
                  {t('reception.insuranceValue', {
                    value: selectedInsuranceObj.priority_score.toFixed(2),
                  })}
                </p>
              )}
            </div>
            <div>
              <label className="mb-1 block text-xs text-slate-500">{t('reception.preferredDay')}</label>
              <select
                value={preferredDay}
                onChange={(e) => setPreferredDay(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-sm text-slate-100"
              >
                {DAYS_EN.map((d) => (
                  <option key={d} value={d}>
                    {t(`reception.days.${d}`)}
                  </option>
                ))}
              </select>
            </div>
            <button
              onClick={handleRecommend}
              disabled={loadingRec || !selectedPatient || !isNumericRecordNo(selectedPatient.record_no)}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-cyan-500 py-2.5 text-sm font-medium text-slate-950 transition-colors hover:bg-cyan-400 disabled:opacity-60"
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
          </div>
          <div className="mt-4 max-h-72 space-y-2 overflow-y-auto">
            {recommendations?.length === 0 && !loadingRec && (
              <EmptyState title={t('reception.noSlots')} message={t('reception.tryDifferentFilters')} />
            )}
            {recommendations?.map((s, i) => (
              <RecommendationCard key={s.slot_id ?? i} slot={s} onBook={(slot) => console.log('Book', slot)} />
            ))}
          </div>
        </SectionCard>
      </div>

      <SectionCard title={t('reception.todayAppointments')} subtitle={t('reception.todaySchedule')}>
        <div className="overflow-x-auto rounded-lg border border-slate-800">
          <table className="w-full text-sm">
            <thead className="bg-slate-800/80 text-start text-xs text-slate-500">
              <tr>
                <th className="px-4 py-3">{t('reception.time')}</th>
                <th className="px-4 py-3">{t('reception.patient')}</th>
                <th className="px-4 py-3">{t('reception.doctor')}</th>
                <th className="px-4 py-3">{t('reception.service')}</th>
                <th className="px-4 py-3">{t('reception.status')}</th>
              </tr>
            </thead>
            <tbody>
              {todayAppts.map((a) => (
                <tr key={a.id} className="border-t border-slate-800 hover:bg-slate-800/30">
                  <td className="px-4 py-2.5 text-slate-200">{a.time}</td>
                  <td className="px-4 py-2.5 text-slate-200">{a.patient}</td>
                  <td className="px-4 py-2.5 text-slate-400">{a.doctor}</td>
                  <td className="px-4 py-2.5 text-slate-400">{a.service}</td>
                  <td className="px-4 py-2.5">
                    <StatusBadge status={a.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionCard>
    </div>
  )
}






