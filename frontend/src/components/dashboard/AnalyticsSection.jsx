export function AnalyticsSection({ title, subtitle, children }) {
  return (
    <section className="space-y-4">
      {(title || subtitle) && (
        <div>
          <h2 className="text-base font-semibold text-slate-200">{title}</h2>
          {subtitle && <p className="mt-0.5 text-sm text-slate-500">{subtitle}</p>}
        </div>
      )}
      {children}
    </section>
  )
}
