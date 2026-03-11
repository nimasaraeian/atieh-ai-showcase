import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Filter, Loader2 } from 'lucide-react'
import { atiehApi } from '../../services/atiehApi'

function toDateStr(d) {
  return d.toISOString().slice(0, 10)
}

function getDateRangeForPreset(preset) {
  const today = new Date()
  const y = today.getFullYear()
  const m = today.getMonth()
  const d = today.getDate()
  switch (preset) {
    case 'today':
      const t = toDateStr(today)
      return { start_date: t, end_date: t }
    case 'this_week': {
      const day = today.getDay()
      const start = new Date(y, m, d - (day === 0 ? 6 : day - 1))
      return { start_date: toDateStr(start), end_date: toDateStr(today) }
    }
    case 'this_month':
      return {
        start_date: toDateStr(new Date(y, m, 1)),
        end_date: toDateStr(today),
      }
    default:
      return {}
  }
}

export function ManagerFilters({ filters, onApply, onReset }) {
  const { t, i18n } = useTranslation()
  const lng = i18n.language || 'en'
  const [dateRange, setDateRange] = useState(filters?.date_range || '')
  const [doctor, setDoctor] = useState(filters?.doctor || '')
  const [service, setService] = useState(filters?.service || '')
  const [payment, setPayment] = useState(filters?.payment || '')
  const [tier, setTier] = useState(filters?.tier || '')
  const [doctors, setDoctors] = useState([])
  const [services, setServices] = useState([])
  const [paymentTypes, setPaymentTypes] = useState([])
  const [tiers, setTiers] = useState([])
  const [loadingOptions, setLoadingOptions] = useState(true)
  const [applying, setApplying] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoadingOptions(true)
    Promise.all([
      atiehApi.getFilterDoctors(),
      atiehApi.getFilterServices(),
      atiehApi.getFilterPaymentTypes(),
      atiehApi.getFilterPatientTiers(),
    ])
      .then(([d, s, p, t]) => {
        if (cancelled) return
        setDoctors(Array.isArray(d?.data) ? d.data : [])
        setServices(Array.isArray(s?.data) ? s.data : [])
        setPaymentTypes(Array.isArray(p?.data) ? p.data : [])
        setTiers(Array.isArray(t?.data) ? t.data : [])
      })
      .catch(() => {
        if (!cancelled) {
          setDoctors([])
          setServices([])
          setPaymentTypes([])
          setTiers([])
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingOptions(false)
      })
    return () => { cancelled = true }
  }, [])

  const handleApply = () => {
    setApplying(true)
    const range = getDateRangeForPreset(dateRange)
    const next = {
      ...range,
      date_range: dateRange || undefined,
      doctor: doctor || undefined,
      service: service || undefined,
      payment: payment || undefined,
      tier: tier || undefined,
    }
    onApply(next)
    setApplying(false)
  }

  const handleReset = () => {
    setDateRange('')
    setDoctor('')
    setService('')
    setPayment('')
    setTier('')
    onReset({})
  }

  const selectClass =
    'w-full min-w-[140px] appearance-none rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-xs text-slate-200 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500 bg-[length:12px] bg-[right_0.5rem_center] bg-no-repeat'

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4" dir={lng === 'fa' ? 'rtl' : 'ltr'}>
      <div className="mb-3 flex items-center gap-2">
        <Filter className="h-4 w-4 shrink-0 text-slate-400" />
        <span className="text-sm font-medium text-slate-200">{t('manager.filters')}</span>
        {loadingOptions && <Loader2 className="h-4 w-4 animate-spin text-slate-500" />}
      </div>
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-0">
          <select
            className={selectClass}
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
            style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2394a3b8'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'/%3E%3C/svg%3E\")" }}
          >
            <option value="">{t('manager.dateRange')}</option>
            <option value="today">{t('manager.dateToday')}</option>
            <option value="this_week">{t('manager.dateThisWeek')}</option>
            <option value="this_month">{t('manager.dateThisMonth')}</option>
            <option value="all">{t('manager.dateAll')}</option>
          </select>
        </div>
        <div className="min-w-0">
          <select
            className={selectClass}
            value={doctor}
            onChange={(e) => setDoctor(e.target.value)}
            style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2394a3b8'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'/%3E%3C/svg%3E\")" }}
          >
            <option value="">{t('manager.all')} - {t('manager.doctor')}</option>
            {doctors.map((v) => (
              <option key={v} value={v}>
                {v}
              </option>
            ))}
          </select>
        </div>
        <div className="min-w-0">
          <select
            className={selectClass}
            value={service}
            onChange={(e) => setService(e.target.value)}
            style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2394a3b8'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'/%3E%3C/svg%3E\")" }}
          >
            <option value="">{t('manager.all')} - {t('manager.service')}</option>
            {services.map((v) => (
              <option key={v} value={v}>
                {v}
              </option>
            ))}
          </select>
        </div>
        <div className="min-w-0">
          <select
            className={selectClass}
            value={payment}
            onChange={(e) => setPayment(e.target.value)}
            style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2394a3b8'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'/%3E%3C/svg%3E\")" }}
          >
            <option value="">{t('manager.all')} - {t('manager.paymentType')}</option>
            {paymentTypes.map((v) => (
              <option key={v} value={v}>
                {v}
              </option>
            ))}
          </select>
        </div>
        <div className="min-w-0">
          <select
            className={selectClass}
            value={tier}
            onChange={(e) => setTier(e.target.value)}
            style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2394a3b8'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'/%3E%3C/svg%3E\")" }}
          >
            <option value="">{t('manager.all')} - {t('manager.patientTier')}</option>
            {tiers.map((v) => (
              <option key={v} value={v}>
                {v}
              </option>
            ))}
          </select>
        </div>
        <button
          onClick={handleApply}
          disabled={applying}
          className="flex shrink-0 items-center gap-2 rounded-lg bg-cyan-500 px-4 py-2 text-xs font-medium text-slate-950 hover:bg-cyan-400 disabled:opacity-70"
        >
          {applying ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          {t('manager.apply')}
        </button>
        <button
          onClick={handleReset}
          className="shrink-0 rounded-lg border border-slate-700 px-4 py-2 text-xs font-medium text-slate-400 hover:bg-slate-800 hover:text-slate-200"
        >
          {t('manager.reset')}
        </button>
      </div>
    </div>
  )
}
