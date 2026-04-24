import { createContext, useContext, useState, useEffect } from 'react'
import { auth as authApi } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem('user')) } catch { return null }
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) { setLoading(false); return }
    authApi.me()
      .then(r => { setUser(r.data); localStorage.setItem('user', JSON.stringify(r.data)) })
      .catch(() => { localStorage.removeItem('token'); localStorage.removeItem('user'); setUser(null) })
      .finally(() => setLoading(false))
  }, [])

  const login = async (email, password) => {
    const r = await authApi.login(email, password)
    localStorage.setItem('token', r.data.access_token)
    localStorage.setItem('user', JSON.stringify(r.data))
    setUser(r.data)
    return r.data
  }

  const register = async (email, password, full_name) => {
    const r = await authApi.register(email, password, full_name)
    localStorage.setItem('token', r.data.access_token)
    localStorage.setItem('user', JSON.stringify(r.data))
    setUser(r.data)
    return r.data
  }

  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
