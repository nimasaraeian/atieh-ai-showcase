import { Outlet, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'

const ROUTE_KEYS = {
  '/receptionist': { titleKey: 'app.receptionist', subtitleKey: 'app.subtitleReceptionist' },
  '/files': { titleKey: 'app.files', subtitleKey: '' },
  '/manager': { titleKey: 'app.manager', subtitleKey: 'app.subtitleManager' },
}

function parseUser() {
  try {
    const raw = localStorage.getItem('atieh_user')
    if (!raw) {
      return {
        id: null,
        username: 'user',
        full_name: 'User',
        role: 'receptionist',
        active: false,
      }
    }
    const data = JSON.parse(raw)
    return {
      id: data.id ?? null,
      username: data.username ?? data.name ?? 'user',
      full_name: data.full_name ?? data.name ?? data.username ?? 'User',
      role: data.role ?? 'receptionist',
      active: data.active ?? true,
    }
  } catch {
    return {
      id: null,
      username: 'user',
      full_name: 'User',
      role: 'receptionist',
      active: false,
    }
  }
}

export function AppShell() {
  const user = parseUser()
  const { pathname: path } = useLocation()
  const { t } = useTranslation()
  const { titleKey, subtitleKey } = ROUTE_KEYS[path] ?? { titleKey: 'app.title', subtitleKey: '' }

  return (
    <div className="flex h-screen bg-slate-950">
      <Sidebar user={user} />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Topbar title={t(titleKey)} subtitle={subtitleKey ? t(subtitleKey) : ''} />
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
