"""
agents/data_fetcher.py

Data sources:
  - Alpha Vantage  → commodities (monthly OHLC), equities (daily), forex
  - FRED           → macro indicators (10Y yield, DXY, VIX, Fed rate, CPI, etc.)
  - NewsAPI        → latest headlines

Rate limit reality:
  - AV free tier: 25 requests/day, 5/min  → we add 12s delay between calls
  - FRED free tier: generous, no hard limit
  - NewsAPI free tier: 100 req/day
"""
import httpx
import asyncio
from datetime import datetime
from typing import Optional
from core.config import get_settings

settings = get_settings()

AV_BASE   = "https://www.alphavantage.co/query"
AV_DELAY  = 12.0   # seconds between AV calls (5 req/min limit)

# Alpha Vantage commodity function names
COMMODITY_AV = {
    "SILVER":      "SILVER",
    "GOLD":        "GOLD",
    "CRUDE_BRENT": "BRENT",
    "CRUDE_WTI":   "WTI",
    "NATURAL_GAS": "NATURAL_GAS",
    "COPPER":      "COPPER",
    "ALUMINIUM":   "ALUMINUM",
}


# ── RSI calculation ────────────────────────────────────────────

def _calculate_rsi(closes: list, period: int = 14) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    deltas   = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains    = [d if d > 0 else 0.0 for d in deltas]
    losses   = [abs(d) if d < 0 else 0.0 for d in deltas]
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    return round(100 - (100 / (1 + avg_gain / avg_loss)), 2)


# ── Alpha Vantage helpers ──────────────────────────────────────

async def _av_get(params: dict) -> dict:
    """Single AV request with error handling. Returns raw JSON or {}."""
    if not settings.alpha_vantage_key:
        return {"_error": "ALPHA_VANTAGE_KEY not set in .env"}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            params["apikey"] = settings.alpha_vantage_key
            r = await client.get(AV_BASE, params=params)
            data = r.json()
            # AV returns this when rate limited
            if "Note" in data or "Information" in data:
                note = data.get("Note") or data.get("Information", "")
                return {"_error": f"AV rate limit: {note[:100]}"}
            return data
    except Exception as e:
        return {"_error": str(e)}


async def _av_commodity(function: str) -> list:
    """
    Monthly commodity data from AV.
    Returns list of {date, value} sorted oldest→newest.
    """
    data = await _av_get({"function": function, "interval": "monthly"})
    if "_error" in data:
        return []
    rows = data.get("data", [])
    return list(reversed(rows))   # AV gives newest first


async def _av_quote(symbol: str) -> dict:
    data = await _av_get({"function": "GLOBAL_QUOTE", "symbol": symbol})
    return data.get("Global Quote", {})


async def _av_daily(symbol: str, outputsize: str = "compact") -> dict:
    data = await _av_get({
        "function":   "TIME_SERIES_DAILY",
        "symbol":     symbol,
        "outputsize": outputsize,
    })
    return data.get("Time Series (Daily)", {})


async def _av_forex_daily(from_sym: str, to_sym: str) -> dict:
    data = await _av_get({
        "function":    "FX_DAILY",
        "from_symbol": from_sym,
        "to_symbol":   to_sym,
        "outputsize":  "compact",
    })
    return data.get("Time Series FX (Daily)", {})


# ── FRED helpers ───────────────────────────────────────────────

async def _fred_latest(series_id: str) -> Optional[float]:
    if not settings.fred_api_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                "https://api.stlouisfed.org/fred/series/observations",
                params={
                    "series_id":  series_id,
                    "api_key":    settings.fred_api_key,
                    "file_type":  "json",
                    "sort_order": "desc",
                    "limit":      1,
                },
            )
            obs = r.json().get("observations", [])
            if obs and obs[0]["value"] != ".":
                return float(obs[0]["value"])
    except Exception:
        pass
    return None


# ── Public data functions ──────────────────────────────────────

async def get_commodity_data(symbol: str) -> dict:
    """
    Returns price, technicals, and price history for a commodity.
    Uses AV monthly data → calculates RSI, SMA locally.
    """
    av_function = COMMODITY_AV.get(symbol.upper())
    if not av_function:
        return {"error": f"Unknown symbol: {symbol}. Valid: {list(COMMODITY_AV.keys())}"}

    if not settings.alpha_vantage_key:
        return {"error": "ALPHA_VANTAGE_KEY is not set in your .env file"}

    rows = await _av_commodity(av_function)

    if not rows:
        return {
            "error": (
                f"Alpha Vantage returned no data for {symbol}. "
                "Likely cause: free tier rate limit (25 req/day) or invalid API key. "
                f"Key used: {settings.alpha_vantage_key[:6]}..."
            ),
            "symbol": symbol,
        }

    closes        = []
    price_history = []
    for row in rows[-60:]:
        try:
            val = float(row["value"])
            closes.append(val)
            price_history.append({"date": row["date"], "close": round(val, 4)})
        except Exception:
            continue

    if not closes:
        return {"error": "Price data is empty after parsing", "symbol": symbol}

    current_price = closes[-1]
    last_12       = closes[-12:] if len(closes) >= 12 else closes
    week_52_high  = round(max(last_12), 4)
    week_52_low   = round(min(last_12), 4)
    pct_from_high = round((current_price - week_52_high) / week_52_high * 100, 2)

    sma_20 = round(sum(closes[-20:]) / min(20, len(closes)), 2) if len(closes) >= 5 else None
    sma_50 = round(sum(closes[-50:]) / min(50, len(closes)), 2) if len(closes) >= 5 else None
    rsi    = _calculate_rsi(closes)

    return {
        "symbol":            symbol,
        "ticker":            av_function,
        "current_price":     round(current_price, 4),
        "currency":          "USD",
        "week_52_high":      week_52_high,
        "week_52_low":       week_52_low,
        "pct_from_52w_high": pct_from_high,
        "sma_20":            sma_20,
        "sma_50":            sma_50,
        "rsi_14":            rsi,
        "price_history":     price_history[-60:],
        "fetched_at":        datetime.utcnow().isoformat(),
    }


