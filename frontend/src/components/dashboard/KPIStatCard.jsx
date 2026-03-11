import { cn } from '../../utils/cn'

/**
 * KPI card with icon, title, value, optional subtitle.
 * Supports valueTooltip for full value on hover (when display is abbreviated).
 */
export function KPIStatCard({ title, value, subtitle, icon: Icon, accent, valueTooltip }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 shadow-sm min-w-0">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500">{title}</p>
          <p
            className="metric-value mt-1 text-[28px] font-bold text-slate-100"
            title={valueTooltip || (typeof value === 'string' ? value : undefined)}
          >
            {value}
          </p>
          {subtitle && <p className="mt-0.5 truncate text-xs text-slate-500">{subtitle}</p>}
        </div>
        {Icon && (
          <div
            className={cn(
              'flex h-10 w-10 shrink-0 items-center justify-center rounded-lg',
              accent === 'cyan' && 'bg-cyan-500/15 text-cyan-400',
              accent === 'green' && 'bg-emerald-500/15 text-emerald-400',
              accent === 'amber' && 'bg-amber-500/15 text-amber-400',
              accent === 'red' && 'bg-red-500/15 text-red-400',
              !accent && 'bg-slate-800 text-slate-400'
            )}
          >
            <Icon className="h-5 w-5" />
          </div>
        )}
      </div>
    </div>
  )
}
