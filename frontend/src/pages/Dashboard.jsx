import { useState, useEffect, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { reports as reportsApi } from '../api/client'

const STATUS_STYLE = {
  queued:     { bg: 'rgba(251,191,36,0.08)',  border: 'rgba(251,191,36,0.2)',  text: '#fbbf24', label: 'Queued' },
  processing: { bg: 'rgba(96,165,250,0.08)',  border: 'rgba(96,165,250,0.2)',  text: '#60a5fa', label: 'Processing' },
  completed:  { bg: 'rgba(52,211,153,0.08)',  border: 'rgba(52,211,153,0.2)',  text: '#34d399', label: 'Completed' },
  failed:     { bg: 'rgba(248,113,113,0.08)', border: 'rgba(248,113,113,0.2)', text: '#f87171', label: 'Failed' },
}

const TIER_LIMITS = { free: 3, basic: 20, pro: 100, business: 999999 }

function StatusBadge({ status }) {
  const s = STATUS_STYLE[status] || STATUS_STYLE.queued
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-mono px-2.5 py-1 rounded-full"
      style={{ background: s.bg, border: `1px solid ${s.border}`, color: s.text }}>
      {status === 'processing' && (
        <span className="w-1.5 h-1.5 rounded-full bg-current" style={{ animation: 'pulse 1s ease-in-out infinite' }} />
      )}
      {s.label}
    </span>
  )
}

export default function Dashboard() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [reportList, setReportList] = useState([])
  const [loading, setLoading] = useState(true)
  const [deleting, setDeleting] = useState(null)

  const fetchReports = useCallback(async () => {
    try {
      const r = await reportsApi.list()
      setReportList(r.data.reports || [])
    } catch {
      // handled by interceptor
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchReports()
    // Poll every 8s if any report is in progress
    const interval = setInterval(() => {
      const hasActive = reportList.some(r => ['queued', 'processing'].includes(r.status))
      if (hasActive) fetchReports()
    }, 8000)
    return () => clearInterval(interval)
  }, [fetchReports, reportList])

  const handleDelete = async (id, e) => {
    e.stopPropagation()
    if (!confirm('Delete this report?')) return
    setDeleting(id)
    try {
      await reportsApi.delete(id)
      setReportList(prev => prev.filter(r => r.id !== id))
    } catch { }
    setDeleting(null)
  }

  const usedThisMonth = reportList.filter(r => {
    const d = new Date(r.created_at)
    const now = new Date()
    return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear()
  }).length

  const limit = TIER_LIMITS[user?.tier] || 3
  const pct = Math.min((usedThisMonth / limit) * 100, 100)

  return (
    <div className="min-h-screen pt-20 px-6 pb-16">
      <div className="max-w-6xl mx-auto">

        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-10">
          <div>
            <div className="section-label mb-3">Dashboard</div>
            <h1 className="font-display font-700 text-3xl text-white">
              Welcome back{user?.full_name ? `, ${user.full_name.split(' ')[0]}` : ''}
            </h1>
            <p className="text-slate-500 font-body text-sm mt-1">Your intelligence reports</p>
          </div>
          <Link to="/generate" className="btn-primary text-sm self-start md:self-auto">
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
              <path d="M8 3v10M3 8h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
            <span>Generate Report</span>
          </Link>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
          {[
            { label: 'Reports Generated', val: reportList.length },
            { label: 'This Month', val: usedThisMonth },
            { label: 'Monthly Limit', val: limit === 999999 ? '∞' : limit },
            { label: 'Plan', val: user?.tier?.toUpperCase() || 'FREE' },
          ].map((s, i) => (
            <div key={i} className="glass-card p-5">
              <div className="text-xs font-mono text-slate-600 uppercase tracking-wider mb-2">{s.label}</div>
              <div className="font-display font-700 text-2xl text-white">{s.val}</div>
            </div>
          ))}
        </div>

        {/* Usage bar */}
        <div className="glass-card p-5 mb-8">
          <div className="flex justify-between items-center mb-3">
            <span className="text-xs font-mono text-slate-500 uppercase tracking-wider">Monthly Usage</span>
            <span className="text-xs font-mono text-slate-400">{usedThisMonth} / {limit === 999999 ? '∞' : limit}</span>
          </div>
          <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
            <div className="h-full rounded-full transition-all duration-500"
              style={{ width: `${pct}%`, background: pct > 80 ? '#f87171' : 'linear-gradient(90deg,#10b981,#34d399)' }} />
          </div>
          {pct > 80 && (
            <p className="text-xs font-body text-red-400 mt-2">
              Running low.{' '}
              <a href="/#pricing" className="underline">Upgrade your plan</a>
            </p>
          )}
        </div>

        {/* Reports list */}
        {loading ? (
          <div className="flex items-center justify-center py-24">
            <div className="w-8 h-8 rounded-full border-2 border-emerald-400/30 border-t-emerald-400"
              style={{ animation: 'spin 1s linear infinite' }} />
          </div>
        ) : reportList.length === 0 ? (
          <div className="glass-card p-16 text-center">
            <div className="text-4xl mb-4 text-slate-700">◈</div>
            <h2 className="font-display font-600 text-white text-xl mb-3">No reports yet</h2>
            <p className="text-slate-500 font-body text-sm mb-8">Generate your first intelligence report</p>
            <Link to="/generate" className="btn-primary text-sm inline-flex">
              <span>Generate your first report</span>
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {reportList.map((r) => (
              <div key={r.id}
                onClick={() => r.status === 'completed' && r.file_url ? window.open(r.file_url) : navigate(`/reports/${r.id}`)}
                className="glass-card p-5 cursor-pointer flex items-center justify-between gap-4">
                <div className="flex items-center gap-4 min-w-0">
                  <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 font-mono text-sm font-500"
                    style={{
                      background: r.asset_type === 'commodity' ? 'rgba(245,158,11,0.1)' : 'rgba(59,130,246,0.1)',
                      color: r.asset_type === 'commodity' ? '#F59E0B' : '#60a5fa',
                    }}>
                    {r.asset_symbol?.slice(0, 2)}
                  </div>
                  <div className="min-w-0">
                    <div className="font-display font-600 text-white text-sm">{r.asset_symbol}</div>
                    <div className="text-xs font-mono text-slate-600 capitalize">{r.asset_type} · {new Date(r.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}</div>
                  </div>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  <StatusBadge status={r.status} />
                  {r.status === 'completed' && r.file_url && (
                    <a href={r.file_url} target="_blank" rel="noreferrer"
                      onClick={e => e.stopPropagation()}
                      className="text-xs font-mono text-emerald-400 hover:text-emerald-300 transition-colors px-3 py-1.5 rounded-lg"
                      style={{ background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.15)' }}>
                      Download
                    </a>
                  )}
                  <button onClick={(e) => handleDelete(r.id, e)}
                    disabled={deleting === r.id}
                    className="text-slate-700 hover:text-red-400 transition-colors p-1.5 rounded-lg hover:bg-red-400/10 text-xs font-mono">
                    ✕
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
