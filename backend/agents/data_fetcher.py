import httpx
from datetime import datetime
from typing import Optional
from core.config import get_settings
import asyncio

settings = get_settings()

# ── Twelve Data symbol maps ────────────────────────────────────
# Twelve Data uses these exact symbols for commodities/forex/indices
COMMODITY_TD = {
    "SILVER":      "XAG/USD",
    "GOLD":        "XAU/USD",
    "CRUDE_BRENT": "BCO/USD",
    "CRUDE_WTI":   "WTI/USD",
    "NATURAL_GAS": "NATURALGAS/USD",
    "COPPER":      "COPPER/USD",
}

MACRO_TD = {
    "DXY":          "DXY",
    "US_10Y_YIELD": "TNX",
    "NIFTY50":      "NSEI",
    "USDINR":       "USD/INR",
    "VIX_US":       "VIX",
}

TD_BASE = "https://api.twelvedata.com"


# ── Core Twelve Data helpers ───────────────────────────────────

async def _td_price(symbol: str) -> Optional[float]:
    """Get latest price for any Twelve Data symbol."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{TD_BASE}/price", params={
                "symbol":  symbol,
                "apikey":  settings.twelvedata_api_key,
            })
            data = r.json()
            if data.get("status") == "error":
                return None
            return float(data.get("price", 0)) or None
    except Exception:
        return None


async def _td_time_series(symbol: str, outputsize: int = 90) -> list:
    """Get OHLCV daily time series. Returns list of dicts oldest→newest."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(f"{TD_BASE}/time_series", params={
                "symbol":     symbol,
                "interval":   "1day",
                "outputsize": outputsize,
                "apikey":     settings.twelvedata_api_key,
            })
            data = r.json()
            if data.get("status") == "error":
                return []
            values = data.get("values", [])
            # TD returns newest first — reverse to oldest first
            return list(reversed(values))
    except Exception:
        return []


