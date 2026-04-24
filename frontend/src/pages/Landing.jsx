import { Link } from 'react-router-dom'
import { useEffect, useRef } from 'react'

const TICKER_ITEMS = [
  { label: 'SILVER', val: '$31.42', chg: '+1.2%', up: true },
  { label: 'GOLD', val: '$2,341', chg: '+0.8%', up: true },
  { label: 'CRUDE WTI', val: '$78.91', chg: '-0.3%', up: false },
  { label: 'DXY', val: '104.2', chg: '-0.1%', up: false },
  { label: 'USD/INR', val: '83.41', chg: '+0.2%', up: true },
  { label: 'NIFTY 50', val: '22,450', chg: '+0.6%', up: true },
  { label: 'US 10Y', val: '4.35%', chg: '-2bp', up: false },
  { label: 'COPPER', val: '$4.12', chg: '+0.9%', up: true },
  { label: 'NAT GAS', val: '$2.18', chg: '-1.4%', up: false },
  { label: 'VIX', val: '13.8', chg: '-0.4%', up: false },
]

const MODULES = [
  {
    icon: '◈',
    label: 'Module 01',
    title: 'Commodity Intelligence',
    desc: 'Gold, Silver, Crude Oil, Copper — price action, RSI, SMA with macro correlation.',
    tags: ['Gold', 'Silver', 'Crude', 'Copper'],
    color: '#F59E0B',
  },
  {
    icon: '◉',
    label: 'Module 02',
    title: 'Equity Analysis',
    desc: 'NSE/BSE + US equities. Technicals, fundamentals, analyst targets.',
    tags: ['NSE', 'BSE', 'US Stocks', 'ETFs'],
    color: '#3b82f6',
  },
  {
    icon: '◎',
    label: 'Module 03',
    title: 'India Macro',
    desc: 'RBI rate decisions, GDP, FPI flows, INR trend, CPI — in one snapshot.',
    tags: ['RBI', 'GDP', 'FPI', 'CPI'],
    color: '#10b981',
  },
  {
    icon: '◐',
    label: 'Module 04',
    title: 'Global Macro',
    desc: 'Fed/ECB decisions, US yield curve, DXY, geopolitical risk indicators.',
    tags: ['Fed', 'ECB', 'DXY', 'Yields'],
    color: '#8b5cf6',
  },
  {
    icon: '◑',
    label: 'Module 05 — Moat',
    title: 'State-Level Intelligence',
    desc: 'How TN, GJ, MH policy shifts, industrial output & local elections affect your portfolio.',
    tags: ['Tamil Nadu', 'Gujarat', 'Maharashtra'],
    color: '#f43f5e',
    highlight: true,
  },
  {
    icon: '◒',
    label: 'Module 06',
    title: 'Mutual Fund & ETF',
    desc: 'AMC flows, NAV trends, sector rotation signals, expense ratio analysis.',
    tags: ['SIP', 'AMC Flows', 'Sector ETFs'],
    color: '#06b6d4',
  },
]

const WHY_CARDS = [
  {
    q: 'You check prices but don\'t know what they mean',
    a: 'FinSight translates raw numbers into plain-language signals. RSI at 72? We tell you what that means for your next move.',
    icon: '→',
  },
  {
    q: 'You read news but can\'t connect it to your holdings',
    a: 'Our macro module links global events — a Fed rate hike, a TN election outcome — directly to how it impacts Silver or Nifty.',
    icon: '→',
  },
  {
    q: 'You want professional analysis, not a Twitter hot take',
    a: 'Every report is investment-grade: executive summary, technicals, macro context, risks, and price targets. Like a Bloomberg brief, built for you.',
    icon: '→',
  },
]

const PRICING = [
  {
    name: 'Free',
    price: '₹0',
    period: '',
    reports: '3 reports / month',
    features: ['Commodity & Equity reports', 'Basic macro snapshot', 'PDF download'],
    cta: 'Get started free',
    href: '/register',
    highlight: false,
  },
  {
    name: 'Starter',
    price: '₹299',
    period: '/month',
    reports: '20 reports / month',
    features: ['All Free features', 'India Macro module', 'Global Macro module', 'Priority generation'],
    cta: 'Start for ₹299',
    href: '/register',
    highlight: false,
  },
  {
    name: 'Pro',
    price: '₹999',
    period: '/month',
    reports: '100 reports / month',
    features: ['All Starter features', 'State Intelligence module', 'Options Intelligence', 'Portfolio Analyser'],
    cta: 'Go Pro',
    href: '/register',
    highlight: true,
  },
  {
    name: 'Business',
    price: '₹4,999',
    period: '/month',
    reports: 'Unlimited',
    features: ['All Pro features', 'API access', 'Custom modules', 'White-label reports'],
    cta: 'Contact us',
    href: '/register',
    highlight: false,
  },
]

