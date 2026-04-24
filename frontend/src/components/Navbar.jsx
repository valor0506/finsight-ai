import { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const TIER_COLORS = {
  free: 'text-slate-400 border-slate-600',
  basic: 'text-blue-400 border-blue-600',
  pro: 'text-emerald-400 border-emerald-600',
  business: 'text-gold-400 border-yellow-600',
}

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)

  const handleLogout = () => { logout(); navigate('/') }
  const isActive = (path) => location.pathname === path

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 glass border-b border-white/5">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">

        <Link to="/" className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, #10b981, #059669)' }}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M3 12L6 8L9 10L13 4" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
              <circle cx="13" cy="4" r="1.5" fill="white"/>
            </svg>
          </div>
          <span className="font-display font-700 text-base tracking-tight text-white">
            Fin<span className="text-gradient">Sight</span>
            <span className="text-slate-500 font-normal"> AI</span>
          </span>
        </Link>

        <div className="hidden md:flex items-center gap-8">
          {!user ? (
            <>
              <a href="/#how-it-works" className="text-sm font-body text-slate-400 hover:text-white transition-colors">How it works</a>
              <a href="/#modules" className="text-sm font-body text-slate-400 hover:text-white transition-colors">Modules</a>
              <a href="/#pricing" className="text-sm font-body text-slate-400 hover:text-white transition-colors">Pricing</a>
            </>
          ) : (
            <>
              <Link to="/dashboard"
                className={`text-sm font-body transition-colors ${isActive('/dashboard') ? 'text-emerald-400' : 'text-slate-400 hover:text-white'}`}>
                Dashboard
              </Link>
              <Link to="/generate"
                className={`text-sm font-body transition-colors ${isActive('/generate') ? 'text-emerald-400' : 'text-slate-400 hover:text-white'}`}>
                Generate Report
              </Link>
            </>
          )}
        </div>

        <div className="flex items-center gap-3">
          {user ? (
            <div className="flex items-center gap-3">
              <div className="hidden md:flex items-center gap-2">
                <span className={`text-xs font-mono px-2.5 py-1 rounded-full border uppercase tracking-wider ${TIER_COLORS[user.tier] || TIER_COLORS.free}`}>
                  {user.tier}
                </span>
                <span className="text-sm text-slate-400 font-body">{user.email?.split('@')[0]}</span>
              </div>
              <button onClick={handleLogout}
                className="text-sm font-body text-slate-500 hover:text-red-400 transition-colors px-3 py-1.5 rounded-lg hover:bg-red-400/10">
                Sign out
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Link to="/login" className="btn-outline text-sm py-2 px-4">Sign in</Link>
              <Link to="/register" className="btn-primary text-sm py-2 px-4">
                <span>Get started</span>
              </Link>
            </div>
          )}
        </div>
      </div>
    </nav>
  )
}
