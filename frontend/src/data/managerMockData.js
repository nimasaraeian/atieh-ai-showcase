export const MOCK_DASHBOARD_SUMMARY = {
  total_patients: 1250,
  total_revenue: 485000000,
  total_transactions: 3420,
  active_doctors: 4,
  vip_patients: 45,
  no_show_rate: 4.2,
}

export const MOCK_REVENUE_TREND = [
  { month: 'فروردین', value: 72 },
  { month: 'اردیبهشت', value: 78 },
  { month: 'خرداد', value: 85 },
  { month: 'تیر', value: 90 },
  { month: 'مرداد', value: 88 },
  { month: 'شهریور', value: 92 },
]

export const MOCK_MONTHLY_REVENUE = [
  { month: 'فروردین', revenue: 42000000 },
  { month: 'اردیبهشت', revenue: 48000000 },
  { month: 'خرداد', revenue: 52000000 },
  { month: 'تیر', revenue: 55000000 },
  { month: 'مرداد', revenue: 51000000 },
  { month: 'شهریور', revenue: 58000000 },
]

export const MOCK_PAYMENT_DISTRIBUTION = [
  { name: 'Cash', value: 45, color: '#10b981' },
  { name: 'Card', value: 35, color: '#06b6d4' },
  { name: 'Insurance', value: 20, color: '#f59e0b' },
]

export const MOCK_DEBT_VS_COLLECTED = [
  { name: 'Collected', value: 460000000 },
  { name: 'Outstanding', value: 25000000 },
]

export const MOCK_REVENUE_BY_DOCTOR = [
  { name: 'دکتر احمدی', revenue: 185000000 },
  { name: 'دکتر رضایی', revenue: 142000000 },
  { name: 'دکتر محمدی', revenue: 98000000 },
  { name: 'دکتر کریمی', revenue: 60000000 },
]

export const MOCK_REVENUE_BY_SERVICE = [
  { name: 'درمان ریشه', revenue: 120000000 },
  { name: 'ایمپلنت', revenue: 95000000 },
  { name: 'جرمگیری', revenue: 45000000 },
  { name: 'معاینه', revenue: 38000000 },
  { name: 'سایر', revenue: 87000000 },
]

export const MOCK_FINANCIAL_SUMMARY = {
  today_revenue: 12500000,
  weekly_revenue: 72000000,
  monthly_revenue: 58000000,
  total_collected: 460000000,
  outstanding_debt: 25000000,
  discounts: 8500000,
  refunds: 1200000,
}

export const MOCK_PATIENT_GROWTH = [
  { month: 'فروردین', count: 98 },
  { month: 'اردیبهشت', count: 112 },
  { month: 'خرداد', count: 128 },
  { month: 'تیر', count: 135 },
  { month: 'مرداد', count: 118 },
  { month: 'شهریور', count: 142 },
]

export const MOCK_NEW_VS_RETURNING = [
  { name: 'New', value: 28 },
  { name: 'Returning', value: 72 },
]

export const MOCK_TIER_DISTRIBUTION = [
  { name: 'VIP', value: 45, color: '#f59e0b' },
  { name: 'High', value: 120, color: '#10b981' },
  { name: 'Medium', value: 350, color: '#06b6d4' },
  { name: 'Low', value: 735, color: '#64748b' },
]

export const MOCK_VISIT_FREQUENCY = [
  { range: '1-2 visits', count: 420 },
  { range: '3-5 visits', count: 380 },
  { range: '6-10 visits', count: 220 },
  { range: '10+ visits', count: 230 },
]

export const MOCK_VIP_PATIENTS = [
  { record_no: 139990, patient_name: 'علی محمدی', tier: 'VIP' },
  { record_no: 139991, patient_name: 'سارا احمدی', tier: 'VIP' },
  { record_no: 139995, patient_name: 'محمد کریمی', tier: 'HIGH' },
]

export const MOCK_TOP_PATIENTS = [
  { record_no: 139990, patient_name: 'علی محمدی', tier: 'VIP', revenue: 45000000 },
  { record_no: 139991, patient_name: 'سارا احمدی', tier: 'VIP', revenue: 32000000 },
  { record_no: 139995, patient_name: 'محمد کریمی', tier: 'HIGH', revenue: 28000000 },
]

