import { useTranslation } from 'react-i18next'
import { Languages } from 'lucide-react'
import { cn } from '../../utils/cn'

const LANGUAGES = [
  { code: 'en', label: 'EN' },
  { code: 'fa', label: 'فا' },
]

export function LanguageSwitcher({ className }) {
  const { i18n } = useTranslation()

  return (
    <div className={cn('flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-800/50 p-0.5', className)}>
      <Languages className="ms-1.5 h-4 w-4 text-slate-500" />
      {LANGUAGES.map(({ code, label }) => (
        <button
          key={code}
          onClick={() => i18n.changeLanguage(code)}
          className={cn(
            'rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors',
            i18n.language === code
              ? 'bg-cyan-500/20 text-cyan-400'
              : 'text-slate-400 hover:bg-slate-700/80 hover:text-slate-200'
          )}
        >
          {label}
        </button>
      ))}
    </div>
  )
}
