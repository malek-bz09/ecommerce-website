import { useCallback, useState } from 'react'
import { AuthContext } from './auth'
import { ApiError, apiFetch } from '../services/api'

const STORAGE_KEY = 'admin-session'

// Session lasts until the tab is closed (or the server's 8-hour limit)
function loadSession() {
  try {
    const saved = JSON.parse(sessionStorage.getItem(STORAGE_KEY))
    return saved?.token && saved?.user ? saved : null
  } catch {
    return null
  }
}

function saveSession(session) {
  try {
    if (session) sessionStorage.setItem(STORAGE_KEY, JSON.stringify(session))
    else sessionStorage.removeItem(STORAGE_KEY)
  } catch {
    // Storage can be unavailable (private mode); the session still works in memory
  }
}

function AuthProvider({ children }) {
  const [session, setSession] = useState(loadSession)
  const token = session?.token

  const clearSession = useCallback(() => {
    saveSession(null)
    setSession(null)
  }, [])

  // The server checks the username and password; throws ApiError when they're wrong
  const login = async (username, password) => {
    const next = await apiFetch('/admin/login', { method: 'POST', body: { username, password } })
    saveSession(next)
    setSession(next)
  }

  const logout = async () => {
    clearSession()
    // Also end the session on the server; nothing to do if that fails
    await apiFetch('/admin/logout', { method: 'POST', token }).catch(() => {})
  }

  // fetch for admin pages: adds the token, and signs out when the server rejects it.
  // useCallback keeps the same function between renders so pages can use it in useEffect.
  const authFetch = useCallback(
    async (path, options = {}) => {
      try {
        return await apiFetch(path, { ...options, token })
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) clearSession()
        throw error
      }
    },
    [token, clearSession],
  )

  const value = { user: session?.user ?? null, login, logout, authFetch }

  return <AuthContext value={value}>{children}</AuthContext>
}

export default AuthProvider