async def _td_indicator(symbol: str, indicator: str, **params) -> Optional[float]:
    """
    Get latest value of a technical indicator from Twelve Data.
    indicator: "rsi", "sma", "ema" etc.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{TD_BASE}/{indicator}", params={
                "symbol":   symbol,
                "interval": "1day",
                "apikey":   settings.twelvedata_api_key,
                **params,
            })
            data = r.json()
            if data.get("status") == "error":
                return None
            values = data.get("values", [])
            if not values:
                return None
            # first value in response = most recent
            key = list(values[0].keys())[-1]  # rsi/sma/ema key
            return round(float(values[0][key]), 2)
    except Exception:
        return None


async def _td_52w(symbol: str) -> tuple[Optional[float], Optional[float]]:
    """Returns (52w_high, 52w_low) from 1-year daily data."""
    series = await _td_time_series(symbol, outputsize=252)
    if not series:
        return None, None
    highs = [float(c["high"]) for c in series if c.get("high")]
    lows  = [float(c["low"])  for c in series if c.get("low")]
    return (round(max(highs), 4), round(min(lows), 4)) if highs else (None, None)


# ── Public functions ───────────────────────────────────────────

async def get_commodity_data(symbol: str) -> dict:
    td_sym = COMMODITY_TD.get(symbol.upper())
    if not td_sym:
        return {"error": f"Unknown symbol: {symbol}"}

    try:
        # Fetch price + time series + indicators concurrently
        # TD free = 8 calls/min — we batch carefully
        price_task   = _td_price(td_sym)
        series_task  = _td_time_series(td_sym, outputsize=60)
        rsi_task     = _td_indicator(td_sym, "rsi",  time_period=14)
        sma20_task   = _td_indicator(td_sym, "sma",  time_period=20)
        sma50_task   = _td_indicator(td_sym, "sma",  time_period=50)

        price, series, rsi, sma20, sma50 = await asyncio.gather(
            price_task, series_task, rsi_task, sma20_task, sma50_task
        )

        # 52w high/low from series
        hi52w, lo52w = None, None
        if series:
            highs = [float(c["high"]) for c in series if c.get("high")]
            lows  = [float(c["low"])  for c in series if c.get("low")]
            hi52w = round(max(highs), 4) if highs else None
            lo52w = round(min(lows),  4) if lows  else None

        pct_from_high = (
            round((price - hi52w) / hi52w * 100, 2)
            if price and hi52w else None
        )

        price_history = []
        for candle in series:
            try:
                price_history.append({
                    "date":   candle["datetime"],
                    "open":   round(float(candle["open"]),   4),
                    "high":   round(float(candle["high"]),   4),
                    "low":    round(float(candle["low"]),    4),
                    "close":  round(float(candle["close"]),  4),
                    "volume": int(float(candle.get("volume", 0))),
                })
            except Exception:
                continue

        return {
            "symbol":           symbol,
            "ticker":           td_sym,
            "current_price":    price,
            "currency":         "USD",
            "week_52_high":     hi52w,
            "week_52_low":      lo52w,
            "pct_from_52w_high": pct_from_high,
            "sma_20":           sma20,
            "sma_50":           sma50,
            "rsi_14":           rsi,
            "price_history":    price_history,
            "fetched_at":       datetime.utcnow().isoformat(),
        }

    except Exception as e:
        return {"error": str(e), "symbol": symbol}


async def get_equity_data(ticker: str) -> dict:
    """
    Equity data via Twelve Data.
    For Indian stocks use BSE/NSE suffix e.g. "RELIANCE:NSE"
    For US stocks just the ticker e.g. "AAPL"
    Fundamentals (PE, PB etc.) not available on TD free tier —
    those fields will be None. Price + technicals work fine.
    """
    try:
        price_task  = _td_price(ticker)
        series_task = _td_time_series(ticker, outputsize=60)
        rsi_task    = _td_indicator(ticker, "rsi",  time_period=14)
        sma50_task  = _td_indicator(ticker, "sma",  time_period=50)
        sma200_task = _td_indicator(ticker, "sma",  time_period=200)

        price, series, rsi, sma50, sma200 = await asyncio.gather(
            price_task, series_task, rsi_task, sma50_task, sma200_task
        )

        hi52w, lo52w = None, None
        if series:
            highs = [float(c["high"]) for c in series if c.get("high")]
            lows  = [float(c["low"])  for c in series if c.get("low")]
            hi52w = round(max(highs), 2) if highs else None
            lo52w = round(min(lows),  2) if lows  else None

        price_history = []
        for candle in series:
            try:
                price_history.append({
                    "date":   candle["datetime"],
                    "close":  round(float(candle["close"]), 2),
                    "volume": int(float(candle.get("volume", 0))),
                })
            except Exception:
                continue

        return {
            "ticker":        ticker,
            "company_name":  ticker,       # TD free doesn't give company name
            "current_price": price,
            "currency":      "INR",
            "week_52_high":  hi52w,
            "week_52_low":   lo52w,
            "sma_50":        sma50,
            "sma_200":       sma200,
            "rsi_14":        rsi,
            "price_history": price_history,
            # Fundamentals below — None on free tier
            # Upgrade TD plan or add separate BSE/NSE scraper later
            "sector":                None,
            "industry":              None,
            "market_cap":            None,
            "pe_ratio":              None,
            "forward_pe":            None,
            "pb_ratio":              None,
            "ev_ebitda":             None,
            "revenue":               None,
            "revenue_growth":        None,
            "gross_margin":          None,
            "operating_margin":      None,
            "profit_margin":         None,
            "roe":                   None,
            "roa":                   None,
            "debt_to_equity":        None,
            "current_ratio":         None,
            "free_cashflow":         None,
            "dividend_yield":        None,
            "beta":                  None,
            "analyst_target_price":  None,
            "analyst_recommendation":None,
            "analyst_count":         None,
            "fetched_at":            datetime.utcnow().isoformat(),
        }

    except Exception as e:
        return {"error": str(e), "ticker": ticker}


async def get_macro_snapshot() -> dict:
    """
    Macro indicators via Twelve Data.
    All fetched concurrently — no sleep needed (TD is reliable).
    """
    results = {}

    async def _fetch_one(name: str, sym: str):
        price = await _td_price(sym)
        results[name] = {
            "value":          price,
            "change_pct_1d":  None,   # would need 2 calls — skip for now
        }

    tasks = [_fetch_one(name, sym) for name, sym in MACRO_TD.items()]
    await asyncio.gather(*tasks)

    # Gold-Silver ratio
    try:
        gold_p   = await _td_price("XAU/USD")
        silver_p = await _td_price("XAG/USD")
        if gold_p and silver_p:
            results["GOLD_SILVER_RATIO"] = {
                "value": round(gold_p / silver_p, 2)
            }
    except Exception:
        pass

    results["fetched_at"] = datetime.utcnow().isoformat()
    return results


async def get_fred_data() -> dict:
    """US macro data from FRED API — reliable, official, always works."""
    if not settings.fred_api_key:
        return {"error": "FRED API key not configured"}

    fred_series = {
        "fed_funds_rate":     "FEDFUNDS",
        "cpi_yoy":            "CPIAUCSL",
        "core_pce":           "PCEPILFE",
        "unemployment":       "UNRATE",
        "us_10y_yield":       "GS10",
        "us_real_gdp_growth": "A191RL1Q225SBEA",
    }

    base_url = "https://api.stlouisfed.org/fred/series/observations"
    results  = {}

    async with httpx.AsyncClient(timeout=10.0) as client:
        for name, series_id in fred_series.items():
            try:
                resp = await client.get(base_url, params={
                    "series_id":  series_id,
                    "api_key":    settings.fred_api_key,
                    "file_type":  "json",
                    "sort_order": "desc",
                    "limit":      2,
                })
                obs = resp.json().get("observations", [])
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
                results[name] = {"error": str(e)}

    results["fetched_at"] = datetime.utcnow().isoformat()
    return results


async def get_news(query: str, page_size: int = 10) -> list:
    if not settings.news_api_key:
        return []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q":        query,
                    "apiKey":   settings.news_api_key,
                    "pageSize": page_size,
                    "sortBy":   "publishedAt",
                    "language": "en",
                }
            )
            articles = resp.json().get("articles", [])
            return [
                {
                    "title":        a.get("title"),
                    "source":       a.get("source", {}).get("name"),
                    "published_at": a.get("publishedAt"),
                    "url":          a.get("url"),
                    "description":  a.get("description"),
                }
                for a in articles
            ]
    except Exception:
        return []