function TickerBar() {
  const doubled = [...TICKER_ITEMS, ...TICKER_ITEMS]
  return (
    <div className="overflow-hidden py-3 border-y border-white/5" style={{ background: 'rgba(16,185,129,0.03)' }}>
      <div className="flex gap-10 whitespace-nowrap" style={{ animation: 'ticker 40s linear infinite' }}>
        {doubled.map((item, i) => (
          <span key={i} className="flex items-center gap-2 text-xs font-mono shrink-0">
            <span className="text-slate-500">{item.label}</span>
            <span className="text-white">{item.val}</span>
            <span className={item.up ? 'text-emerald-400' : 'text-red-400'}>{item.chg}</span>
            <span className="text-slate-700 ml-4">|</span>
          </span>
        ))}
      </div>
    </div>
  )
}

export default function Landing() {
  return (
    <div className="min-h-screen">

      {/* Hero */}
      <section className="relative min-h-screen flex flex-col justify-center pt-16 overflow-hidden">
        <div className="absolute inset-0 grid-bg opacity-60" />
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full"
          style={{ background: 'radial-gradient(circle, rgba(16,185,129,0.08) 0%, transparent 70%)' }} />

        <TickerBar />

        <div className="relative max-w-7xl mx-auto px-6 py-24 flex flex-col items-center text-center">
          <div className="section-label mb-8">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block" style={{ animation: 'pulse 2s ease-in-out infinite' }} />
            AI-Powered Financial Intelligence
          </div>

          <h1 className="font-display font-800 text-5xl md:text-7xl leading-none tracking-tight mb-6 max-w-4xl">
            Stop guessing.<br />
            <span className="text-gradient">Start knowing.</span>
          </h1>

          <p className="font-body text-slate-400 text-lg md:text-xl max-w-2xl mb-4 leading-relaxed">
            You're a retail investor. You see the numbers. You read the headlines.
            But connecting it all into a <em className="text-slate-300 not-italic">decision</em>?
            That's where most people get lost.
          </p>
          <p className="font-body text-slate-500 text-base max-w-xl mb-12">
            FinSight AI generates professional-grade investment reports — commodities, equities,
            macro, and even how <span className="text-slate-300">state-level policy in Tamil Nadu or Gujarat</span> affects your portfolio.
          </p>

          <div className="flex flex-wrap gap-4 justify-center mb-16">
            <Link to="/register" className="btn-primary text-base px-8 py-4">
              <span>Generate your first report free</span>
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </Link>
            <a href="#how-it-works" className="btn-outline text-base px-8 py-4">See how it works</a>
          </div>

          {/* stat row */}
          <div className="flex flex-wrap gap-12 justify-center">
            {[
              { val: '8', label: 'Intelligence Modules' },
              { val: '6+', label: 'Data Sources' },
              { val: '<2min', label: 'Report Generation' },
              { val: 'Free', label: 'To Start' },
            ].map((s, i) => (
              <div key={i} className="text-center">
                <div className="font-display font-700 text-3xl text-gradient">{s.val}</div>
                <div className="text-xs font-mono text-slate-500 uppercase tracking-wider mt-1">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Why FinSight */}
      <section className="py-24 relative" id="why">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex flex-col items-center text-center mb-16">
            <div className="section-label mb-4">The Problem We Solve</div>
            <h2 className="font-display font-700 text-4xl md:text-5xl mb-4">
              You already want to invest.<br />
              <span className="text-gradient">You just don't know where to look.</span>
            </h2>
            <p className="text-slate-500 font-body max-w-lg">
              FinSight is built for the investor who thinks in fundamentals but needs the data to back it up.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {WHY_CARDS.map((c, i) => (
              <div key={i} className="glass-card p-8">
                <div className="text-2xl text-emerald-400 mb-4 font-mono">{c.icon}</div>
                <h3 className="font-display font-600 text-white text-lg mb-3 leading-snug">{c.q}</h3>
                <p className="font-body text-slate-400 text-sm leading-relaxed">{c.a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-24 relative" id="how-it-works">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex flex-col items-center text-center mb-16">
            <div className="section-label mb-4">How It Works</div>
            <h2 className="font-display font-700 text-4xl">Three steps to clarity</h2>
          </div>

          <div className="grid md:grid-cols-3 gap-8 relative">
            <div className="hidden md:block absolute top-10 left-1/3 right-1/3 h-px"
              style={{ background: 'linear-gradient(90deg, transparent, rgba(16,185,129,0.3), transparent)' }} />

            {[
              { step: '01', title: 'Pick your asset', desc: 'Select commodity, equity, or macro. Type any symbol — SILVER, RELIANCE, GOLD.' },
              { step: '02', title: 'We fetch & analyse', desc: 'FinSight pulls live data from Alpha Vantage, FRED, and NewsAPI, then Gemini builds the analysis.' },
              { step: '03', title: 'Download your report', desc: 'Get a professional DOCX report — executive summary, technicals, macro context, risks, targets.' },
            ].map((s, i) => (
              <div key={i} className="glass-card p-8 flex flex-col items-start">
                <div className="font-mono text-5xl font-700 text-emerald-400/20 mb-4">{s.step}</div>
                <h3 className="font-display font-600 text-white text-xl mb-3">{s.title}</h3>
                <p className="font-body text-slate-400 text-sm leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Modules */}
      <section className="py-24" id="modules">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex flex-col items-center text-center mb-16">
            <div className="section-label mb-4">Intelligence Modules</div>
            <h2 className="font-display font-700 text-4xl mb-4">
              Every angle covered
            </h2>
            <p className="text-slate-500 font-body max-w-lg">
              From global macro to Tamil Nadu industrial output — FinSight connects the dots no other retail tool does.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
            {MODULES.map((m, i) => (
              <div key={i} className={`glass-card p-7 relative overflow-hidden ${m.highlight ? 'ring-1 ring-rose-500/30' : ''}`}>
                {m.highlight && (
                  <div className="absolute top-0 right-0 text-xs font-mono px-3 py-1 rounded-bl-xl"
                    style={{ background: 'rgba(244,63,94,0.15)', color: '#f43f5e', border: '1px solid rgba(244,63,94,0.2)' }}>
                    Unique Moat ◆
                  </div>
                )}
                <div className="text-2xl mb-3" style={{ color: m.color }}>{m.icon}</div>
                <div className="text-xs font-mono text-slate-600 mb-2">{m.label}</div>
                <h3 className="font-display font-600 text-white text-lg mb-3">{m.title}</h3>
                <p className="font-body text-slate-400 text-sm leading-relaxed mb-5">{m.desc}</p>
                <div className="flex flex-wrap gap-2">
                  {m.tags.map((t) => (
                    <span key={t} className="text-xs font-mono px-2.5 py-1 rounded-full"
                      style={{ background: `${m.color}15`, color: m.color, border: `1px solid ${m.color}30` }}>
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* State Intelligence callout */}
          <div className="mt-8 p-8 rounded-2xl relative overflow-hidden"
            style={{ background: 'rgba(244,63,94,0.05)', border: '1px solid rgba(244,63,94,0.15)' }}>
            <div className="max-w-3xl">
              <div className="text-xs font-mono text-rose-400 uppercase tracking-wider mb-3">Why State Intelligence is our moat</div>
              <h3 className="font-display font-600 text-white text-2xl mb-4">
                When Maharashtra changes its EV subsidy policy, it moves Tata Motors.<br />
                When TN announces a new semiconductor zone, it moves the supply chain.
              </h3>
              <p className="font-body text-slate-400 leading-relaxed">
                No retail platform tracks this. Bloomberg terminals don't surface it cleanly for retail investors.
                FinSight's State Intelligence module connects local policy shifts, industrial data,
                and election outcomes to portfolio impact — in plain language, not in a 40-page government document.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="py-24" id="pricing">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex flex-col items-center text-center mb-16">
            <div className="section-label mb-4">Pricing</div>
            <h2 className="font-display font-700 text-4xl mb-4">Start free. Scale when ready.</h2>
            <p className="text-slate-500 font-body">No credit card for free tier. Cancel anytime.</p>
          </div>

          <div className="grid md:grid-cols-4 gap-5">
            {PRICING.map((p) => (
              <div key={p.name}
                className={`glass-card p-7 flex flex-col ${p.highlight ? 'ring-1 ring-emerald-500/40 relative' : ''}`}>
                {p.highlight && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 text-xs font-mono px-3 py-1 rounded-full"
                    style={{ background: 'linear-gradient(135deg,#10b981,#059669)', color: 'white' }}>
                    Most Popular
                  </div>
                )}
                <div className="text-slate-500 font-mono text-xs uppercase tracking-wider mb-3">{p.name}</div>
                <div className="mb-4">
                  <span className="font-display font-700 text-3xl text-white">{p.price}</span>
                  <span className="text-slate-500 text-sm font-body">{p.period}</span>
                </div>
                <div className="text-xs font-mono text-emerald-400 mb-5">{p.reports}</div>
                <ul className="space-y-2.5 mb-8 flex-1">
                  {p.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm font-body text-slate-400">
                      <span className="text-emerald-400 mt-0.5 shrink-0">✓</span>
                      {f}
                    </li>
                  ))}
                </ul>
                <Link to={p.href}
                  className={p.highlight ? 'btn-primary text-sm text-center justify-center' : 'btn-outline text-sm text-center justify-center'}>
                  <span>{p.cta}</span>
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-24">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <div className="glass-card p-16 relative overflow-hidden">
            <div className="absolute inset-0 grid-bg opacity-40" />
            <div className="relative">
              <h2 className="font-display font-700 text-4xl md:text-5xl mb-6">
                Your first report is <span className="text-gradient">free.</span>
              </h2>
              <p className="font-body text-slate-400 mb-10 text-lg max-w-lg mx-auto">
                No credit card. No commitment. Just clarity on the assets you care about.
              </p>
              <Link to="/register" className="btn-primary text-base px-10 py-4 inline-flex">
                <span>Generate a free report now</span>
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/5 py-10">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg,#10b981,#059669)' }}>
              <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
                <path d="M3 12L6 8L9 10L13 4" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <span className="font-display font-600 text-sm text-slate-400">FinSight AI</span>
          </div>
          <p className="text-xs font-mono text-slate-600">
            Not financial advice. For informational purposes only.
          </p>
          <p className="text-xs font-body text-slate-600">© 2026 FinSight AI</p>
        </div>
      </footer>
    </div>
  )
}
