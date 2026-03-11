import { Routes, Route, Navigate } from 'react-router-dom'
import { AppShell } from './components/layout/AppShell'
import { LoginPage } from './pages/LoginPage'
import { ReceptionistPage } from './pages/ReceptionistPage'
import { DoctorPage } from './pages/DoctorPage'
import { ManagerPage } from './pages/ManagerPage'

function ProtectedRoute({ children }) {
  try {
    const raw = localStorage.getItem('atieh_user')
    if (!raw || raw === 'null') return <Navigate to="/login" replace />
    JSON.parse(raw)
  } catch {
    return <Navigate to="/login" replace />
  }
  return children
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/receptionist"
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route index element={<ReceptionistPage />} />
      </Route>
      <Route
        path="/doctor"
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route index element={<DoctorPage />} />
      </Route>
      <Route
        path="/manager"
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route index element={<ManagerPage />} />
      </Route>
      <Route path="/" element={<Navigate to="/receptionist" replace />} />
      <Route path="*" element={<Navigate to="/receptionist" replace />} />
    </Routes>
  )
}
