import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import Auth from './pages/Auth'
import Dashboard from './pages/Dashboard'
import Unemployement from './pages/Unemployement'
import Wages from './pages/Wages'
import Agriculture from './pages/Agriculture'
import GDP from './pages/GDP'
import Expenditure from './pages/Expenditure'
import Chat from './pages/Chat'
import Settings from './pages/Settings'
import AppLayout from './components/AppLayout'

function PrivateRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="full-page-loader"><div className="spinner" /></div>
  return user ? children : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <Routes>
      {/* ── Auth pages ── */}
      <Route path="/login"           element={<Auth initialView="login"  />} />
      <Route path="/signup"          element={<Auth initialView="signup" />} />
      <Route path="/forgot-password" element={<Auth initialView="forgot" />} />
      <Route path="/verify"          element={<Auth initialView="verify" />} />

      {/* ── Protected app ── */}
      <Route
        path="/"
        element={
          <PrivateRoute>
            <AppLayout />
          </PrivateRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="unemployment" element={<Unemployement />} />
        <Route path="wages" element={<Wages />} />
        <Route path="agriculture" element={<Agriculture />} />
        <Route path="GDP" element={<GDP />} />
        <Route path="Expenditure" element={<Expenditure />} />
        <Route path="chat"      element={<Chat />} />
        <Route path="settings"  element={<Settings />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
