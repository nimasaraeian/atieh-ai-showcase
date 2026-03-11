import { useTranslation } from 'react-i18next'
import { formatCurrencyValue, formatCount } from '../../utils/formatters'

/**
 * Recharts custom Tooltip with i18n support.
 * Handles: labelKey (translation key for value), valueFormatter.
 */
export function DashboardTooltip({ active, payload, label, labelKey = 'chart.total', valueFormatter }) {
  const { t, i18n } = useTranslation()
  const lng = i18n.language || 'en'

  if (!active || !payload?.length) return null

  const fmt = valueFormatter || ((v) => (typeof v === 'number' && (v >= 1000 || v < 1)) ? formatCount(v, lng) : formatCurrencyValue(v, lng))

  return (
    <div
      className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 shadow-lg"
      style={{ direction: lng === 'fa' ? 'rtl' : 'ltr' }}
    >
      {label && <p className="mb-1 text-xs text-slate-400">{label}</p>}
      {payload.map((entry, i) => (
        <div key={i} className="flex items-center justify-between gap-4 text-sm">
          <span className="text-slate-300" style={{ color: entry.color }}>
            {entry.name || t(labelKey)}
          </span>
          <span className="font-medium text-slate-100">
            {typeof entry.value === 'number' ? fmt(entry.value) : entry.value}
          </span>
        </div>
      ))}
    </div>
  )
}
