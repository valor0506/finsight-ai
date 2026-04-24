import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { reports as reportsApi } from '../api/client'

const STEPS = [
  { key: 'queued',     label: 'Queued',              desc: 'Waiting for a worker' },
  { key: 'processing', label: 'Fetching Data',        desc: 'Alpha Vantage · FRED · NewsAPI' },
  { key: 'analysing',  label: 'AI Analysis',          desc: 'Gemini 1.5 Flash generating report' },
  { key: 'completed',  label: 'Report Ready',         desc: 'Download your DOCX file' },
]

function StepIndicator({ status }) {
  const activeIdx = status === 'completed' ? 3 : status === 'processing' ? 1 : status === 'queued' ? 0 : 0
  const isFailed = status === 'failed'

  return (
    <div className="flex items-start gap-0 mb-10">
      {STEPS.map((step, i) => {
        const done = i < activeIdx || status === 'completed'
        const active = i === activeIdx && !isFailed
        return (
          <div key={step.key} className="flex-1 flex flex-col items-center">
            <div className="flex items-center w-full">
              {i > 0 && (
                <div className="flex-1 h-px transition-all duration-500"
                  style={{ background: done ? '#10b981' : 'rgba(255,255,255,0.08)' }} />
              )}
              <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 transition-all duration-500"
                style={{
                  background: done ? '#10b981' : active ? 'rgba(16,185,129,0.15)' : 'rgba(255,255,255,0.05)',
                  border: `2px solid ${done ? '#10b981' : active ? '#10b981' : 'rgba(255,255,255,0.1)'}`,
                }}>
                {done ? (
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                    <path d="M2 6l3 3 5-5" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                ) : active ? (
                  <div className="w-2.5 h-2.5 rounded-full bg-emerald-400"
                    style={{ animation: 'pulse 1s ease-in-out infinite' }} />
                ) : (
                  <div className="w-2 h-2 rounded-full" style={{ background: 'rgba(255,255,255,0.2)' }} />
                )}
              </div>
              {i < STEPS.length - 1 && (
                <div className="flex-1 h-px transition-all duration-500"
                  style={{ background: done ? '#10b981' : 'rgba(255,255,255,0.08)' }} />
              )}
            </div>
            <div className="mt-2 text-center px-1">
              <div className={`text-xs font-mono ${done || active ? 'text-white' : 'text-slate-600'}`}>{step.label}</div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

export default function ReportStatus() {
  const { id } = useParams()
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)

  const fetch = async () => {
    try {
      const r = await reportsApi.get(id)
      setReport(r.data)
    } catch {
      // handled by interceptor
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetch()
    const interval = setInterval(() => {
      if (report && ['queued', 'processing'].includes(report.status)) {
        fetch()
      }
    }, 5000)
    return () => clearInterval(interval)
  }, [id, report?.status])

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="w-8 h-8 rounded-full border-2 border-emerald-400/30 border-t-emerald-400"
        style={{ animation: 'spin 1s linear infinite' }} />
    </div>
  )

  if (!report) return (
    <div className="min-h-screen flex items-center justify-center text-slate-500 font-body">
      Report not found.{' '}
      <Link to="/dashboard" className="text-emerald-400 ml-1">Go to dashboard</Link>
    </div>
  )

  return (
    <div className="min-h-screen pt-20 px-6 pb-16">
      <div className="max-w-2xl mx-auto">

        <div className="mb-10">
          <Link to="/dashboard" className="text-xs font-mono text-slate-600 hover:text-slate-400 transition-colors flex items-center gap-1 mb-6">
            ← Back to dashboard
          </Link>
          <div className="section-label mb-3">Report Status</div>
          <h1 className="font-display font-700 text-3xl text-white">
            {report.asset_symbol} <span className="text-slate-500 font-400 text-xl capitalize">{report.asset_type}</span>
          </h1>
          <p className="text-xs font-mono text-slate-600 mt-1">{report.id}</p>
        </div>

        <div className="glass-card p-8 mb-6">
          <StepIndicator status={report.status} />

          {report.status === 'completed' && (
            <div className="text-center">
              <div className="text-4xl mb-4">✓</div>
              <h2 className="font-display font-700 text-white text-xl mb-2">Report Ready</h2>
              <p className="text-slate-500 font-body text-sm mb-8">
                Your {report.asset_symbol} intelligence report has been generated.
              </p>
              <a href={report.file_url} target="_blank" rel="noreferrer"
                className="btn-primary text-sm inline-flex px-8 py-3.5">
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                  <path d="M8 3v7M5 7l3 3 3-3M3 13h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                <span>Download Report (.docx)</span>
              </a>
            </div>
          )}

          {['queued', 'processing'].includes(report.status) && (
            <div className="text-center">
              <div className="w-12 h-12 rounded-full border-2 border-emerald-400/30 border-t-emerald-400 mx-auto mb-4"
                style={{ animation: 'spin 1s linear infinite' }} />
              <h2 className="font-display font-600 text-white text-lg mb-2">
                {report.status === 'queued' ? 'Report queued...' : 'Generating your report...'}
              </h2>
              <p className="text-slate-500 font-body text-sm">
                {report.status === 'queued'
                  ? 'A Celery worker will pick this up shortly.'
                  : 'Fetching market data, running AI analysis. This takes 60–120 seconds.'}
              </p>
              <p className="text-xs font-mono text-slate-700 mt-4">This page auto-refreshes every 5 seconds</p>
            </div>
          )}

          {report.status === 'failed' && (
            <div className="text-center">
              <div className="text-4xl mb-4">✗</div>
              <h2 className="font-display font-600 text-red-400 text-xl mb-2">Generation Failed</h2>
              {report.error_message && (
                <div className="my-4 p-4 rounded-xl text-left text-xs font-mono text-red-400/80"
                  style={{ background: 'rgba(248,113,113,0.05)', border: '1px solid rgba(248,113,113,0.15)' }}>
                  {report.error_message}
                </div>
              )}
              <Link to="/generate" className="btn-primary text-sm inline-flex px-8 py-3.5">
                <span>Try again</span>
              </Link>
            </div>
          )}
        </div>

        {/* Report metadata */}
        <div className="glass-card p-6">
          <div className="text-xs font-mono text-slate-600 uppercase tracking-wider mb-4">Report Details</div>
          <div className="space-y-3">
            {[
              { label: 'Asset', val: report.asset_symbol },
              { label: 'Type', val: report.asset_type },
              { label: 'Analysis', val: report.analysis_type },
              { label: 'Status', val: report.status },
              { label: 'Created', val: new Date(report.created_at).toLocaleString('en-IN') },
              report.completed_at && { label: 'Completed', val: new Date(report.completed_at).toLocaleString('en-IN') },
            ].filter(Boolean).map((row) => (
              <div key={row.label} className="flex justify-between items-center py-2 border-b border-white/5 last:border-0">
                <span className="text-xs font-mono text-slate-600">{row.label}</span>
                <span className="text-xs font-mono text-slate-300 capitalize">{row.val}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