async def get_equity_data(ticker: str) -> dict:
    """Equity data via AV daily time series."""
    if not settings.alpha_vantage_key:
        return {"error": "ALPHA_VANTAGE_KEY is not set in your .env file"}

    quote, daily = await asyncio.gather(
        _av_quote(ticker),
        _av_daily(ticker, outputsize="full"),
    )

    if not daily:
        return {"error": f"No daily data returned for {ticker}. Check ticker or AV rate limit.", "ticker": ticker}

    sorted_dates = sorted(daily.keys())
    closes = [float(daily[d]["4. close"]) for d in sorted_dates]

    price_history = [
        {
            "date":   d,
            "close":  round(float(daily[d]["4. close"]), 2),
            "volume": int(float(daily[d]["5. volume"])),
        }
        for d in sorted_dates[-60:]
    ]

    current_price = float(quote.get("05. price", closes[-1] if closes else 0))
    hi52  = round(max(float(daily[d]["2. high"]) for d in sorted_dates[-252:]), 2) if len(sorted_dates) >= 5 else None
    lo52  = round(min(float(daily[d]["3. low"])  for d in sorted_dates[-252:]), 2) if len(sorted_dates) >= 5 else None
    sma_50  = round(sum(closes[-50:])  / min(50,  len(closes)), 2) if closes else None
    sma_200 = round(sum(closes[-200:]) / min(200, len(closes)), 2) if closes else None
    rsi     = _calculate_rsi(closes)

    return {
        "ticker":        ticker,
        "current_price": round(current_price, 2),
        "currency":      "USD",
        "week_52_high":  hi52,
        "week_52_low":   lo52,
        "sma_50":        sma_50,
        "sma_200":       sma_200,
        "rsi_14":        rsi,
        "price_history": price_history,
        "fetched_at":    datetime.utcnow().isoformat(),
    }


async def get_macro_snapshot() -> dict:
    """
    Macro indicators — FRED is preferred (no rate limit issues).
    AV calls are sequential with delay to avoid 5/min limit.
    """
    results = {}

    # ── FRED (concurrent, no rate limit) ──
    fred_keys = {
        "US_10Y_YIELD": "GS10",
        "DXY":          "DTWEXBGS",
        "VIX_US":       "VIXCLS",
    }
    fred_vals = await asyncio.gather(*[_fred_latest(sid) for sid in fred_keys.values()])
    for key, val in zip(fred_keys.keys(), fred_vals):
        results[key] = {"value": val, "change_pct_1d": None}

    # ── AV Forex — sequential with delay ──
    await asyncio.sleep(AV_DELAY)
    try:
        fx = await _av_forex_daily("USD", "INR")
        if fx:
            dates  = sorted(fx.keys())
            latest = float(fx[dates[-1]]["4. close"])
            prev   = float(fx[dates[-2]]["4. close"]) if len(dates) >= 2 else None
            change = round((latest - prev) / prev * 100, 2) if prev else None
            results["USDINR"] = {"value": round(latest, 4), "change_pct_1d": change}
        else:
            results["USDINR"] = {"value": None}
    except Exception as e:
        results["USDINR"] = {"value": None, "error": str(e)}

    # ── Gold-Silver ratio — sequential with delay ──
    await asyncio.sleep(AV_DELAY)
    gold_rows = await _av_commodity("GOLD")
    await asyncio.sleep(AV_DELAY)
    silver_rows = await _av_commodity("SILVER")

    if gold_rows and silver_rows:
        try:
            gold_p   = float(gold_rows[-1]["value"])
            silver_p = float(silver_rows[-1]["value"])
            results["GOLD_SILVER_RATIO"] = {"value": round(gold_p / silver_p, 2)}
        except Exception:
            results["GOLD_SILVER_RATIO"] = {"value": None}
    else:
        results["GOLD_SILVER_RATIO"] = {"value": None}

    results["fetched_at"] = datetime.utcnow().isoformat()
    return results


async def get_fred_data() -> dict:
    """Full FRED macro data for India Macro module."""
    if not settings.fred_api_key:
        return {"error": "FRED_API_KEY not set in .env"}

    series = {
        "fed_funds_rate":     "FEDFUNDS",
        "cpi_yoy":            "CPIAUCSL",
        "core_pce":           "PCEPILFE",
        "unemployment":       "UNRATE",
        "us_10y_yield":       "GS10",
        "us_real_gdp_growth": "A191RL1Q225SBEA",
    }
    results = {}

    async with httpx.AsyncClient(timeout=10.0) as client:
        for name, sid in series.items():
            try:
                resp = await client.get(
                    "https://api.stlouisfed.org/fred/series/observations",
                    params={
                        "series_id":  sid,
                        "api_key":    settings.fred_api_key,
                        "file_type":  "json",
                        "sort_order": "desc",
                        "limit":      2,
                    },
                )
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
    """Latest news from NewsAPI."""
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
                },
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