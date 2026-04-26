"""
agents/data_fetcher.py

Data Hierarchy:
    Tier 1 — Live APIs (source of truth)
        Groww API    → NSE/BSE live prices, OHLC
        nsepython    → Nifty50, Sensex, FII/DII flows
        Finnhub      → USD/INR forex, commodities, US stocks
        FRED         → US macro (10Y, DXY, VIX, Fed rate, CPI, GDP)
        NewsAPI      → Headlines per asset

    Tier 2 — Cache (cached_data table in Supabase/Postgres)
        Commodity    → TTL 6 hours
        Equity       → TTL 1 hour
        Macro        → TTL 1 hour
        FRED         → TTL 24 hours
        News         → TTL 30 minutes

    Tier 3 — Gemini (llm_analyst.py)
        ONLY receives structured data from Tier 1/2.
        If any field is None → LLM says "Data unavailable".
        LLM never fills, estimates, or hallucinates numbers.
"""

import httpx
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from core.config import get_settings

settings = get_settings()

FINNHUB_BASE = "https://finnhub.io/api/v1"
FRED_BASE    = "https://api.stlouisfed.org/fred/series/observations"

FINNHUB_COMMODITIES = {
    "GOLD":        "OANDA:XAU_USD",
    "SILVER":      "OANDA:XAG_USD",
    "CRUDE_WTI":   "OANDA:WTICO_USD",
    "CRUDE_BRENT": "OANDA:BCO_USD",
    "NATURAL_GAS": "OANDA:NATGAS_USD",
    "COPPER":      "OANDA:COPPER_USD",
}

FRED_SERIES = {
    "US_10Y_YIELD":   "GS10",
    "DXY":            "DTWEXBGS",
    "VIX_US":         "VIXCLS",
    "FED_FUNDS_RATE": "FEDFUNDS",
    "CPI_YOY":        "CPIAUCSL",
    "CORE_PCE":       "PCEPILFE",
    "UNEMPLOYMENT":   "UNRATE",
    "US_GDP_GROWTH":  "A191RL1Q225SBEA",
}


# ── Local calculations ─────────────────────────────────────────

def _rsi(closes: list, period: int = 14) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains  = [d if d > 0 else 0.0 for d in deltas]
    losses = [abs(d) if d < 0 else 0.0 for d in deltas]
    ag = sum(gains[-period:]) / period
    al = sum(losses[-period:]) / period
    if al == 0:
        return 100.0
    return round(100 - (100 / (1 + ag / al)), 2)


def _sma(closes: list, period: int) -> Optional[float]:
    if len(closes) < period:
        return None
    return round(sum(closes[-period:]) / period, 4)


# ── Tier 2: Cache Layer ────────────────────────────────────────

async def _cache_get(key: str) -> Optional[dict]:
    """Check cache. Returns data dict if valid, None if miss or expired."""
    try:
        from supabase import create_client
        sb  = create_client(settings.supabase_url, settings.supabase_service_key)
        res = sb.table("cached_data").select("*").eq("cache_key", key).execute()
        if not res.data:
            return None
        row        = res.data[0]
        fetched_at = datetime.fromisoformat(row["fetched_at"])
        ttl        = row.get("ttl_minutes", 60)
        if datetime.utcnow() - fetched_at > timedelta(minutes=ttl):
            return None  # expired
        return row["data"]
    except Exception:
        return None


async def _cache_set(key: str, data: dict, ttl_minutes: int = 60):
    """Write to cache. Non-fatal on failure."""
    try:
        from supabase import create_client
        sb = create_client(settings.supabase_url, settings.supabase_service_key)
        sb.table("cached_data").upsert({
            "cache_key":   key,
            "data":        data,
            "fetched_at":  datetime.utcnow().isoformat(),
            "ttl_minutes": ttl_minutes,
        }, on_conflict="cache_key").execute()
    except Exception:
        pass


# ── Tier 1: Finnhub ────────────────────────────────────────────

async def _fh_quote(symbol: str) -> dict:
    if not settings.finnhub_api_key:
        return {}
    try:
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.get(f"{FINNHUB_BASE}/quote",
                            params={"symbol": symbol, "token": settings.finnhub_api_key})
            d = r.json()
            return d if d.get("c", 0) != 0 else {}
    except Exception:
        return {}


