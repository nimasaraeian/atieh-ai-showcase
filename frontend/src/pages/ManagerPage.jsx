import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { PageHeader } from '../components/layout/PageHeader'
import { SectionCard } from '../components/ui/SectionCard'
import { StatusBadge } from '../components/ui/StatusBadge'
import {
  KPIStatCard,
  ChartCard,
  AnalyticsSection,
  ManagerFilters,
  ReportTable,
} from '../components/dashboard'
import { DashboardTooltip } from '../components/dashboard/DashboardTooltip'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  Legend,
} from 'recharts'
import {
  TrendingUp,
  Users,
  DollarSign,
  Activity,
  FileText,
  Download,
  Loader2,
  AlertCircle,
} from 'lucide-react'
import { atiehApi } from '../services/atiehApi'
import {
  formatCurrency,
  formatCount,
  formatPercent,
  formatAxisValue,
  formatCurrencyValue,
  formatNumberShort,
  formatCurrencyShort,
} from '../utils/formatters'
import { getPaymentMethodKey } from '../utils/paymentMethodMap'

const CHART_COLORS = ['#06b6d4', '#10b981', '#f59e0b', '#6366f1', '#8b5cf6']

export function ManagerPage() {
  const { t, i18n } = useTranslation()
  const lng = i18n.language || 'en'
  const [filters, setFilters] = useState({})
  const [kpis, setKpis] = useState({
    total_patients: null,
    total_revenue: null,
    total_transactions: null,
    active_doctors: null,
    vip_patients: null,
    no_show_rate: null,
    utilization: null,
  })
  const [paymentDistribution, setPaymentDistribution] = useState([])
  const [revenueTrend, setRevenueTrend] = useState([])
  const [topPatients, setTopPatients] = useState([])
  const [financialSummary, setFinancialSummary] = useState(null)
  const [transactionStats, setTransactionStats] = useState(null)
  const [tierDistribution, setTierDistribution] = useState([])
  const [transactionTrend, setTransactionTrend] = useState([])
  const [revenueByService, setRevenueByService] = useState([])
  const [topServices, setTopServices] = useState([])
  const [revenueByDoctor, setRevenueByDoctor] = useState([])
  const [doctorWorkload, setDoctorWorkload] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    const load = async () => {
      const f = filters
      try {
        const [tp, tr, txn, vp, nsr, util, ad, pd, rt, tv, fs, ts, td, ttr, rbs, tsvc, rbd, dwl] = await Promise.allSettled([
          atiehApi.getTotalPatients(f),
          atiehApi.getTotalRevenue(f),
          atiehApi.getTotalTransactions(f),
          atiehApi.getVipPatientsCount(),
          atiehApi.getNoShowRate(f),
          atiehApi.getDoctorUtilization(f),
          atiehApi.getActiveDoctors(),
          atiehApi.getPaymentDistribution(f),
          atiehApi.getRevenueTrend(90, f),
          atiehApi.getTopValuePatients(10, f),
          atiehApi.getFinancialSummary(f),
          atiehApi.getTransactionStats(f),
          atiehApi.getTierDistribution(f),
          atiehApi.getTransactionTrend(30, f),
          atiehApi.getRevenueByService(15, f),
          atiehApi.getTopServices(15, f),
          atiehApi.getRevenueByDoctor(15, f),
          atiehApi.getDoctorWorkload(15, f),
        ])
        setKpis({
          total_patients: tp.status === 'fulfilled' ? tp.value.total_patients : null,
          total_revenue: tr.status === 'fulfilled' ? tr.value.total_revenue : null,
          total_transactions: txn.status === 'fulfilled' ? txn.value.total_transactions : null,
          vip_patients: vp.status === 'fulfilled' ? vp.value.vip_patients : null,
          no_show_rate: nsr.status === 'fulfilled' ? nsr.value.no_show_rate : null,
          utilization: util.status === 'fulfilled' ? util.value.utilization : null,
          active_doctors: ad.status === 'fulfilled' ? ad.value.active_doctors : null,
        })
        setPaymentDistribution(pd.status === 'fulfilled' && Array.isArray(pd.value?.data) ? pd.value.data.map((r, i) => ({ ...r, color: CHART_COLORS[i % CHART_COLORS.length], value: r.percent })) : [])
        setRevenueTrend(rt.status === 'fulfilled' && Array.isArray(rt.value?.data) ? rt.value.data.map((r) => ({ day: r.day, total: r.total })) : [])
        setTopPatients(tv.status === 'fulfilled' && Array.isArray(tv.value?.data) ? tv.value.data : [])
        setFinancialSummary(fs.status === 'fulfilled' ? fs.value : null)
        setTransactionStats(ts.status === 'fulfilled' ? ts.value : null)
        setTierDistribution(td.status === 'fulfilled' && Array.isArray(td.value?.data) ? td.value.data : [])
        setTransactionTrend(ttr.status === 'fulfilled' && Array.isArray(ttr.value?.data) ? ttr.value.data : [])
        const rbsData = rbs.status === 'fulfilled' && Array.isArray(rbs.value?.data) ? rbs.value.data.map((r) => ({ name: r.service, revenue: r.revenue })) : []
        setRevenueByService(rbsData)
        const tsvcData = tsvc.status === 'fulfilled' && Array.isArray(tsvc.value?.data) ? tsvc.value.data.map((r) => ({ name: r.service, count: r.count })) : []
        setTopServices(tsvcData)
        const rbdData = rbd.status === 'fulfilled' && Array.isArray(rbd.value?.data) ? rbd.value.data.map((r) => ({ name: r.doctor_name, revenue: r.revenue })) : []
        setRevenueByDoctor(rbdData)
        const dwlData = dwl.status === 'fulfilled' && Array.isArray(dwl.value?.data) ? dwl.value.data.map((r) => ({ name: r.doctor_name, workload: r.appointment_count })) : []
        setDoctorWorkload(dwlData)
      } catch (e) {
        setError(e?.message || 'Failed to load dashboard')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [filters])

  const vipList = topPatients.length ? topPatients : []
  const paymentPieData = Array.isArray(paymentDistribution) && paymentDistribution.length
    ? paymentDistribution.map((r, i) => ({
        name: t(getPaymentMethodKey(r.payment_method || r.name)),
        value: r.percent ?? r.value ?? r.count ?? 0,
        color: r.color || CHART_COLORS[i % CHART_COLORS.length],
      }))
    : []

  if (loading) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-slate-400">
          <Loader2 className="h-10 w-10 animate-spin" />
          <p>{t('loading')}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6" dir={lng === 'fa' ? 'rtl' : 'ltr'}>
      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-amber-500/50 bg-amber-500/10 px-4 py-3 text-amber-400">
          <AlertCircle className="h-5 w-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}
      <PageHeader
        title={t('manager.title')}
        subtitle={t('manager.subtitle')}
        action={
          <div className="flex gap-2">
            <button className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800/50 px-3 py-2 text-xs font-medium text-slate-500 cursor-not-allowed" disabled title={t('exportComingSoon')}>
              <Download className="h-4 w-4" />
              {t('manager.exportCsv')}
            </button>
            <button className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800/50 px-3 py-2 text-xs font-medium text-slate-500 cursor-not-allowed" disabled title={t('exportComingSoon')}>
              <Download className="h-4 w-4" />
              {t('manager.exportExcel')}
            </button>
            <button className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800/50 px-3 py-2 text-xs font-medium text-slate-500 cursor-not-allowed" disabled title={t('exportComingSoon')}>
              <Download className="h-4 w-4" />
              {t('manager.exportPdf')}
            </button>
          </div>
        }
      />

      <ManagerFilters
        filters={filters}
        onApply={(f) => setFilters(f)}
        onReset={() => setFilters({})}
      />

      {/* 1) Executive KPI Row - Real data from API */}
      <section>
        <div className="grid gap-4 grid-cols-[repeat(auto-fit,minmax(220px,1fr))]">
          <KPIStatCard title={t('kpi.totalPatients')} value={formatNumberShort(kpis.total_patients, lng).short} valueTooltip={formatNumberShort(kpis.total_patients, lng).full} icon={Users} accent="cyan" />
          <KPIStatCard title={t('kpi.totalRevenue')} value={formatCurrencyShort(kpis.total_revenue, lng).short} valueTooltip={formatCurrencyShort(kpis.total_revenue, lng).full} icon={DollarSign} accent="green" />
          <KPIStatCard title={t('kpi.totalTransactions')} value={formatNumberShort(kpis.total_transactions, lng).short} valueTooltip={formatNumberShort(kpis.total_transactions, lng).full} icon={FileText} accent="cyan" />
          <KPIStatCard title={t('kpi.activeDoctors')} value={formatCount(kpis.active_doctors, lng)} icon={Activity} accent="amber" />
          <KPIStatCard title={t('kpi.vipPatients')} value={formatNumberShort(kpis.vip_patients, lng).short} valueTooltip={formatNumberShort(kpis.vip_patients, lng).full} icon={Users} accent="green" />
          <KPIStatCard title={t('kpi.noShowRate')} value={formatPercent(kpis.no_show_rate, lng, 1)} icon={TrendingUp} accent="red" />
          <KPIStatCard title={t('doctors.workload')} value={formatPercent(kpis.utilization, lng, 1)} icon={Activity} accent="amber" />
        </div>
      </section>

      {/* 2) Financial Analytics */}
      <AnalyticsSection title={t('financial.title')}>
        <div className="grid gap-4 rounded-xl border border-slate-800 bg-slate-900/30 p-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-lg bg-slate-800/50 p-3">
            <p className="text-xs text-slate-500">{t('financial.today')}</p>
            <p className="text-lg font-semibold text-cyan-400">{formatCurrency(financialSummary?.today_revenue ?? 0, lng)}</p>
          </div>
          <div className="rounded-lg bg-slate-800/50 p-3">
            <p className="text-xs text-slate-500">{t('financial.weekly')}</p>
            <p className="text-lg font-semibold text-slate-200">{formatCurrency(financialSummary?.weekly_revenue ?? 0, lng)}</p>
          </div>
          <div className="rounded-lg bg-slate-800/50 p-3">
            <p className="text-xs text-slate-500">{t('financial.totalCollected')}</p>
            <p className="text-lg font-semibold text-emerald-400">{formatCurrency(financialSummary?.total_collected ?? kpis.total_revenue ?? 0, lng)}</p>
          </div>
          <div className="rounded-lg bg-slate-800/50 p-3">
            <p className="text-xs text-slate-500">{t('financial.outstandingDebt')} <span className="text-slate-600">({t('dataRange')})</span></p>
            <p className="text-lg font-semibold text-amber-400">{formatCurrency(financialSummary?.outstanding_debt ?? 0, lng)}</p>
          </div>
        </div>
        <div className="mt-4 grid gap-6 lg:grid-cols-2">
          <ChartCard title={t('financial.revenueTrend')} subtitle={t('dataRange')}>
            <div className="h-56">
              {revenueTrend.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={revenueTrend} margin={{ top: 8, right: 12, left: 12, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="day" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                  <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} tickFormatter={(v) => formatAxisValue(v, lng)} />
                  <Tooltip content={<DashboardTooltip valueFormatter={(v) => formatCurrencyValue(v, lng)} labelKey="chart.revenue" />} />
                  <Line type="monotone" dataKey="total" stroke="#06b6d4" strokeWidth={2} dot={{ fill: '#06b6d4' }} name={t('chart.revenue')} />
                </LineChart>
              </ResponsiveContainer>
              ) : (
                <div className="flex h-56 items-center justify-center text-slate-500">{t('empty')}</div>
              )}
            </div>
          </ChartCard>
          <ChartCard title={t('financial.paymentDistribution')}>
            <div className="h-56">
              {paymentPieData.length ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart margin={{ top: 12, right: 12, left: 12, bottom: 12 }}>
                    <Pie data={paymentPieData} cx="50%" cy="50%" innerRadius={50} outerRadius={75} paddingAngle={2} dataKey="value" label={false}>
                      {paymentPieData.map((e, i) => (
                        <Cell key={i} fill={e.color} name={e.name} />
                      ))}
                    </Pie>
                    <Tooltip content={<DashboardTooltip valueFormatter={(v) => formatPercent(v, lng, 1)} labelKey="chart.percent" />} />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex h-56 items-center justify-center text-slate-500">{t('empty')}</div>
              )}
            </div>
          </ChartCard>
          <ChartCard title={t('financial.revenueByDoctor')} subtitle={revenueByDoctor.length ? t('dataRange') : t('comingSoon')}>
            <div className="h-56">
              {revenueByDoctor.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={revenueByDoctor} layout="vertical" margin={{ top: 8, right: 12, left: 12, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 11 }} tickFormatter={(v) => formatAxisValue(v, lng)} />
                  <YAxis dataKey="name" type="category" width={90} tick={{ fill: '#94a3b8', fontSize: 11 }} />
                  <Tooltip content={<DashboardTooltip valueFormatter={(v) => formatCurrencyValue(v, lng)} labelKey="chart.revenue" />} />
                  <Bar dataKey="revenue" fill="#06b6d4" radius={[0, 4, 4, 0]} name={t('chart.revenue')} />
                </BarChart>
              </ResponsiveContainer>
              ) : (
                <div className="flex h-56 items-center justify-center text-slate-500">{t('comingSoon')}</div>
              )}
            </div>
          </ChartCard>
          <ChartCard title={t('financial.revenueByService')} subtitle={revenueByService.length ? t('dataRange') : t('comingSoon')}>
            <div className="h-56">
              {revenueByService.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={revenueByService} margin={{ top: 8, right: 12, left: 12, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                  <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} tickFormatter={(v) => formatAxisValue(v, lng)} />
                  <Tooltip content={<DashboardTooltip valueFormatter={(v) => formatCurrencyValue(v, lng)} labelKey="chart.revenue" />} />
                  <Bar dataKey="revenue" fill="#10b981" radius={[4, 4, 0, 0]} name={t('chart.revenue')} />
                </BarChart>
              </ResponsiveContainer>
              ) : (
                <div className="flex h-56 items-center justify-center text-slate-500">{t('comingSoon')}</div>
              )}
            </div>
          </ChartCard>
        </div>
      </AnalyticsSection>

      {/* 3) Patient Analytics */}
      <AnalyticsSection title={t('patients.title')}>
        <div className="grid gap-6 lg:grid-cols-2">
          <ChartCard title={t('patients.growth')} subtitle={t('comingSoon')}>
            <div className="h-48 flex items-center justify-center text-slate-500">{t('comingSoon')}</div>
          </ChartCard>
          <ChartCard title={t('patients.tierDistribution')}>
            <div className="h-48">
              {tierDistribution.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart margin={{ top: 12, right: 12, left: 12, bottom: 12 }}>
                  <Pie data={tierDistribution.map((e) => ({ ...e, name: t(`tier.${String(e.name || '').toUpperCase()}`) }))} cx="50%" cy="50%" innerRadius={40} outerRadius={70} paddingAngle={2} dataKey="value" label={false}>
                    {tierDistribution.map((e, i) => (
                      <Cell key={i} fill={e.color || CHART_COLORS[i % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip content={<DashboardTooltip valueFormatter={(v) => formatCount(v, lng)} labelKey="chart.count" />} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
              ) : (
                <div className="flex h-48 items-center justify-center text-slate-500">{t('empty')}</div>
              )}
            </div>
          </ChartCard>
        </div>
      </AnalyticsSection>

      {/* 4) Transaction Analytics */}
      <AnalyticsSection title={t('transactions.title')}>
        <div className="mb-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
          <div className="rounded-lg border border-slate-800 bg-slate-800/30 p-3">
            <p className="text-xs text-slate-500">{t('transactions.total')}</p>
            <p className="text-lg font-semibold text-slate-200">{formatCount(transactionStats?.total ?? kpis.total_transactions ?? 0, lng)}</p>
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-800/30 p-3">
            <p className="text-xs text-slate-500">{t('transactions.successful')}</p>
            <p className="text-lg font-semibold text-emerald-400">{formatCount(transactionStats?.successful ?? kpis.total_transactions ?? 0, lng)}</p>
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-800/30 p-3">
            <p className="text-xs text-slate-500">{t('transactions.failed')}</p>
            <p className="text-lg font-semibold text-amber-400">{formatCount(transactionStats?.failed ?? 0, lng)}</p>
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-800/30 p-3">
            <p className="text-xs text-slate-500">{t('transactions.cashVsInsurance')}</p>
            <p className="text-sm font-medium text-slate-300">{formatPercent(transactionStats?.cash_pct ?? 0, lng, 0)} / {formatPercent(transactionStats?.insurance_pct ?? 0, lng, 0)}</p>
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-800/30 p-3">
            <p className="text-xs text-slate-500">{t('transactions.avgValue')}</p>
            <p className="text-lg font-semibold text-cyan-400">
              {transactionStats?.avg_value != null
                ? formatCurrency(transactionStats.avg_value, lng)
                : kpis.total_revenue != null && kpis.total_transactions != null && kpis.total_transactions > 0
                  ? formatCurrency(Math.round(kpis.total_revenue / kpis.total_transactions), lng)
                  : formatCurrency(0, lng)}
            </p>
          </div>
        </div>
        <ChartCard title={t('transactions.trend')}>
          <div className="h-48">
            {transactionTrend.length ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={transactionTrend} margin={{ top: 8, right: 12, left: 12, bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="day" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} tickFormatter={(v) => formatAxisValue(v, lng)} />
                <Tooltip content={<DashboardTooltip valueFormatter={(v) => formatCount(v, lng)} labelKey="chart.count" />} />
                <Bar dataKey="count" fill="#06b6d4" radius={[4, 4, 0, 0]} name={t('chart.count')} />
              </BarChart>
            </ResponsiveContainer>
            ) : (
              <div className="flex h-48 items-center justify-center text-slate-500">{t('empty')}</div>
            )}
          </div>
        </ChartCard>
        <div className="mt-4">
          <SectionCard title={t('tables.recentTransactions')} subtitle={t('comingSoon')}>
            <div className="flex h-24 items-center justify-center text-slate-500">{t('comingSoon')}</div>
          </SectionCard>
        </div>
      </AnalyticsSection>

      {/* 5) Doctor Performance */}
      <AnalyticsSection title={t('doctors.title')}>
        <div className="grid gap-6 lg:grid-cols-2">
          <ChartCard title={t('doctors.workload')} subtitle={doctorWorkload.length ? t('services.byCount') : t('comingSoon')}>
            <div className="h-56">
              {doctorWorkload.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={doctorWorkload} margin={{ top: 8, right: 12, left: 12, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                  <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} tickFormatter={(v) => formatAxisValue(v, lng)} />
                  <Tooltip content={<DashboardTooltip valueFormatter={(v) => formatCount(v, lng)} labelKey="chart.count" />} />
                  <Bar dataKey="workload" fill="#6366f1" name={t('chart.count')} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
              ) : (
                <div className="flex h-56 items-center justify-center text-slate-500">{t('comingSoon')}</div>
              )}
            </div>
          </ChartCard>
          <ChartCard title={t('doctors.revenue')} subtitle={revenueByDoctor.length ? t('dataRange') : t('comingSoon')}>
            {revenueByDoctor.length ? (
            <div className="space-y-2">
              {revenueByDoctor.map((d, i) => (
                <div key={i} className="flex items-center justify-between rounded-lg border border-slate-800 p-3">
                  <span className="font-medium text-slate-200">{d.name}</span>
                  <span className="text-slate-400">{formatCurrency(d.revenue, lng)}</span>
                </div>
              ))}
            </div>
            ) : (
              <div className="flex h-48 items-center justify-center text-slate-500">{t('comingSoon')}</div>
            )}
          </ChartCard>
        </div>
      </AnalyticsSection>

      {/* 6) Service Analytics */}
      <AnalyticsSection title={t('services.title')}>
        <ChartCard title={t('services.topPerforming')} subtitle={topServices.length ? t('services.byCount') : t('comingSoon')}>
            <div className="h-48">
            {topServices.length ? (
            <ResponsiveContainer width="100%" height="100%">
                <BarChart data={topServices} layout="vertical" margin={{ top: 8, right: 12, left: 12, bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 11 }} tickFormatter={(v) => formatAxisValue(v, lng)} />
                <YAxis dataKey="name" type="category" width={90} tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <Tooltip content={<DashboardTooltip valueFormatter={(v) => formatCount(v, lng)} labelKey={t('chart.count')} />} />
                <Bar dataKey="count" fill="#10b981" radius={[0, 4, 4, 0]} name={t('chart.count')} />
              </BarChart>
            </ResponsiveContainer>
            ) : (
              <div className="flex h-48 items-center justify-center text-slate-500">{t('comingSoon')}</div>
            )}
          </div>
        </ChartCard>
      </AnalyticsSection>

      {/* 7) Operational */}
      <AnalyticsSection title={t('operational.title')}>
        <div className="grid gap-6 lg:grid-cols-2">
          <ChartCard title={t('operational.appointmentTrend')} subtitle={t('comingSoon')}>
            <div className="flex h-56 items-center justify-center text-slate-500">{t('comingSoon')}</div>
          </ChartCard>
          <ChartCard title={t('operational.peakHours')} subtitle={t('comingSoon')}>
            <div className="flex h-56 items-center justify-center text-slate-500">{t('comingSoon')}</div>
          </ChartCard>
        </div>
      </AnalyticsSection>

      {/* 8) Detailed Tables */}
      <section className="grid gap-6 lg:grid-cols-2">
        <SectionCard title={t('tables.vipPatients')} subtitle={vipList.length ? undefined : t('empty')}>
          <ReportTable
            columns={[
              { key: 'record_no', header: t('transactions.recordNo') },
              { key: 'patient_name', header: t('transactions.patient'), render: (_, r) => r.patient_name ?? r.name },
              { key: 'tier', header: t('manager.patientTier'), render: (v, r) => <StatusBadge status={r.financial_tier ?? r.tier ?? v} tier /> },
            ]}
            data={vipList}
          />
        </SectionCard>
        <SectionCard title={t('tables.debtors')} subtitle={t('comingSoon')}>
            <div className="flex h-24 items-center justify-center text-slate-500">{t('comingSoon')}</div>
          </SectionCard>
        <SectionCard title={t('tables.recentAppointments')} subtitle={t('comingSoon')}>
            <div className="flex h-24 items-center justify-center text-slate-500">{t('comingSoon')}</div>
          </SectionCard>
        <SectionCard title={t('tables.inactivePatients')} subtitle={t('comingSoon')}>
            <div className="flex h-24 items-center justify-center text-slate-500">{t('comingSoon')}</div>
          </SectionCard>
      </section>
    </div>
  )
}
