import { cn } from '../../utils/cn'

export function PageHeader({ title, subtitle, action }) {
  return (
    <div className={cn('mb-6 flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between')}>
      <div>
        <h1 className="text-xl font-semibold text-slate-100">{title}</h1>
        {subtitle && <p className="mt-0.5 text-sm text-slate-500">{subtitle}</p>}
      </div>
      {action && <div className="mt-2 sm:mt-0">{action}</div>}
    </div>
  )
}
