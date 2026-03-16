import { useTranslation } from 'react-i18next'
import { Stethoscope, Calendar, Clock } from 'lucide-react'
import { gregorianToShamsi } from '../../utils/formatters'

export function RecommendationCard({
  slot,
  onSelect,
  onBook,
  showDoctor = true,
  disabled = false,
  actionLabel,
  isBest = false,
  isSelected = false,
}) {
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

  // Relative day label from today (clinic local on frontend)
  let relativeLabel = ''
  if (slot.date) {
    try {
      const [y, m, d] = slot.date.split('-').map(Number)
      const slotDate = new Date(y, (m || 1) - 1, d || 1)
      const today = new Date()
      const oneDayMs = 24 * 60 * 60 * 1000
      const diffDays = Math.round((slotDate.setHours(0, 0, 0, 0) - today.setHours(0, 0, 0, 0)) / oneDayMs)
      if (diffDays === 0) {
        relativeLabel = t('reception.relativeDay.today')
      } else if (diffDays === 1) {
        relativeLabel = t('reception.relativeDay.tomorrow')
      } else if (diffDays > 1) {
        relativeLabel = t('reception.relativeDay.inDays', { count: diffDays })
      } else if (diffDays === -1) {
        relativeLabel = t('reception.relativeDay.yesterday')
      } else if (diffDays < -1) {
        relativeLabel = t('reception.relativeDay.daysAgo', { count: Math.abs(diffDays) })
      }
    } catch {
      relativeLabel = ''
    }
  }

  function mapReason(reason) {
    const r = String(reason || '')
    if (r === 'MULTI_CAPACITY') return t('reception.reasons.multiCapacity')
    if (r === 'IN_PREFERRED_WINDOW') return t('reception.reasons.inPreferredWindow')
    if (r === 'OUTSIDE_PREFERRED_BUT_ALLOWED') return t('reception.reasons.outsidePreferredButAllowed')
    if (r === 'FOLLOWUP_QUEUE') return t('reception.reasons.followupQueue')
    if (r === 'TOP_QUEUE') return t('reception.reasons.topQueue')
    if (r === 'FILTERED_BY_DOCTOR') return t('reception.reasons.filteredByDoctor')
    if (r === 'INSURANCE_OK') return t('reception.reasons.insuranceOk')
    return ''
  }

  const handleClick = () => {
    if (onSelect) onSelect(slot)
    else if (onBook) onBook(slot)
  }

  return (
    <div className={`rounded-xl border bg-slate-900/60 p-4 transition-colors hover:border-cyan-500/40 ${isBest ? 'border-emerald-500/60 shadow-[0_0_0_1px_rgba(16,185,129,0.4)]' : isSelected ? 'border-cyan-500/60' : 'border-slate-800'}`}>
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
            {relativeLabel && (
              <span className="flex items-center gap-1 text-xs text-slate-300">
                {relativeLabel}
              </span>
            )}
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
              {reasons.slice(0, 3).map((reason, idx) => {
                const label = mapReason(reason)
                if (!label) return null
                return (
                  <span
                    key={`${reason}-${idx}`}
                    className="rounded-md border border-slate-700 bg-slate-800 px-2 py-1 text-[11px] text-slate-300"
                  >
                    {label}
                  </span>
                )
              })}
              {(typeof slot?.capacity_count === 'number' && slot.capacity_count > 1) && (
                <span className="rounded-md border border-slate-700 bg-slate-800 px-2 py-1 text-[11px] text-slate-300">
                  {t('reception.capacity')} {slot.capacity_count}
                </span>
              )}
            </div>
          )}
        </div>

        <div className="flex shrink-0 flex-col items-end gap-2">
          {isBest && (
            <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-400">
              {t('reception.bestRecommendation')}
            </span>
          )}
          {showScore && (
            <span className="rounded-lg bg-cyan-500/15 px-2 py-1 text-xs font-medium text-cyan-400">
              {t('reception.aiScore')} {score}%
            </span>
          )}

          <button
            onClick={handleClick}
            disabled={disabled}
            className={`rounded-lg px-3 py-2 text-xs font-medium text-slate-950 transition-colors disabled:opacity-60 disabled:cursor-not-allowed ${
              isSelected ? 'bg-emerald-500 hover:bg-emerald-400' : 'bg-cyan-500 hover:bg-cyan-400'
            }`}
          >
            {actionLabel || t('reception.bookThisSlot')}
          </button>
        </div>
      </div>
    </div>
  )
}
