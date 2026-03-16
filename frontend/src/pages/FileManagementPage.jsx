import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { UploadCloud, FileSpreadsheet, CheckCircle2, AlertTriangle } from 'lucide-react'
import { SectionCard } from '../components/ui/SectionCard'
import { PageHeader } from '../components/layout/PageHeader'
import { atiehApi } from '../services/atiehApi'

const FILE_TYPES = [
  { id: 'history', label: 'سوابق (History)' },
  { id: 'payments', label: 'پرداخت‌ها (Payments)' },
  { id: 'reference', label: 'مرجع (Reference)' },
]

const IMPORT_MODES = [
  { id: 'append', label: 'افزودن به داده‌های موجود (Append)' },
  { id: 'replace', label: 'جایگزینی کامل (Replace)' },
  { id: 'validate', label: 'فقط اعتبارسنجی (Validate-only)' },
]

export function FileManagementPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [file, setFile] = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const [fileType, setFileType] = useState('')
  const [sourceSystem, setSourceSystem] = useState('')
  const [period, setPeriod] = useState('')
  const [importMode, setImportMode] = useState('append')
  const [notes, setNotes] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [message, setMessage] = useState(null)
  const [error, setError] = useState(null)

  const userRaw = localStorage.getItem('atieh_user')
  let userRole = null
  try {
    userRole = userRaw ? JSON.parse(userRaw)?.role : null
  } catch {
    userRole = null
  }

  const isOperator = userRole === 'operator'

  function handleFileSelect(f) {
    if (!f) return
    const allowed = ['.xlsx', '.xls', '.csv']
    const lower = f.name.toLowerCase()
    if (!allowed.some((ext) => lower.endsWith(ext))) {
      setError('فقط فایل‌های Excel یا CSV مجاز هستند.')
      setMessage(null)
      setFile(null)
      return
    }
    setFile(f)
    setError(null)
    setMessage(null)
  }

  function handleDrop(e) {
    e.preventDefault()
    setDragOver(false)
    if (!isOperator) return
    const f = e.dataTransfer.files?.[0]
    if (f) handleFileSelect(f)
  }

  function handleDragOver(e) {
    e.preventDefault()
    if (!isOperator) return
    setDragOver(true)
  }

  function handleDragLeave(e) {
    e.preventDefault()
    setDragOver(false)
  }

  async function handleSubmit(e) {
    e?.preventDefault?.()
    if (!isOperator) {
      setError('دسترسی به این بخش فقط برای اپراتور فنی مجاز است.')
      return
    }
    if (!file) {
      setError('لطفاً ابتدا فایل را انتخاب کنید.')
      return
    }
    if (!fileType) {
      setError('لطفاً نوع فایل را مشخص کنید.')
      return
    }
    setSubmitting(true)
    setError(null)
    setMessage(null)
    try {
      await atiehApi.uploadImportFile({
        file,
        file_type: fileType,
        source_system: sourceSystem || null,
        period: period || null,
        import_mode: importMode || 'append',
        notes: notes || null,
      })
      setMessage('فایل با موفقیت ثبت و وارد فرآیند شد.')
      setFile(null)
      setNotes('')
    } catch (err) {
      setError(err?.message || 'خطا در آپلود فایل')
    } finally {
      setSubmitting(false)
    }
  }

  if (!isOperator) {
    return (
      <div className="space-y-4">
        <PageHeader
          title="پنل مدیریت فایل‌ها"
          subtitle="دسترسی این بخش فقط برای اپراتور فنی مجاز است."
        />
        <SectionCard title="عدم دسترسی" subtitle="">
          <p className="text-sm text-slate-300">
            برای استفاده از پنل مدیریت فایل‌ها، با حساب کاربری اپراتور فنی وارد شوید.
          </p>
          <button
            type="button"
            onClick={() => navigate('/login')}
            className="mt-4 rounded-lg bg-cyan-500 px-4 py-2 text-sm font-medium text-slate-950 hover:bg-cyan-400"
          >
            بازگشت به صفحه ورود
          </button>
        </SectionCard>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="پنل مدیریت فایل‌ها"
        subtitle="آپلود کنترل‌شده‌ی فایل‌های CRM و ورود به فرآیند واردسازی"
      />
      <SectionCard
        title="آپلود فایل"
        subtitle="فایل Excel یا CSV را بکشید و رها کنید، سپس تنظیمات را انتخاب و ثبت کنید."
      >
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            className={`flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-10 text-center transition-colors ${
              dragOver ? 'border-cyan-400 bg-slate-800/60' : 'border-slate-700 bg-slate-900/50'
            }`}
            onClick={() => {
              if (!isOperator) return
              const input = document.createElement('input')
              input.type = 'file'
              input.accept = '.xlsx,.xls,.csv'
              input.onchange = (ev) => {
                const f = ev.target.files?.[0]
                if (f) handleFileSelect(f)
              }
              input.click()
            }}
          >
            <UploadCloud className="h-10 w-10 text-cyan-400" />
            <p className="mt-3 text-sm font-medium text-slate-100">
              فایل را اینجا رها کنید یا کلیک کنید
            </p>
            <p className="mt-1 text-xs text-slate-400">
              فقط فایل‌های Excel یا CSV مربوط به خروجی CRM
            </p>
            {file && (
              <div className="mt-4 inline-flex items-center gap-2 rounded-full bg-slate-800/80 px-3 py-1 text-xs text-slate-100">
                <FileSpreadsheet className="h-3.5 w-3.5 text-cyan-400" />
                <span>{file.name}</span>
                <span className="text-slate-500">
                  ({(file.size / 1024).toFixed(1)}
                  {' '}
                  KB)
                </span>
              </div>
            )}
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="mb-1 block text-xs text-slate-400">نوع فایل</label>
              <select
                value={fileType}
                onChange={(e) => setFileType(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-sm text-slate-100"
              >
                <option value="">انتخاب نوع فایل</option>
                {FILE_TYPES.map((t) => (
                  <option key={t.id} value={t.id}>{t.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs text-slate-400">سیستم/منبع</label>
              <input
                type="text"
                value={sourceSystem}
                onChange={(e) => setSourceSystem(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-sm text-slate-100"
                placeholder="مثلاً: CRM اصلی کلینیک"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-slate-400">دوره/سال</label>
              <input
                type="text"
                value={period}
                onChange={(e) => setPeriod(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-sm text-slate-100"
                placeholder="مثلاً: 1403Q1 یا 1403-01"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-slate-400">حالت واردسازی</label>
              <select
                value={importMode}
                onChange={(e) => setImportMode(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-sm text-slate-100"
              >
                {IMPORT_MODES.map((m) => (
                  <option key={m.id} value={m.id}>{m.label}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="mb-1 block text-xs text-slate-400">توضیحات (اختیاری)</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              className="w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-sm text-slate-100"
              placeholder="توضیحات کمکی برای تیم فنی یا تاریخچه واردسازی"
            />
          </div>

          {error && (
            <div className="flex items-center gap-2 rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-400">
              <AlertTriangle className="h-4 w-4" />
              <span>{error}</span>
            </div>
          )}
          {message && (
            <div className="flex items-center gap-2 rounded-lg bg-emerald-500/10 px-3 py-2 text-xs text-emerald-400">
              <CheckCircle2 className="h-4 w-4" />
              <span>{message}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="inline-flex items-center gap-2 rounded-lg bg-cyan-500 px-4 py-2.5 text-sm font-semibold text-slate-950 transition-colors hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <UploadCloud className="h-4 w-4" />
            {submitting ? 'در حال ثبت...' : 'ثبت و ورود به فرآیند'}
          </button>
        </form>
      </SectionCard>
    </div>
  )
}

