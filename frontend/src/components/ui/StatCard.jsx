import { cn } from '../../utils/cn'

export function StatCard({ title, value, subtitle, icon: Icon, accent }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 shadow-sm">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500">{title}</p>
          <p className="mt-1 text-2xl font-semibold text-slate-100">{value}</p>
          {subtitle && <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>}
        </div>
        {Icon && (
          <div
            className={cn(
              'flex h-10 w-10 items-center justify-center rounded-lg',
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
