import { useTranslation } from 'react-i18next'
import { Stethoscope, Calendar, Clock } from 'lucide-react'
import { cn } from '../../utils/cn'

export function RecommendationCard({ slot, onBook }) {
  const { t } = useTranslation()
  const score = slot.score != null ? Math.round(slot.score * 100) : null
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 transition-colors hover:border-cyan-500/40">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 space-y-2">
          <div className="flex items-center gap-2">
            <Stethoscope className="h-4 w-4 shrink-0 text-cyan-400" />
            <span className="font-medium text-slate-200">{slot.doctor_name}</span>
          </div>
          <div className="flex flex-wrap gap-3 text-sm text-slate-400">
            <span className="flex items-center gap-1">
              <Calendar className="h-3.5 w-3.5" />
              {slot.weekday ? t(`reception.days.${slot.weekday}`) : ''}
            </span>
            <span className="flex items-center gap-1">
              <Clock className="h-3.5 w-3.5" />
              {slot.time}
            </span>
          </div>
          {slot.floor && (
            <p className="text-xs text-slate-500">
              {slot.floor}
              {slot.unit && ` · ${slot.unit}`}
            </p>
          )}
        </div>
        <div className="flex shrink-0 flex-col items-end gap-2">
          {score != null && (
            <span className="rounded-lg bg-cyan-500/15 px-2 py-1 text-xs font-medium text-cyan-400">
              {t('reception.score')} {score}%
            </span>
          )}
          <button
            onClick={() => onBook?.(slot)}
            className="rounded-lg bg-cyan-500 px-3 py-2 text-xs font-medium text-slate-950 transition-colors hover:bg-cyan-400"
          >
            {t('reception.bookThisSlot')}
          </button>
        </div>
      </div>
    </div>
  )
}
