import { useTranslation } from 'react-i18next'
import { Filter } from 'lucide-react'

export function FilterBar({ filters, onApply, onReset }) {
  const { t } = useTranslation()

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4" dir="auto">
      <div className="mb-3 flex items-center gap-2">
        <Filter className="h-4 w-4 text-slate-400" />
        <span className="text-sm font-medium text-slate-200">{t('manager.filters')}</span>
      </div>
      <div className="flex flex-wrap items-end gap-3">
        {filters}
        <button
          onClick={onApply}
          className="rounded-lg bg-cyan-500 px-4 py-2 text-xs font-medium text-slate-950 hover:bg-cyan-400"
        >
          {t('manager.apply')}
        </button>
        <button
          onClick={onReset}
          className="rounded-lg border border-slate-700 px-4 py-2 text-xs font-medium text-slate-400 hover:bg-slate-800 hover:text-slate-200"
        >
          {t('manager.reset')}
        </button>
      </div>
    </div>
  )
}
