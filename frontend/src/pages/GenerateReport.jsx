import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { reports as reportsApi } from '../api/client'

const ASSET_OPTIONS = {
  commodity: [
    { symbol: 'SILVER',      label: 'Silver',       desc: 'XAG — precious metals' },
    { symbol: 'GOLD',        label: 'Gold',          desc: 'XAU — safe haven' },
    { symbol: 'CRUDE_WTI',   label: 'Crude Oil WTI', desc: 'US benchmark crude' },
    { symbol: 'CRUDE_BRENT', label: 'Crude Oil Brent', desc: 'Global benchmark' },
    { symbol: 'NATURAL_GAS', label: 'Natural Gas',   desc: 'Energy commodity' },
    { symbol: 'COPPER',      label: 'Copper',        desc: 'Industrial metal' },
  ],
  equity: [],
}

const ANALYSIS_TYPES = [
  { value: 'full',      label: 'Full Report',     desc: 'Executive summary, technicals, macro, risks, targets' },
  { value: 'technical', label: 'Technical Only',   desc: 'Price action, RSI, SMA, momentum signals' },
  { value: 'macro',     label: 'Macro + Sentiment', desc: 'Macro context, news sentiment, macro correlations' },
]

const MODULE_INFO = {
  commodity: {
    color: '#F59E0B',
    icon: '◈',
    label: 'Commodity Intelligence',
    desc: 'AI-generated report with price action, technicals, macro correlations, and price targets.',
  },
  equity: {
    color: '#3b82f6',
    icon: '◉',
    label: 'Equity Analysis',
    desc: 'Enter any NSE/BSE or US ticker. We fetch fundamentals, technicals, and analyst data.',
  },
}

