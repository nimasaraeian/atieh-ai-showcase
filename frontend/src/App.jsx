import { Routes, Route, Navigate } from 'react-router-dom'
import { LoginPage } from './pages/LoginPage'
import { ReceptionistPage } from './pages/ReceptionistPage'
import { FileManagementPage } from './pages/FileManagementPage'
import { ManagerPage } from './pages/ManagerPage'
import { AppShell } from './components/layout/AppShell'

function getUserRole() {
  try {
    const raw = localStorage.getItem('atieh_user')
    if (!raw) return null
    return JSON.parse(raw)?.role || null
  } catch {
    return null
  }
}

function hasToken() {
  try {
    return !!localStorage.getItem('atieh_token')
  } catch {
    return false
  }
}

function RequireRole({ allow, children }) {
  const role = getUserRole()
  if (!hasToken() || !role) return <Navigate to="/login" replace />
  if (role === 'owner') return children
  if (allow.includes(role)) return children
  return <Navigate to="/login" replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/receptionist" element={<AppShell />}>
        <Route
          index
          element={
            <RequireRole allow={['receptionist', 'clinic_manager']}>
              <ReceptionistPage />
            </RequireRole>
          }
        />
      </Route>
      <Route path="/files" element={<AppShell />}>
        <Route
          index
          element={
            <RequireRole allow={['operator', 'clinic_manager']}>
              <FileManagementPage />
            </RequireRole>
          }
        />
      </Route>
      <Route path="/manager" element={<AppShell />}>
        <Route
          index
          element={
            <RequireRole allow={['clinic_manager']}>
              <ManagerPage />
            </RequireRole>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}
