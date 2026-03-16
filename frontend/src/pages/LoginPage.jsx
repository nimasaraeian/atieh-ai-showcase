import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { LayoutDashboard } from 'lucide-react'

const ROLES = [
  { id: 'receptionist', label: 'Receptionist' },
  { id: 'manager', label: 'Manager' },
  { id: 'operator', label: 'Technical Operator' },
]

const ROLE_ROUTES = {
  receptionist: '/receptionist',
  manager: '/manager',
  operator: '/files',
}

export function LoginPage() {
  const [username, setUsername] = useState('')
  const [fullName, setFullName] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('receptionist')
  const [error, setError] = useState('')
  const navigate = useNavigate()

  function handleSubmit(e) {
    e.preventDefault()
    setError('')

    if (!username.trim()) {
      setError('Please enter username')
      return
    }

    // Simple credential check for technical operator
    if (role === 'operator') {
      // Hard-coded demo credentials; can be wired to backend auth later
      if (username.trim() !== 'operator' || password !== 'clinic123') {
        setError('نام کاربری یا رمز عبور اپراتور نادرست است.')
        return
      }
    }

    const now = Date.now()
    const user = {
      id: now,
      username: username.trim(),
      full_name: (fullName || username).trim(),
      role,
      active: true,
    }

    localStorage.setItem('atieh_user', JSON.stringify(user))
    navigate(ROLE_ROUTES[role] ?? '/receptionist')
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 px-4">
      <div className="w-full max-w-md">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-8 shadow-xl">
          <div className="mb-8 flex items-center justify-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-cyan-500/20">
              <LayoutDashboard className="h-7 w-7 text-cyan-400" />
            </div>
            <span className="text-xl font-semibold text-slate-100">Atieh AI</span>
          </div>
          <p className="mb-6 text-center text-sm text-slate-400">
            Clinic Operations · Sign in to continue
          </p>
          {error && (
            <div className="mb-4 rounded-lg bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</div>
          )}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-400">Role</label>
              <div className="flex gap-2">
                {ROLES.map((r) => (
                  <button
                    key={r.id}
                    type="button"
                    onClick={() => setRole(r.id)}
                    className={`flex-1 rounded-lg border py-2.5 text-sm font-medium transition-colors ${
                      role === r.id
                        ? 'border-cyan-500/50 bg-cyan-500/15 text-cyan-400'
                        : 'border-slate-700 bg-slate-800/50 text-slate-400 hover:border-slate-600 hover:text-slate-300'
                    }`}
                  >
                    {r.label}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-400">Full name</label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-800/80 px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:border-cyan-500/50 focus:outline-none focus:ring-1 focus:ring-cyan-500/30"
                placeholder="Enter full name (e.g. Receptionist Ali)"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-400">Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-800/80 px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:border-cyan-500/50 focus:outline-none focus:ring-1 focus:ring-cyan-500/30"
                placeholder="Enter username"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-400">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-800/80 px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:border-cyan-500/50 focus:outline-none focus:ring-1 focus:ring-cyan-500/30"
                placeholder="Enter password"
              />
            </div>
            <button
              type="submit"
              className="w-full rounded-lg bg-cyan-500 py-3 text-sm font-semibold text-slate-950 transition-colors hover:bg-cyan-400"
            >
              Sign in
            </button>
          </form>
        </div>
        <p className="mt-6 text-center text-xs text-slate-600">
          Demo: any credentials accepted. Role determines redirect.
        </p>
      </div>
    </div>
  )
}
