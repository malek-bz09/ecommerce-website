import { useState } from 'react'
import { AuthContext } from './auth'
import { adminAccounts } from '../data/adminAccounts'

const STORAGE_KEY = 'admin-session'

// Session lasts until the tab is closed
function loadUser() {
  try {
    const saved = JSON.parse(sessionStorage.getItem(STORAGE_KEY))
    return adminAccounts.find((a) => a.username === saved?.username) ? saved : null
  } catch {
    return null
  }
}

function saveUser(user) {
  try {
    if (user) sessionStorage.setItem(STORAGE_KEY, JSON.stringify(user))
    else sessionStorage.removeItem(STORAGE_KEY)
  } catch {
    // Storage can be unavailable (private mode); the session still works in memory
  }
}

function AuthProvider({ children }) {
  const [user, setUser] = useState(loadUser)

  const value = {
    user,
    // Returns true when the username/password match a predefined account
    login: (username, password) => {
      const account = adminAccounts.find(
        (a) => a.username === username.trim() && a.password === password,
      )
      if (!account) return false
      const next = { username: account.username, name: account.name }
      saveUser(next)
      setUser(next)
      return true
    },
    logout: () => {
      saveUser(null)
      setUser(null)
    },
  }

  return <AuthContext value={value}>{children}</AuthContext>
}

export default AuthProvider
