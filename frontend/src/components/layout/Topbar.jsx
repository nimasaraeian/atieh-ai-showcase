import { LanguageSwitcher } from '../ui/LanguageSwitcher'

export function Topbar({ title, subtitle, actions }) {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between gap-4 border-b border-slate-800 bg-slate-900/30 px-6">
      <div className="min-w-0 flex-1">
        <h1 className="text-base font-semibold text-slate-100">{title}</h1>
        {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
      </div>
      <div className="flex shrink-0 items-center gap-3">
        {actions}
        <LanguageSwitcher />
      </div>
    </header>
  )
}
