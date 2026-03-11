import { Outlet, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'

const ROUTE_KEYS = {
  '/receptionist': { titleKey: 'app.receptionist', subtitleKey: 'app.subtitleReceptionist' },
  '/doctor': { titleKey: 'app.doctor', subtitleKey: 'app.subtitleDoctor' },
  '/manager': { titleKey: 'app.manager', subtitleKey: 'app.subtitleManager' },
}

function parseUser() {
  try {
    const raw = localStorage.getItem('atieh_user')
    return raw ? JSON.parse(raw) : { name: 'User', role: 'Receptionist' }
  } catch {
    return { name: 'User', role: 'Receptionist' }
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
