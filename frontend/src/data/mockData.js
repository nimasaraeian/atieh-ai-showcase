export const MOCK_PATIENTS = [
  { record_no: 139990, patient_name: 'علی محمدی', mobile: '09121234567', tier: 'VIP', last_visit: '2025-02-15' },
  { record_no: 139991, patient_name: 'سارا احمدی', mobile: '09129876543', tier: 'HIGH', last_visit: '2025-02-20' },
  { record_no: 139992, patient_name: 'رضا کریمی', mobile: '09121112233', tier: 'MEDIUM', last_visit: '2025-01-10' },
  { record_no: 139993, patient_name: 'مریم رضایی', mobile: '09123334455', tier: 'LOW', last_visit: '2024-12-01' },
]

export const MOCK_TODAY_APPOINTMENTS = [
  { id: 1, time: '09:00', patient: 'علی محمدی', doctor: 'دکتر احمدی', service: 'معاینه', status: 'completed' },
  { id: 2, time: '10:00', patient: 'سارا احمدی', doctor: 'دکتر رضایی', service: 'درمان ریشه', status: 'in_progress' },
  { id: 3, time: '11:00', patient: 'رضا کریمی', doctor: 'دکتر احمدی', service: 'جرمگیری', status: 'pending' },
  { id: 4, time: '14:00', patient: 'مریم رضایی', doctor: 'دکتر محمدی', service: 'معاینه', status: 'pending' },
]

export const MOCK_DOCTOR_SCHEDULE = [
  { time: '09:00', patient: 'علی محمدی', service: 'معاینه', status: 'completed' },
  { time: '10:30', patient: 'سارا احمدی', service: 'درمان ریشه', status: 'in_progress' },
  { time: '12:00', patient: 'رضا کریمی', service: 'جرمگیری', status: 'pending' },
  { time: '14:00', patient: 'مریم رضایی', service: 'معاینه', status: 'pending' },
]

export const MOCK_DASHBOARD_SUMMARY = {
  total_patients: 1250,
  vip_patients: 45,
  high_patients: 120,
  medium_patients: 350,
  low_patients: 735,
}

export const MOCK_APPOINTMENTS_TREND = [
  { day: 'شنبه', count: 42 },
  { day: 'یکشنبه', count: 38 },
  { day: 'دوشنبه', count: 45 },
  { day: 'سه‌شنبه', count: 40 },
  { day: 'چهارشنبه', count: 48 },
  { day: 'پنجشنبه', count: 35 },
]

export const MOCK_DOCTOR_WORKLOAD = [
  { name: 'دکتر احمدی', appointments: 12, utilization: 85 },
  { name: 'دکتر رضایی', appointments: 10, utilization: 72 },
  { name: 'دکتر محمدی', appointments: 8, utilization: 60 },
]

export const MOCK_VIP_PATIENTS = [
  { record_no: 139990, patient_name: 'علی محمدی', tier: 'VIP' },
  { record_no: 139991, patient_name: 'سارا احمدی', tier: 'VIP' },
  { record_no: 139995, patient_name: 'محمد کریمی', tier: 'HIGH' },
]

export const DAYS_EN = ['Saturday', 'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