export default function GenerateReport() {
  const navigate = useNavigate()
  const [assetType, setAssetType] = useState('commodity')
  const [symbol, setSymbol] = useState('')
  const [customSymbol, setCustomSymbol] = useState('')
  const [analysisType, setAnalysisType] = useState('full')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const finalSymbol = assetType === 'equity' ? customSymbol.toUpperCase() : symbol
  const info = MODULE_INFO[assetType]

  const submit = async () => {
    if (!finalSymbol) { setError('Please select or enter an asset symbol'); return }
    setError('')
    setLoading(true)
    try {
      const r = await reportsApi.generate(assetType, finalSymbol, analysisType)
      navigate(`/reports/${r.data.report_id}`)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to queue report. Try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen pt-20 px-6 pb-16">
      <div className="max-w-3xl mx-auto">

        <div className="mb-10">
          <div className="section-label mb-3">Generate Report</div>
          <h1 className="font-display font-700 text-3xl text-white mb-2">What do you want to analyse?</h1>
          <p className="text-slate-500 font-body text-sm">Takes 60–120 seconds depending on data availability.</p>
        </div>

        {error && (
          <div className="mb-6 px-4 py-3 rounded-xl text-sm font-body text-red-400"
            style={{ background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.2)' }}>
            {error}
          </div>
        )}

        {/* Step 1 — Asset Type */}
        <div className="glass-card p-7 mb-5">
          <div className="text-xs font-mono text-slate-600 uppercase tracking-wider mb-4">Step 1 — Asset Category</div>
          <div className="grid grid-cols-2 gap-3">
            {Object.entries(MODULE_INFO).map(([type, meta]) => (
              <button key={type} onClick={() => { setAssetType(type); setSymbol(''); setCustomSymbol('') }}
                className="p-5 rounded-xl text-left transition-all"
                style={{
                  background: assetType === type ? `${meta.color}15` : 'rgba(255,255,255,0.02)',
                  border: `1px solid ${assetType === type ? `${meta.color}40` : 'rgba(255,255,255,0.06)'}`,
                }}>
                <div className="text-xl mb-2" style={{ color: meta.color }}>{meta.icon}</div>
                <div className="font-display font-600 text-white text-sm mb-1">{meta.label}</div>
                <div className="text-xs font-body text-slate-500 leading-relaxed">{meta.desc}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Step 2 — Symbol */}
        <div className="glass-card p-7 mb-5">
          <div className="text-xs font-mono text-slate-600 uppercase tracking-wider mb-4">Step 2 — Select Asset</div>

          {assetType === 'commodity' ? (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {ASSET_OPTIONS.commodity.map((opt) => (
                <button key={opt.symbol} onClick={() => setSymbol(opt.symbol)}
                  className="p-4 rounded-xl text-left transition-all"
                  style={{
                    background: symbol === opt.symbol ? 'rgba(245,158,11,0.1)' : 'rgba(255,255,255,0.02)',
                    border: `1px solid ${symbol === opt.symbol ? 'rgba(245,158,11,0.35)' : 'rgba(255,255,255,0.06)'}`,
                  }}>
                  <div className="font-mono text-sm font-500 text-yellow-400 mb-1">{opt.symbol}</div>
                  <div className="font-body text-white text-sm font-500">{opt.label}</div>
                  <div className="text-xs font-body text-slate-600">{opt.desc}</div>
                </button>
              ))}
            </div>
          ) : (
            <div>
              <label className="block text-xs font-mono text-slate-500 uppercase tracking-wider mb-2">
                Enter Ticker Symbol
              </label>
              <input value={customSymbol} onChange={e => setCustomSymbol(e.target.value)}
                className="input-field font-mono" placeholder="e.g. RELIANCE, TCS, AAPL, TSLA" />
              <p className="text-xs font-body text-slate-600 mt-2">
                For NSE stocks use the base ticker (RELIANCE, not RELIANCE.NS). US stocks work directly.
              </p>
            </div>
          )}
        </div>

        {/* Step 3 — Analysis type */}
        <div className="glass-card p-7 mb-8">
          <div className="text-xs font-mono text-slate-600 uppercase tracking-wider mb-4">Step 3 — Report Type</div>
          <div className="space-y-3">
            {ANALYSIS_TYPES.map((t) => (
              <button key={t.value} onClick={() => setAnalysisType(t.value)}
                className="w-full p-4 rounded-xl text-left flex items-start gap-3 transition-all"
                style={{
                  background: analysisType === t.value ? 'rgba(16,185,129,0.08)' : 'rgba(255,255,255,0.02)',
                  border: `1px solid ${analysisType === t.value ? 'rgba(16,185,129,0.3)' : 'rgba(255,255,255,0.06)'}`,
                }}>
                <div className="w-4 h-4 rounded-full border-2 shrink-0 mt-0.5 flex items-center justify-center"
                  style={{ borderColor: analysisType === t.value ? '#10b981' : 'rgba(255,255,255,0.2)' }}>
                  {analysisType === t.value && (
                    <div className="w-2 h-2 rounded-full bg-emerald-400" />
                  )}
                </div>
                <div>
                  <div className="font-display font-600 text-white text-sm">{t.label}</div>
                  <div className="text-xs font-body text-slate-500 mt-0.5">{t.desc}</div>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Summary + Generate */}
        {finalSymbol && (
          <div className="glass-card p-6 mb-6"
            style={{ background: 'rgba(16,185,129,0.04)', borderColor: 'rgba(16,185,129,0.15)' }}>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center font-mono font-500 text-sm"
                style={{ background: 'rgba(16,185,129,0.1)', color: '#10b981' }}>
                {finalSymbol.slice(0, 2)}
              </div>
              <div>
                <div className="font-display font-600 text-white">{finalSymbol}</div>
                <div className="text-xs font-mono text-slate-500 capitalize">{assetType} · {ANALYSIS_TYPES.find(t => t.value === analysisType)?.label}</div>
              </div>
            </div>
          </div>
        )}

        <button onClick={submit} disabled={loading || !finalSymbol}
          className="btn-primary w-full justify-center text-base py-4">
          {loading ? (
            <>
              <div className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white"
                style={{ animation: 'spin 0.8s linear infinite' }} />
              <span>Queuing report...</span>
            </>
          ) : (
            <>
              <span>Generate Report</span>
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </>
          )}
        </button>

        <p className="text-xs font-body text-slate-600 text-center mt-4">
          Report takes 60–120 seconds to generate. You'll be redirected to status page.
        </p>
      </div>
    </div>
  )
}
