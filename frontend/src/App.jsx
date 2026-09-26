import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import NavBar from './components/common/NavBar'
import { AuthProvider, useAuth } from './store/AuthContext'
import { SessionProvider } from './store/SessionContext'
import { ToastProvider } from './store/ToastContext'
import { ForgotPassword, Login, Register, ResetPassword, VerifyEmail } from './pages/Auth'
import ComplianceMatrix from './pages/ComplianceMatrix'
import EvidenceViewer from './pages/EvidenceViewer'
import Reports from './pages/Reports'
import Requirements from './pages/Requirements'
import Upload from './pages/Upload'
import Dashboard from './pages/Dashboard'

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  const location = useLocation()
  if (loading) return <div className="auth-loading">Loading secure workspace...</div>
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  return children
}

function AuthenticatedApp() {
  const { user } = useAuth()
  return (
    <div className="min-h-screen">
      {user && <NavBar />}
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/verify-email" element={<VerifyEmail />} />
        <Route path="*" element={<ProtectedRoute><Routes><Route path="/" element={<Dashboard />} /><Route path="/dashboard" element={<Dashboard />} /><Route path="/upload" element={<Upload />} /><Route path="/requirements" element={<Requirements />} /><Route path="/compliance" element={<ComplianceMatrix />} /><Route path="/evidence" element={<EvidenceViewer />} /><Route path="/evidence/:ruleId" element={<EvidenceViewer />} /><Route path="/reports" element={<Reports />} /></Routes></ProtectedRoute>} />
      </Routes>
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider><SessionProvider><ToastProvider><AuthenticatedApp /></ToastProvider></SessionProvider></AuthProvider>
  )
}