async def _fh_candles(symbol: str, days: int = 365) -> list:
    if not settings.finnhub_api_key:
        return []
    try:
        to_ts   = int(datetime.utcnow().timestamp())
        from_ts = int((datetime.utcnow() - timedelta(days=days)).timestamp())
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.get(f"{FINNHUB_BASE}/stock/candle", params={
                "symbol": symbol, "resolution": "D",
                "from": from_ts, "to": to_ts,
                "token": settings.finnhub_api_key,
            })
            d = r.json()
            if d.get("s") != "ok":
                return []
            closes = d.get("c", [])
            ts     = d.get("t", [])
            opens  = d.get("o", [])
            highs  = d.get("h", [])
            lows   = d.get("l", [])
            vols   = d.get("v", [])
            return [
                {
                    "date":   datetime.utcfromtimestamp(ts[i]).strftime("%Y-%m-%d"),
                    "open":   opens[i],
                    "high":   highs[i],
                    "low":    lows[i],
                    "close":  closes[i],
                    "volume": vols[i] if i < len(vols) else None,
                }
                for i in range(len(closes))
            ]
    except Exception:
        return []


async def _fh_forex(from_cur: str, to_cur: str) -> Optional[float]:
    if not settings.finnhub_api_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.get(f"{FINNHUB_BASE}/forex/rates",
                            params={"base": from_cur, "token": settings.finnhub_api_key})
            return r.json().get("quote", {}).get(to_cur)
    except Exception:
        return None


# ── Tier 1: Groww ──────────────────────────────────────────────

def _groww_client():
    if not settings.groww_api_key or not settings.groww_api_secret:
        return None
    try:
        from growwapi import GrowwAPI
        token = GrowwAPI.get_access_token(
            api_key=settings.groww_api_key,
            secret=settings.groww_api_secret,
        )
        return GrowwAPI(token)
    except Exception:
        return None


async def _groww_quote(symbol: str, exchange: str = "NSE") -> dict:
    try:
        g = _groww_client()
        if not g:
            return {}
        loop = asyncio.get_event_loop()
        q = await loop.run_in_executor(
            None,
            lambda: g.get_ltp(trading_symbol=symbol, exchange=exchange, segment="CASH")
        )
        if not q:
            return {}
        return {
            "price":      q.get("ltp"),
            "high":       q.get("high"),
            "low":        q.get("low"),
            "volume":     q.get("volume"),
            "change_pct": q.get("change_percent"),
        }
    except Exception:
        return {}


async def _groww_ohlc(symbol: str, exchange: str = "NSE", days: int = 365) -> list:
    try:
        g = _groww_client()
        if not g:
            return []
        to_d   = datetime.utcnow().strftime("%Y-%m-%d")
        from_d = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
        loop   = asyncio.get_event_loop()
        data   = await loop.run_in_executor(
            None,
            lambda: g.get_historical_data(
                trading_symbol=symbol, exchange=exchange,
                segment="CASH", from_date=from_d,
                to_date=to_d, interval="1d",
            )
        )
        if not data:
            return []
        candles = data.get("candles", [])
        return [
            {
                "date":   c[0][:10] if isinstance(c[0], str) else str(c[0]),
                "open":   c[1], "high": c[2],
                "low":    c[3], "close": c[4],
                "volume": c[5] if len(c) > 5 else None,
            }
            for c in candles if len(c) >= 5
        ]
    except Exception:
        return []


# ── Tier 1: nsepython ──────────────────────────────────────────

async def _nse_index(name: str) -> Optional[float]:
    try:
        loop = asyncio.get_event_loop()
        from nsepython import nse_get_index_quote
        data = await loop.run_in_executor(None, lambda: nse_get_index_quote(name))
        return float(data.get("last", 0)) or None if data else None
    except Exception:
        return None


async def _nse_fii_dii() -> dict:
    try:
        loop = asyncio.get_event_loop()
        from nsepython import fii_dii_data
        data = await loop.run_in_executor(None, fii_dii_data)
        if isinstance(data, list) and data:
            row = data[0]
            return {
                "fii_net": row.get("fiiNet"),
                "dii_net": row.get("diiNet"),
                "date":    row.get("date"),
            }
        return {"fii_net": None, "dii_net": None}
    except Exception:
        return {"fii_net": None, "dii_net": None}


# ── Tier 1: FRED ───────────────────────────────────────────────

async def _fred_latest(series_id: str) -> Optional[float]:
    if not settings.fred_api_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.get(FRED_BASE, params={
                "series_id": series_id, "api_key": settings.fred_api_key,
                "file_type": "json", "sort_order": "desc", "limit": 1,
            })
            obs = r.json().get("observations", [])
            if obs and obs[0]["value"] != ".":
                return float(obs[0]["value"])
    except Exception:
        pass
    return None


# ── Tier 1: NewsAPI ────────────────────────────────────────────

