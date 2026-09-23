import { createContext, useContext, useEffect, useState } from 'react'
import { getCurrentUser, loginUser, logoutUser } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const accessToken = localStorage.getItem('tenderguard.accessToken')

  useEffect(() => {
    if (!accessToken) {
      setIsLoading(false)
      return
    }
    getCurrentUser()
      .then(({ user: currentUser }) => setUser(currentUser))
      .catch(() => {
        localStorage.removeItem('tenderguard.accessToken')
        localStorage.removeItem('tenderguard.refreshToken')
      })
      .finally(() => setIsLoading(false))
  }, [accessToken])

  async function login(identifier, password) {
    const result = await loginUser(identifier, password)
    localStorage.setItem('tenderguard.accessToken', result.accessToken)
    localStorage.setItem('tenderguard.refreshToken', result.refreshToken)
    setUser(result.user)
  }

  async function logout() {
    try {
      if (localStorage.getItem('tenderguard.accessToken')) await logoutUser()
    } finally {
      localStorage.removeItem('tenderguard.accessToken')
      localStorage.removeItem('tenderguard.refreshToken')
      setUser(null)
    }
  }

  return (
    <AuthContext.Provider value={{ user, isLoading, isAuthenticated: Boolean(user), login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within AuthProvider')
  return context
}