export const MOCK_INACTIVE_PATIENTS = [
  { record_no: 139988, patient_name: 'فاطمه زارعی', last_visit: '1402/06/15' },
  { record_no: 139989, patient_name: 'حسین نوری', last_visit: '1402/05/20' },
]

export const MOCK_TRANSACTION_STATS = {
  total: 3420,
  successful: 3280,
  failed: 140,
  cash_pct: 45,
  insurance_pct: 55,
  avg_value: 141800,
}

export const MOCK_TRANSACTION_TREND = [
  { day: 'شنبه', count: 95 },
  { day: 'یکشنبه', count: 88 },
  { day: 'دوشنبه', count: 102 },
  { day: 'سه‌شنبه', count: 98 },
  { day: 'چهارشنبه', count: 110 },
  { day: 'پنجشنبه', count: 72 },
]

export const MOCK_TRANSACTIONS = [
  { id: 1001, patient_name: 'علی محمدی', record_no: 139990, date: '1403/06/15', amount: 2500000, payment: 'Cash', service: 'درمان ریشه', doctor: 'دکتر احمدی', status: 'completed' },
  { id: 1002, patient_name: 'سارا احمدی', record_no: 139991, date: '1403/06/15', amount: 1800000, payment: 'Card', service: 'ایمپلنت', doctor: 'دکتر رضایی', status: 'completed' },
  { id: 1003, patient_name: 'رضا کریمی', record_no: 139992, date: '1403/06/14', amount: 450000, payment: 'Insurance', service: 'جرمگیری', doctor: 'دکتر محمدی', status: 'completed' },
  { id: 1004, patient_name: 'مریم رضایی', record_no: 139993, date: '1403/06/14', amount: 350000, payment: 'Cash', service: 'معاینه', doctor: 'دکتر احمدی', status: 'pending' },
]

export const MOCK_DOCTOR_WORKLOAD = [
  { name: 'دکتر احمدی', appointments: 12, utilization: 85, revenue: 185000000, completion: 92, cancellation: 3 },
  { name: 'دکتر رضایی', appointments: 10, utilization: 72, revenue: 142000000, completion: 88, cancellation: 5 },
  { name: 'دکتر محمدی', appointments: 8, utilization: 60, revenue: 98000000, completion: 90, cancellation: 4 },
  { name: 'دکتر کریمی', appointments: 6, utilization: 55, revenue: 60000000, completion: 85, cancellation: 6 },
]

export const MOCK_APPOINTMENTS_TREND = [
  { day: 'شنبه', count: 42, completed: 38, cancelled: 2, pending: 2 },
  { day: 'یکشنبه', count: 38, completed: 35, cancelled: 1, pending: 2 },
  { day: 'دوشنبه', count: 45, completed: 42, cancelled: 2, pending: 1 },
  { day: 'سه‌شنبه', count: 40, completed: 37, cancelled: 1, pending: 2 },
  { day: 'چهارشنبه', count: 48, completed: 44, cancelled: 2, pending: 2 },
  { day: 'پنجشنبه', count: 35, completed: 32, cancelled: 1, pending: 2 },
]

export const MOCK_PEAK_HOURS = [
  { hour: '09-10', count: 12 },
  { hour: '10-11', count: 18 },
  { hour: '11-12', count: 22 },
  { hour: '12-13', count: 8 },
  { hour: '14-15', count: 15 },
  { hour: '15-16', count: 20 },
]

export const MOCK_RECENT_APPOINTMENTS = [
  { id: 1, time: '09:00', patient: 'علی محمدی', doctor: 'دکتر احمدی', service: 'معاینه', status: 'completed' },
  { id: 2, time: '10:00', patient: 'سارا احمدی', doctor: 'دکتر رضایی', service: 'درمان ریشه', status: 'in_progress' },
  { id: 3, time: '11:00', patient: 'رضا کریمی', doctor: 'دکتر احمدی', service: 'جرمگیری', status: 'pending' },
]

export const MOCK_DEBTORS = [
  { record_no: 139987, patient_name: 'احمد صادقی', amount: 2500000 },
  { record_no: 139986, patient_name: 'زهرا موسوی', amount: 1800000 },
]
