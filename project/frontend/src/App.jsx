import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import NavBar from './components/common/NavBar'
import { useAuth } from './store/AuthContext'
import { SessionProvider } from './store/SessionContext'
import { ToastProvider } from './store/ToastContext'
import ComplianceMatrix from './pages/ComplianceMatrix'
import EvidenceViewer from './pages/EvidenceViewer'
import Reports from './pages/Reports'
import Requirements from './pages/Requirements'
import Upload from './pages/Upload'
import Login from './pages/Login'
import Register from './pages/Register'

function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth()
  const location = useLocation()
  if (isLoading) return <div className="flex min-h-screen items-center justify-center text-sm text-slate-500">Loading workspace...</div>
  if (!isAuthenticated) return <Navigate to="/login" replace state={{ from: location }} />
  return <ProtectedApp />
}

function ProtectedApp() {
  return (
    <SessionProvider>
      <ToastProvider>
        <div className="min-h-screen">
          <NavBar />
          <Routes>
            <Route path="/" element={<Upload />} />
            <Route path="/requirements" element={<Requirements />} />
            <Route path="/compliance" element={<ComplianceMatrix />} />
            <Route path="/evidence" element={<EvidenceViewer />} />
            <Route path="/evidence/:ruleId" element={<EvidenceViewer />} />
            <Route path="/reports" element={<Reports />} />
          </Routes>
        </div>
      </ToastProvider>
    </SessionProvider>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/*" element={<ProtectedRoute />} />
    </Routes>
  )
}
