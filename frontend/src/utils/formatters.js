/**
 * Locale-aware formatting for Manager Dashboard.
 * Uses current i18n language for digit/currency display.
 */

import { toJalaali } from 'jalaali-js'

const CURRENCY_UNITS = { fa: 'تومان', en: 'Toman' }

export function getLocale(lng) {
  return lng === 'fa' ? 'fa-IR' : 'en-US'
}

export function getDigitLocale(lng) {
  return lng === 'fa' ? 'fa-IR' : 'en-US'
}

/**
 * Format currency. Returns value + unit for display.
 * @param {number|null|undefined} n
 * @param {string} lng - 'en' | 'fa'
 * @param {boolean} compact - use compact notation (e.g. ۱۲.۵M) for large values
 */
export function formatCurrency(n, lng = 'en', compact = false) {
  if (n == null || n === undefined) return '—'
  if (typeof n !== 'number' || isNaN(n)) return '—'
  const locale = getDigitLocale(lng)
  const unit = CURRENCY_UNITS[lng] || CURRENCY_UNITS.en
  if (compact && Math.abs(n) >= 1e6) {
    const val = n / 1e6
    const s = new Intl.NumberFormat(locale, { maximumFractionDigits: 1, minimumFractionDigits: 0 }).format(val)
    return lng === 'fa' ? `${s} میلیون ${unit}` : `${s}M ${unit}`
  }
  const s = new Intl.NumberFormat(locale, { maximumFractionDigits: 0, minimumFractionDigits: 0 }).format(Math.round(n))
  return `${s} ${unit}`
}

/**
 * Format count (integers).
 */
export function formatCount(n, lng = 'en') {
  if (n == null || n === undefined) return '—'
  if (typeof n !== 'number') return String(n)
  return new Intl.NumberFormat(getDigitLocale(lng)).format(Math.round(n))
}

/**
 * Format percent.
 */
export function formatPercent(n, lng = 'en', decimals = 1) {
  if (n == null || n === undefined) return '—'
  if (typeof n !== 'number') return String(n)
  return new Intl.NumberFormat(getDigitLocale(lng), {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(n) + '%'
}

/**
 * Compact value for chart axes (e.g. 8M instead of 8000000).
 * Business-readable, no decimals for large values unless needed.
 */
export function formatAxisValue(n, lng = 'en') {
  if (n == null || n === undefined) return ''
  const num = Number(n)
  if (isNaN(num)) return ''
  const locale = getDigitLocale(lng)
  if (Math.abs(num) >= 1e9) {
    const v = num / 1e9
    return new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(v) + 'B'
  }
  if (Math.abs(num) >= 1e6) {
    const v = num / 1e6
    return new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(v) + 'M'
  }
  if (Math.abs(num) >= 1e3) {
    const v = num / 1e3
    return new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(v) + 'K'
  }
  return new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(num)
}

/**
 * Short format for large numbers: 1K, 1M, 1B, 1T.
 * Used for KPI cards to prevent overflow.
 * @param {number|null|undefined} n
 * @param {string} lng - 'en' | 'fa'
 * @returns {{ short: string, full: string }} short for display, full for tooltip
 */
export function formatNumberShort(n, lng = 'en') {
  if (n == null || n === undefined) return { short: '—', full: '—' }
  const num = Number(n)
  if (isNaN(num)) return { short: '—', full: '—' }
  const locale = getDigitLocale(lng)
  const full = new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(Math.round(num))
  const abs = Math.abs(num)
  const suf = lng === 'fa' ? { K: ' هزار', M: ' میلیون', B: ' میلیارد', T: ' تریلیون' } : { K: 'K', M: 'M', B: 'B', T: 'T' }
  let short
  if (abs >= 1e12) {
    const v = num / 1e12
    short = new Intl.NumberFormat(locale, { minimumFractionDigits: 0, maximumFractionDigits: 2 }).format(v) + suf.T
  } else if (abs >= 1e9) {
    const v = num / 1e9
    short = new Intl.NumberFormat(locale, { minimumFractionDigits: 0, maximumFractionDigits: 2 }).format(v) + suf.B
  } else if (abs >= 1e6) {
    const v = num / 1e6
    short = new Intl.NumberFormat(locale, { minimumFractionDigits: 0, maximumFractionDigits: 2 }).format(v) + suf.M
  } else if (abs >= 1e3) {
    const v = num / 1e3
    short = new Intl.NumberFormat(locale, { minimumFractionDigits: 0, maximumFractionDigits: 1 }).format(v) + suf.K
  } else {
    short = new Intl.NumberFormat(locale).format(Math.round(num))
  }
  return { short, full }
}

/**
 * Currency in short form with unit. For KPI cards.
 * @returns {{ short: string, full: string }} e.g. short: "2.09T تومان", full: "2,087,779,737,461 تومان"
 */
export function formatCurrencyShort(n, lng = 'en') {
  const { short: s, full: f } = formatNumberShort(n, lng)
  if (s === '—' || f === '—') return { short: '—', full: '—' }
  const unit = CURRENCY_UNITS[lng] || CURRENCY_UNITS.en
  return { short: `${s} ${unit}`, full: `${f} ${unit}` }
}

/**
 * Currency without unit (for tooltips, inline).
 */
export function formatCurrencyValue(n, lng = 'en') {
  if (n == null || n === undefined) return '—'
  if (typeof n !== 'number' || isNaN(n)) return '—'
  return new Intl.NumberFormat(getDigitLocale(lng), { maximumFractionDigits: 0 }).format(Math.round(n))
}

export { CURRENCY_UNITS }

/**
 * Convert Gregorian date string (YYYY-MM-DD) to Shamsi (YYYY/MM/DD).
 * @param {string} ymd - e.g. "2025-03-11"
 * @returns {string} e.g. "1404/12/20" or empty string on failure
 */
export function gregorianToShamsi(ymd) {
  if (!ymd || typeof ymd !== 'string') return ''
  const parts = ymd.trim().split('-')
  if (parts.length !== 3) return ''
  try {
    const [y, m, d] = parts.map(Number)
    if (isNaN(y) || isNaN(m) || isNaN(d)) return ''
    const j = toJalaali(y, m, d)
    return `${j.jy}/${String(j.jm).padStart(2, '0')}/${String(j.jd).padStart(2, '0')}`
  } catch {
    return ''
  }
}
