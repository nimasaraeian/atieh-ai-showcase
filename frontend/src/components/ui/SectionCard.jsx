import { cn } from '../../utils/cn'

export function SectionCard({ title, subtitle, children, className }) {
  return (
    <section className={cn('rounded-xl border border-slate-800 bg-slate-900/50 p-5 shadow-sm', className)}>
      {(title || subtitle) && (
        <div className="mb-4">
          <h2 className="text-sm font-semibold text-slate-200">{title}</h2>
          {subtitle && <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>}
        </div>
      )}
      {children}
    </section>
  )
}
