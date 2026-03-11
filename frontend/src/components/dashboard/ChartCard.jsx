export function ChartCard({ title, subtitle, children, className }) {
  return (
    <div
      className={`rounded-xl border border-slate-800 bg-slate-900/50 p-5 shadow-sm ${className || ''}`}
    >
      {(title || subtitle) && (
        <div className="mb-4">
          <h3 className="text-sm font-semibold text-slate-200">{title}</h3>
          {subtitle && <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>}
        </div>
      )}
      <div className="min-h-[180px] py-1">
        {children}
      </div>
    </div>
  )
}
