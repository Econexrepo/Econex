import { createContext, useContext, useState, useEffect } from 'react'
import api from '../api/axios'

const AuthContext = createContext(null)

// ── Storage helpers ────────────────────────────────────────────────────────────
// "Remember for 30 days" uses localStorage (persists across browser restarts).
// Normal sessions use sessionStorage (clears when the tab / browser closes).

const THIRTY_DAYS_MS = 30 * 24 * 60 * 60 * 1000   // 30 days in milliseconds

function saveSession(token, user, remember) {
  const storage = remember ? localStorage : sessionStorage
  storage.setItem('econex_token',      token)
  storage.setItem('econex_user',       JSON.stringify(user))
  if (remember) {
    // Store the exact expiry timestamp so we can validate on next load
    storage.setItem('econex_token_exp', String(Date.now() + THIRTY_DAYS_MS))
  }
}

function clearSession() {
  ['econex_token', 'econex_user', 'econex_token_exp'].forEach(k => {
    localStorage.removeItem(k)
    sessionStorage.removeItem(k)
  })
}

function restoreSession() {
  // Try localStorage (remember-me) first
  const lsToken = localStorage.getItem('econex_token')
  if (lsToken) {
    const exp = Number(localStorage.getItem('econex_token_exp') || 0)
    if (exp && Date.now() > exp) {
      // 30-day window has passed – discard and force re-login
      clearSession()
      return null
    }
    try {
      const user = JSON.parse(localStorage.getItem('econex_user'))
      return { token: lsToken, user }
    } catch { clearSession(); return null }
  }

  // Fall back to sessionStorage (normal session)
  const ssToken = sessionStorage.getItem('econex_token')
  if (ssToken) {
    try {
      const user = JSON.parse(sessionStorage.getItem('econex_user'))
      return { token: ssToken, user }
    } catch { return null }
  }

  return null
}

// ── Provider ───────────────────────────────────────────────────────────────────
export function AuthProvider({ children }) {
  const [user,    setUser]    = useState(null)
  const [loading, setLoading] = useState(true)

  // Restore session on mount
  useEffect(() => {
    const session = restoreSession()
    if (session) setUser(session.user)
    setLoading(false)
  }, [])

  /**
   * @param {string}  email
   * @param {string}  password
   * @param {boolean} remember  – if true, persist for 30 days; else session-only
   */
  const login = async (email, password, remember = false) => {
    const { data } = await api.post('/api/auth/login', {
      email,
      password,
      remember_me: remember,          // backend issues a matching-length JWT
    })
    saveSession(data.access_token, data.user, remember)
    setUser(data.user)
    return data.user
  }

  const logout = async () => {
    try { await api.post('/api/auth/logout') } catch { /* ignore */ }
    clearSession()
    setUser(null)
  }

  const updateUser = (updated) => {
    setUser(updated)
    // Update whichever storage is active
    if (localStorage.getItem('econex_token')) {
      localStorage.setItem('econex_user', JSON.stringify(updated))
    } else {
      sessionStorage.setItem('econex_user', JSON.stringify(updated))
    }
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, updateUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
