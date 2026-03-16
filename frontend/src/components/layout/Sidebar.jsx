import { Link, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { LayoutDashboard, UploadCloud, Users, BarChart3, LogOut } from 'lucide-react'
import { cn } from '../../utils/cn'

function navForRole(role) {
  const r = role || ''
  if (r === 'owner' || r === 'clinic_manager') {
    return [
      { to: '/receptionist', labelKey: 'app.receptionist', icon: Users },
      { to: '/files', labelKey: 'app.files', icon: UploadCloud },
      { to: '/manager', labelKey: 'app.manager', icon: BarChart3 },
    ]
  }
  if (r === 'operator') {
    return [{ to: '/files', labelKey: 'app.files', icon: UploadCloud }]
  }
  return [{ to: '/receptionist', labelKey: 'app.receptionist', icon: Users }]
}

export function Sidebar({ user }) {
  const loc = useLocation()
  const { t } = useTranslation()
  const nav = navForRole(user?.role)

  return (
    <aside className="flex w-64 flex-col border-e border-slate-800 bg-slate-900/50">
      <div className="flex h-16 items-center gap-2 border-b border-slate-800 px-6">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-cyan-500/20 text-cyan-400">
          <LayoutDashboard className="h-5 w-5" />
        </div>
        <span className="font-semibold text-slate-100">Atieh AI</span>
      </div>
      <nav className="flex-1 space-y-0.5 p-3">
        {nav.map(({ to, labelKey, icon: Icon }) => {
          const active = loc.pathname === to
          return (
            <Link
              key={to}
              to={to}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors',
                active
                  ? 'bg-cyan-500/15 text-cyan-400'
                  : 'text-slate-400 hover:bg-slate-800/80 hover:text-slate-200'
              )}
            >
              <Icon className="h-4.5 w-4.5 shrink-0" />
              {t(labelKey)}
            </Link>
          )
        })}
      </nav>
      <div className="border-t border-slate-800 p-3">
        <div className="rounded-lg px-3 py-2 text-xs text-slate-500">
          {(user?.full_name || user?.username || 'User')}
          {user?.role && (
            <span className="ms-1 text-[10px] text-slate-600">
              · {user.role}
            </span>
          )}
        </div>
        <Link
          to="/login"
          onClick={() => {
            try {
              localStorage.removeItem('atieh_user')
              localStorage.removeItem('atieh_token')
            } catch {
              // ignore
            }
          }}
          className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-slate-400 transition-colors hover:bg-slate-800/80 hover:text-red-400"
        >
          <LogOut className="h-4.5 w-4.5" />
          {t('app.logout')}
        </Link>
      </div>
    </aside>
  )
}