async def get_news(query: str, page_size: int = 8) -> list:
    cache_key = f"news:{query}"
    cached    = await _cache_get(cache_key)
    if cached:
        return cached
    if not settings.news_api_key:
        return []
    try:
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.get("https://newsapi.org/v2/everything", params={
                "q": query, "apiKey": settings.news_api_key,
                "pageSize": page_size, "sortBy": "publishedAt", "language": "en",
            })
            articles = r.json().get("articles", [])
            result = [
                {
                    "title":        a.get("title"),
                    "source":       a.get("source", {}).get("name"),
                    "published_at": a.get("publishedAt"),
                    "url":          a.get("url"),
                    "description":  a.get("description"),
                }
                for a in articles
            ]
            await _cache_set(cache_key, result, ttl_minutes=30)
            return result
    except Exception:
        return []


# ── Public: Commodity Data ─────────────────────────────────────

async def get_commodity_data(symbol: str) -> dict:
    """
    Finnhub → price, OHLC, RSI, SMA.
    Cache TTL: 6 hours.
    None = genuinely unavailable. LLM must not fill these.
    """
    symbol    = symbol.upper()
    cache_key = f"commodity:{symbol}"

    cached = await _cache_get(cache_key)
    if cached:
        cached["from_cache"] = True
        return cached

    fh_sym = FINNHUB_COMMODITIES.get(symbol)
    if not fh_sym:
        return {"error": f"Unknown commodity: {symbol}. Valid: {list(FINNHUB_COMMODITIES.keys())}"}

    quote, candles, news = await asyncio.gather(
        _fh_quote(fh_sym),
        _fh_candles(fh_sym, days=365),
        get_news(f"{symbol} commodity price gold silver crude", page_size=6),
    )

    current_price = quote.get("c") if quote else None
    closes        = [c["close"] for c in candles] if candles else []
    price_history = candles[-60:] if candles else []
    week_52_high  = round(max(c["high"] for c in candles[-252:]), 4) if len(candles) >= 5 else None
    week_52_low   = round(min(c["low"]  for c in candles[-252:]), 4) if len(candles) >= 5 else None
    pct_from_high = round((current_price - week_52_high) / week_52_high * 100, 2) if (current_price and week_52_high) else None

    result = {
        "symbol":            symbol,
        "current_price":     round(current_price, 4) if current_price else None,
        "currency":          "USD",
        "week_52_high":      week_52_high,
        "week_52_low":       week_52_low,
        "pct_from_52w_high": pct_from_high,
        "rsi_14":            _rsi(closes),
        "sma_20":            _sma(closes, 20),
        "sma_50":            _sma(closes, 50),
        "price_history":     price_history,
        "news":              news,
        "fetched_at":        datetime.utcnow().isoformat(),
        "from_cache":        False,
        "data_source":       "Finnhub",
    }

    if current_price:
        await _cache_set(cache_key, result, ttl_minutes=360)

    return result


# ── Public: Indian Equity Data ─────────────────────────────────

async def get_equity_data(ticker: str, exchange: str = "NSE") -> dict:
    """
    Indian stocks → Groww (primary) prices + OHLC.
    US stocks     → Finnhub.
    Cache TTL: 1 hour.
    """
    ticker    = ticker.upper()
    cache_key = f"equity:{ticker}:{exchange}"

    cached = await _cache_get(cache_key)
    if cached:
        cached["from_cache"] = True
        return cached

    is_indian = exchange in ("NSE", "BSE")

    if is_indian:
        quote, candles, news = await asyncio.gather(
            _groww_quote(ticker, exchange),
            _groww_ohlc(ticker, exchange, days=365),
            get_news(f"{ticker} NSE India stock", page_size=6),
        )
        current_price = quote.get("price") if quote else None
    else:
        quote, candles, news = await asyncio.gather(
            _fh_quote(ticker),
            _fh_candles(ticker, days=365),
            get_news(f"{ticker} stock US", page_size=6),
        )
        current_price = quote.get("c") if quote else None

    closes        = [c["close"] for c in candles] if candles else []
    price_history = candles[-60:] if candles else []
    week_52_high  = round(max(c["high"] for c in candles[-252:]), 2) if len(candles) >= 5 else None
    week_52_low   = round(min(c["low"]  for c in candles[-252:]), 2) if len(candles) >= 5 else None

    result = {
        "ticker":        ticker,
        "exchange":      exchange,
        "current_price": round(current_price, 2) if current_price else None,
        "currency":      "INR" if is_indian else "USD",
        "week_52_high":  week_52_high,
        "week_52_low":   week_52_low,
        "rsi_14":        _rsi(closes),
        "sma_50":        _sma(closes, 50),
        "sma_200":       _sma(closes, 200),
        "price_history": price_history,
        "news":          news,
        "fetched_at":    datetime.utcnow().isoformat(),
        "from_cache":    False,
        "data_source":   "Groww" if is_indian else "Finnhub",
    }

    if current_price:
        await _cache_set(cache_key, result, ttl_minutes=60)

    return result


# ── Public: Macro Snapshot ─────────────────────────────────────

