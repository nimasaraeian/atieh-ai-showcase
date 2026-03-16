import { Routes, Route, Navigate } from 'react-router-dom'
import { LoginPage } from './pages/LoginPage'
import { ReceptionistPage } from './pages/ReceptionistPage'
import { FileManagementPage } from './pages/FileManagementPage'
import { AppShell } from './components/layout/AppShell'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/receptionist" element={<AppShell />}>
        <Route index element={<ReceptionistPage />} />
      </Route>
      <Route path="/files" element={<AppShell />}>
        <Route index element={<FileManagementPage />} />
      </Route>
      <Route path="/manager" element={<AppShell />}>
        <Route index element={<div className="text-white p-6">Manager (placeholder)</div>} />
      </Route>
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}
