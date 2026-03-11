/**
 * Maps backend payment_method / payer_source_norm to i18n keys.
 */
export const PAYMENT_METHOD_KEYS = {
  cash: 'paymentMethod.cash',
  card: 'paymentMethod.card',
  insurance: 'paymentMethod.insurance',
  transfer: 'paymentMethod.transfer',
  installment: 'paymentMethod.installment',
  mixed: 'paymentMethod.mixed',
  unknown: 'paymentMethod.unknown',
}

export function getPaymentMethodKey(value) {
  if (!value) return 'paymentMethod.unknown'
  const v = String(value).toLowerCase().trim()
  return PAYMENT_METHOD_KEYS[v] || PAYMENT_METHOD_KEYS.unknown
}
