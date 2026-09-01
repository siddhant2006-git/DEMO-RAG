import { Route, Routes } from 'react-router-dom'
import NavBar from './components/common/NavBar'
import { SessionProvider } from './store/SessionContext'
import { ToastProvider } from './store/ToastContext'
import ComplianceMatrix from './pages/ComplianceMatrix'
import EvidenceViewer from './pages/EvidenceViewer'
import Reports from './pages/Reports'
import Requirements from './pages/Requirements'
import Upload from './pages/Upload'

export default function App() {
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
