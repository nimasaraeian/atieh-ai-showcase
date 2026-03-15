import { useTranslation } from 'react-i18next'
import { Stethoscope, Calendar, Clock } from 'lucide-react'
import { gregorianToShamsi } from '../../utils/formatters'

export function RecommendationCard({ slot, onBook, showDoctor = true, disabled = false, actionLabel }) {
  const { t } = useTranslation()
  const scoreRaw = slot.final_score ?? slot.score
  const score = typeof scoreRaw === 'number' && scoreRaw >= 0 && scoreRaw <= 1
    ? Math.round(scoreRaw * 100)
    : null
  const showScore = score != null && score >= 0 && score <= 100

  const reasons = Array.isArray(slot.reasons) ? slot.reasons : []
  const weekdayDisplay = slot.weekday_en
    ? t(`reception.days.${slot.weekday_en}`)
    : (slot.weekday || '')
  const dateShamsi = slot.date ? gregorianToShamsi(slot.date) : ''
  const datePart = [weekdayDisplay, dateShamsi].filter(Boolean).join(' ')
  const dateTimeLine = datePart ? (slot.time ? `${datePart} — ${slot.time}` : datePart) : slot.time || ''

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 transition-colors hover:border-cyan-500/40">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 space-y-2">
          {showDoctor && (slot.doctor_name != null && slot.doctor_name !== '') ? (
            <div className="flex items-center gap-2">
              <Stethoscope className="h-4 w-4 shrink-0 text-cyan-400" />
              <span className="font-medium text-slate-200">{slot.doctor_name}</span>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Calendar className="h-4 w-4 shrink-0 text-cyan-400" />
              <span className="font-medium text-slate-200">{t('reception.suggestedTime')}</span>
            </div>
          )}

          <div className="flex flex-wrap gap-3 text-sm text-slate-400">
            <span className="flex items-center gap-1">
              <Calendar className="h-3.5 w-3.5 shrink-0" />
              {dateTimeLine || weekdayDisplay || '—'}
            </span>
            {slot.time && (
              <span className="flex items-center gap-1">
                <Clock className="h-3.5 w-3.5 shrink-0" />
                {slot.time}
              </span>
            )}
          </div>

          {slot.floor && (
            <p className="text-xs text-slate-500">
              {slot.floor}
              {slot.unit && ` · ${slot.unit}`}
            </p>
          )}

          {reasons.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-2">
              {reasons.map((reason, idx) => (
                <span
                  key={`${reason}-${idx}`}
                  className="rounded-md border border-slate-700 bg-slate-800 px-2 py-1 text-[11px] text-slate-300"
                >
                  {reason}
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="flex shrink-0 flex-col items-end gap-2">
          {showScore && (
            <span className="rounded-lg bg-cyan-500/15 px-2 py-1 text-xs font-medium text-cyan-400">
              {t('reception.aiScore')} {score}%
            </span>
          )}

          <button
            onClick={() => onBook?.(slot)}
            disabled={disabled}
            className="rounded-lg bg-cyan-500 px-3 py-2 text-xs font-medium text-slate-950 transition-colors hover:bg-cyan-400 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {actionLabel || t('reception.bookThisSlot')}
          </button>
        </div>
      </div>
    </div>
  )
}