async def get_macro_snapshot() -> dict:
    """
    FRED (US macro) + Finnhub (forex) + nsepython (Indian indices + FII/DII).
    Cache TTL: 1 hour.
    """
    cache_key = "macro:snapshot"
    cached    = await _cache_get(cache_key)
    if cached:
        cached["from_cache"] = True
        return cached

    # FRED — all concurrent, no rate limits
    fred_vals = await asyncio.gather(*[_fred_latest(sid) for sid in FRED_SERIES.values()])
    fred_data = dict(zip(FRED_SERIES.keys(), fred_vals))

    # Finnhub forex + commodity quotes
    usdinr, eurusd, gold_q, silver_q = await asyncio.gather(
        _fh_forex("USD", "INR"),
        _fh_forex("EUR", "USD"),
        _fh_quote(FINNHUB_COMMODITIES["GOLD"]),
        _fh_quote(FINNHUB_COMMODITIES["SILVER"]),
    )

    gold_p   = gold_q.get("c")   if gold_q   else None
    silver_p = silver_q.get("c") if silver_q else None
    gs_ratio = round(gold_p / silver_p, 2) if (gold_p and silver_p) else None

    # nsepython — Indian indices + FII/DII
    nifty50, banknifty, sensex, fii_dii = await asyncio.gather(
        _nse_index("NIFTY 50"),
        _nse_index("NIFTY BANK"),
        _nse_index("SENSEX"),
        _nse_fii_dii(),
    )

    result = {
        # US Macro from FRED
        "US_10Y_YIELD":   {"value": fred_data.get("US_10Y_YIELD"),   "unit": "%"},
        "DXY":            {"value": fred_data.get("DXY"),            "unit": "index"},
        "VIX_US":         {"value": fred_data.get("VIX_US"),         "unit": "index"},
        "FED_FUNDS_RATE": {"value": fred_data.get("FED_FUNDS_RATE"), "unit": "%"},
        "CPI_YOY":        {"value": fred_data.get("CPI_YOY"),        "unit": "index"},
        "CORE_PCE":       {"value": fred_data.get("CORE_PCE"),       "unit": "index"},
        "UNEMPLOYMENT":   {"value": fred_data.get("UNEMPLOYMENT"),   "unit": "%"},
        "US_GDP_GROWTH":  {"value": fred_data.get("US_GDP_GROWTH"),  "unit": "%"},

        # Forex from Finnhub
        "USDINR": {"value": round(usdinr, 4) if usdinr else None, "unit": "INR"},
        "EURUSD": {"value": round(eurusd, 4) if eurusd else None, "unit": "USD"},

        # Commodities derived
        "GOLD_PRICE":        {"value": round(gold_p, 2)   if gold_p   else None, "unit": "USD"},
        "SILVER_PRICE":      {"value": round(silver_p, 4) if silver_p else None, "unit": "USD"},
        "GOLD_SILVER_RATIO": {"value": gs_ratio,                                  "unit": "ratio"},

        # Indian indices from nsepython
        "NIFTY50":    {"value": nifty50,   "unit": "points"},
        "BANKNIFTY":  {"value": banknifty, "unit": "points"},
        "SENSEX":     {"value": sensex,    "unit": "points"},

        # FII/DII flows
        "FII_DII": fii_dii,

        "fetched_at":   datetime.utcnow().isoformat(),
        "from_cache":   False,
        "data_sources": ["FRED", "Finnhub", "nsepython"],
    }

    await _cache_set(cache_key, result, ttl_minutes=60)
    return result


# ── Public: Full FRED data ─────────────────────────────────────

async def get_fred_data() -> dict:
    """Detailed FRED macro data. Cache TTL: 24 hours."""
    cache_key = "fred:full"
    cached    = await _cache_get(cache_key)
    if cached:
        return cached

    if not settings.fred_api_key:
        return {"error": "FRED_API_KEY not set"}

    results = {}
    async with httpx.AsyncClient(timeout=10.0) as client:
        for name, sid in FRED_SERIES.items():
            try:
                r = await client.get(FRED_BASE, params={
                    "series_id": sid, "api_key": settings.fred_api_key,
                    "file_type": "json", "sort_order": "desc", "limit": 2,
                })
                obs = r.json().get("observations", [])
                if obs:
                    val  = float(obs[0]["value"]) if obs[0]["value"] != "." else None
                    prev = float(obs[1]["value"]) if len(obs) > 1 and obs[1]["value"] != "." else None
                    results[name] = {
                        "value":      val,
                        "date":       obs[0]["date"],
                        "prev_value": prev,
                        "change":     round(val - prev, 3) if (val and prev) else None,
                    }
            except Exception as e:
                results[name] = {"value": None, "error": str(e)}

    results["fetched_at"] = datetime.utcnow().isoformat()
    await _cache_set(cache_key, results, ttl_minutes=1440)
    return results