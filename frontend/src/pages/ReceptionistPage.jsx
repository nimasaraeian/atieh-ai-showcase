import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { PageHeader } from '../components/layout/PageHeader'
import { SectionCard } from '../components/ui/SectionCard'
import { SearchBar } from '../components/ui/SearchBar'
import { StatCard } from '../components/ui/StatCard'
import { EmptyState } from '../components/ui/EmptyState'
import { StatusBadge } from '../components/ui/StatusBadge'
import { RecommendationCard } from '../components/ui/RecommendationCard'
import { atiehApi } from '../services/atiehApi'
import {
  MOCK_PATIENTS,
  MOCK_TODAY_APPOINTMENTS,
  DAYS_EN,
} from '../data/mockData'
import { Users, Calendar, Loader2, User } from 'lucide-react'

const TIER_COLORS = { VIP: 'text-amber-400', HIGH: 'text-emerald-400', MEDIUM: 'text-slate-300', LOW: 'text-slate-500' }

export function ReceptionistPage() {
  const { t, i18n } = useTranslation()
  const lng = i18n.language || 'en'
  const [searchQ, setSearchQ] = useState('')
  const [searchResults, setSearchResults] = useState(null)
  const [selectedPatient, setSelectedPatient] = useState(null)
  const [services, setServices] = useState([])
  const [insurances, setInsurances] = useState([])
  const [service, setService] = useState('')
  const [insurance, setInsurance] = useState('CASH')
  const [preferredDay, setPreferredDay] = useState('Monday')
  const [recommendations, setRecommendations] = useState(null)
  const [loadingRec, setLoadingRec] = useState(false)
  const [todayAppts, setTodayAppts] = useState(MOCK_TODAY_APPOINTMENTS)

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

  function handleSearch() {
    if (!searchQ.trim()) {
      setSearchResults(MOCK_PATIENTS)
      return
    }
    atiehApi
      .searchPatients(searchQ)
      .then((r) => setSearchResults(r.data ?? []))
      .catch(() => setSearchResults(MOCK_PATIENTS.filter((p) => p.patient_name?.includes(searchQ) || p.record_no?.toString().includes(searchQ))))
  }

  function handleRecommend() {
    const rec = selectedPatient?.record_no ?? 139990
    setLoadingRec(true)
    setRecommendations(null)
    atiehApi
      .recommendSlot({ record_no: rec, service: service || 'TREATMENT_1', insurance, preferred_day: preferredDay })
      .then((r) => setRecommendations(r.ok ? r.recommendations ?? [] : []))
      .catch(() => setRecommendations([]))
      .finally(() => setLoadingRec(false))
  }

  const patients = searchResults ?? MOCK_PATIENTS
  const stats = { today: todayAppts.length, waiting: 2, vip: 3, doctors: 4 }

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

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title={t('reception.todayAppointments')} value={stats.today} icon={Calendar} accent="cyan" />
        <StatCard title={t('reception.waiting')} value={stats.waiting} icon={Users} accent="amber" />
        <StatCard title={t('reception.vipArrivals')} value={stats.vip} icon={User} accent="green" />
        <StatCard title={t('reception.doctorsAvailable')} value={stats.doctors} icon={User} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <SectionCard title={t('reception.patientSearch')} subtitle={t('reception.patientSearchSubtitle')}>
          <SearchBar
            value={searchQ}
            onChange={setSearchQ}
            onSearch={handleSearch}
            placeholder={t('reception.searchPlaceholder')}
          />
          <div className="mt-4 max-h-64 overflow-y-auto rounded-lg border border-slate-800">
            {patients.length === 0 ? (
              <EmptyState title={t('reception.noPatientsFound')} message={t('reception.tryDifferentSearch')} />
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
                  {patients.map((p) => (
                    <tr
                      key={p.record_no}
                      onClick={() => setSelectedPatient(p)}
                      className={`cursor-pointer border-t border-slate-800 transition-colors hover:bg-slate-800/50 ${
                        selectedPatient?.record_no === p.record_no ? 'bg-cyan-500/10' : ''
                      }`}
                    >
                      <td className="px-4 py-2.5 font-medium text-slate-200">{p.patient_name ?? p.name}</td>
                      <td className="px-4 py-2.5 text-slate-400">{p.record_no}</td>
                      <td className="px-4 py-2.5 text-slate-400">{p.mobile ?? p.mobile_canonical}</td>
                      <td className="px-4 py-2.5">
                        <span className={TIER_COLORS[p.financial_tier ?? p.tier] ?? 'text-slate-400'}>
                          {p.financial_tier ?? p.tier ?? '-'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </SectionCard>

        <SectionCard title={t('reception.aiRecommendation')} subtitle={t('reception.aiRecommendationSubtitle')}>
          {selectedPatient && (
            <div className="mb-4 rounded-lg border border-slate-700 bg-slate-800/50 p-3">
              <p className="text-sm font-medium text-slate-200">{selectedPatient.patient_name ?? selectedPatient.name}</p>
              <p className="text-xs text-slate-500">{t('reception.recordNo')} #{selectedPatient.record_no}</p>
            </div>
          )}
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
              disabled={loadingRec}
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
