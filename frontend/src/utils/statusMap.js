/**
 * Maps status values to i18n keys.
 */
export const STATUS_KEYS = {
  completed: 'status.completed',
  pending: 'status.pending',
  cancelled: 'status.cancelled',
  in_progress: 'status.inProgress',
  inProgress: 'status.inProgress',
  no_show: 'status.no_show',
  noshow: 'status.no_show',
}

export function getStatusKey(value) {
  if (!value) return 'status.pending'
  const v = String(value).toLowerCase().replace(/[_-]/g, '')
  const map = { completed: 'status.completed', pending: 'status.pending', cancelled: 'status.cancelled', inprogress: 'status.inProgress', noshow: 'status.no_show' }
  return map[v] || 'status.pending'
}
