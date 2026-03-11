import { useTranslation } from 'react-i18next'
import { cn } from '../../utils/cn'
import { getStatusKey } from '../../utils/statusMap'

const STATUS_STYLES = {
  completed: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  in_progress: 'bg-cyan-500/15 text-cyan-400 border-cyan-500/30',
  inProgress: 'bg-cyan-500/15 text-cyan-400 border-cyan-500/30',
  pending: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
  cancelled: 'bg-red-500/15 text-red-400 border-red-500/30',
  no_show: 'bg-red-500/15 text-red-400 border-red-500/30',
  default: 'bg-slate-500/15 text-slate-400 border-slate-500/30',
}

const TIER_STYLES = {
  VIP: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
  HIGH: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  MEDIUM: 'bg-cyan-500/15 text-cyan-400 border-cyan-500/30',
  LOW: 'bg-slate-500/15 text-slate-400 border-slate-500/30',
}

export function StatusBadge({ status, tier }) {
  const { t } = useTranslation()
  const key = tier ? `tier.${String(status || '').toUpperCase()}` : getStatusKey(status)
  const style = tier ? (TIER_STYLES[String(status || '').toUpperCase()] ?? TIER_STYLES.LOW) : (STATUS_STYLES[status] ?? STATUS_STYLES.default)
  return (
    <span className={cn('inline-flex rounded-md border px-2 py-0.5 text-xs font-medium', style)}>
      {t(key)}
    </span>
  )
}
