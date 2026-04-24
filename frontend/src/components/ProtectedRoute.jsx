import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="w-8 h-8 rounded-full border-2 border-emerald-400/30 border-t-emerald-400"
        style={{ animation: 'spin 1s linear infinite' }} />
    </div>
  )

  if (!user) return <Navigate to="/login" replace />
  return children
}
