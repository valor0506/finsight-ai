import httpx
from datetime import datetime
from typing import Optional
from core.config import get_settings
import asyncio

settings = get_settings()

AV_BASE = "https://www.alphavantage.co/query"

# Alpha Vantage commodity function map
COMMODITY_AV = {
    "SILVER":      "SILVER",
    "GOLD":        "GOLD",
    "CRUDE_BRENT": "BRENT",
    "CRUDE_WTI":   "WTI",
    "NATURAL_GAS": "NATURAL_GAS",
    "COPPER":      "COPPER",
    "ALUMINIUM":   "ALUMINUM",
}

# Alpha Vantage forex pairs for macro
MACRO_FOREX = {
    "USDINR": ("USD", "INR"),
}

# These come from FRED — more reliable than AV for macro
FRED_MACRO = {
    "US_10Y_YIELD": "GS10",
    "DXY":          "DTWEXBGS",
    "VIX_US":       "VIXCLS",
}


def _calculate_rsi(closes: list, period: int = 14) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    deltas   = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains    = [d if d > 0 else 0 for d in deltas]
    losses   = [abs(d) if d < 0 else 0 for d in deltas]
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    return round(100 - (100 / (1 + avg_gain / avg_loss)), 2)


async def _av_commodity(function: str) -> list:
    """
    Fetch monthly commodity data from Alpha Vantage.
    Returns list of {date, value} dicts sorted oldest to newest.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(AV_BASE, params={
                "function": function,
                "interval": "monthly",
                "apikey":   settings.alpha_vantage_key,
            })
            data = r.json()
            rows = data.get("data", [])
            # AV returns newest first — reverse
            return list(reversed(rows))
    except Exception:
        return []


async def _av_quote(symbol: str) -> dict:
    """Get current quote for a stock/ETF symbol."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(AV_BASE, params={
                "function": "GLOBAL_QUOTE",
                "symbol":   symbol,
                "apikey":   settings.alpha_vantage_key,
            })
            return r.json().get("Global Quote", {})
    except Exception:
        return {}


async def _av_daily(symbol: str, outputsize: str = "compact") -> dict:
    """
    Get daily OHLCV for a stock symbol.
    outputsize: "compact" = last 100 days, "full" = 20 years
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(AV_BASE, params={
                "function":   "TIME_SERIES_DAILY",
                "symbol":     symbol,
                "outputsize": outputsize,
                "apikey":     settings.alpha_vantage_key,
            })
            return r.json().get("Time Series (Daily)", {})
    except Exception:
        return {}


async def _av_forex_daily(from_sym: str, to_sym: str) -> dict:
    """Get daily forex rate history."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(AV_BASE, params={
                "function":    "FX_DAILY",
                "from_symbol": from_sym,
                "to_symbol":   to_sym,
                "outputsize":  "compact",
                "apikey":      settings.alpha_vantage_key,
            })
            return r.json().get("Time Series FX (Daily)", {})
    except Exception:
        return {}


async def _fred_latest(series_id: str) -> Optional[float]:
    """Get latest value for a FRED series."""
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
                }
            )
            obs = r.json().get("observations", [])
            if obs and obs[0]["value"] != ".":
                return float(obs[0]["value"])
    except Exception:
        pass
    return None


async def get_commodity_data(symbol: str) -> dict:
    """
    Fetches commodity data via Alpha Vantage commodity endpoint.
    Returns price, 52W high/low, RSI-14, SMA-20, SMA-50, price history.
    """
    av_function = COMMODITY_AV.get(symbol.upper())
    if not av_function:
        return {"error": f"Unknown symbol: {symbol}. Valid: {list(COMMODITY_AV.keys())}"}

    try:
        rows = await _av_commodity(av_function)

        if not rows:
            return {"error": f"No data from Alpha Vantage for {symbol}", "symbol": symbol}

        # Extract close prices from monthly data
        closes = []
        price_history = []
        for row in rows[-60:]:  # last 60 months max
            try:
                val = float(row["value"])
                closes.append(val)
                price_history.append({
                    "date":  row["date"],
                    "close": round(val, 4),
                })
            except Exception:
                continue

        if not closes:
            return {"error": "Empty price data", "symbol": symbol}

        current_price = closes[-1]
        week_52_high  = round(max(closes[-12:]), 4)   # last 12 months
        week_52_low   = round(min(closes[-12:]), 4)
        pct_from_high = round((current_price - week_52_high) / week_52_high * 100, 2) if week_52_high else 0

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
            "volume":            None,  # AV commodity doesn't provide volume
            "sma_20":            sma_20,
            "sma_50":            sma_50,
            "rsi_14":            rsi,
            "price_history":     price_history[-60:],
            "fetched_at":        datetime.utcnow().isoformat(),
        }

    except Exception as e:
        return {"error": str(e), "symbol": symbol}


async def get_equity_data(ticker: str) -> dict:
    """
    Fetches equity data via Alpha Vantage.
    Use NSE stocks as US-listed ADRs or just use ticker directly.
    For Indian stocks: try BSE/NSE listed tickers like 'RELIANCE.BSE'
    """
    try:
        quote_task = _av_quote(ticker)
        daily_task = _av_daily(ticker, outputsize="full")

        quote, daily = await asyncio.gather(quote_task, daily_task)

        if not daily:
            return {"error": f"No data for {ticker}", "ticker": ticker}

        # Sort dates oldest to newest
        sorted_dates = sorted(daily.keys())
        closes = [float(daily[d]["4. close"]) for d in sorted_dates]

        price_history = []
        for d in sorted_dates[-60:]:
            try:
                price_history.append({
                    "date":   d,
                    "close":  round(float(daily[d]["4. close"]), 2),
                    "volume": int(float(daily[d]["5. volume"])),
                })
            except Exception:
                continue

        current_price = float(quote.get("05. price", closes[-1] if closes else 0))
        hi52  = round(max([float(daily[d]["2. high"]) for d in sorted_dates[-252:]]), 2) if len(sorted_dates) >= 5 else None
        lo52  = round(min([float(daily[d]["3. low"])  for d in sorted_dates[-252:]]), 2) if len(sorted_dates) >= 5 else None

        sma_50  = round(sum(closes[-50:])  / min(50, len(closes)),  2) if len(closes) >= 5 else None
        sma_200 = round(sum(closes[-200:]) / min(200, len(closes)), 2) if len(closes) >= 5 else None
        rsi     = _calculate_rsi(closes)

        return {
            "ticker":                 ticker,
            "company_name":           ticker,
            "sector":                 None,
            "industry":               None,
            "market_cap":             None,
            "current_price":          round(current_price, 2),
            "currency":               "USD",
            "pe_ratio":               None,
            "forward_pe":             None,
            "pb_ratio":               None,
            "ev_ebitda":              None,
            "revenue":                None,
            "revenue_growth":         None,
            "gross_margin":           None,
            "operating_margin":       None,
            "profit_margin":          None,
            "roe":                    None,
            "roa":                    None,
            "debt_to_equity":         None,
            "current_ratio":          None,
            "free_cashflow":          None,
            "dividend_yield":         None,
            "week_52_high":           hi52,
            "week_52_low":            lo52,
            "beta":                   None,
            "analyst_target_price":   None,
            "analyst_recommendation": None,
            "analyst_count":          None,
            "sma_50":                 sma_50,
            "sma_200":                sma_200,
            "rsi_14":                 rsi,
            "price_history":          price_history,
            "fetched_at":             datetime.utcnow().isoformat(),
        }

    except Exception as e:
        return {"error": str(e), "ticker": ticker}


async def get_macro_snapshot() -> dict:
    """
    Macro indicators:
    - USD/INR via Alpha Vantage FX
    - US 10Y yield, DXY, VIX via FRED
    - Gold-Silver ratio derived from commodity data
    """
    results = {}

    # Forex via AV
    try:
        fx_data = await _av_forex_daily("USD", "INR")
        if fx_data:
            latest_date = sorted(fx_data.keys())[-1]
            prev_date   = sorted(fx_data.keys())[-2] if len(fx_data) >= 2 else None
            latest = float(fx_data[latest_date]["4. close"])
            prev   = float(fx_data[prev_date]["4. close"]) if prev_date else None
            change = round((latest - prev) / prev * 100, 2) if prev else None
            results["USDINR"] = {"value": round(latest, 4), "change_pct_1d": change}
    except Exception as e:
        results["USDINR"] = {"error": str(e)}

    # Macro from FRED concurrently
    fred_tasks = {
        "US_10Y_YIELD": _fred_latest("GS10"),
        "DXY":          _fred_latest("DTWEXBGS"),
        "VIX_US":       _fred_latest("VIXCLS"),
    }

    fred_results = await asyncio.gather(*fred_tasks.values())
    for key, val in zip(fred_tasks.keys(), fred_results):
        results[key] = {"value": val, "change_pct_1d": None}

    # Nifty — AV supports Indian indices via BSE
    try:
        nifty_quote = await _av_quote("^NSEI")
        if nifty_quote:
            results["NIFTY50"] = {
                "value": float(nifty_quote.get("05. price", 0)) or None,
                "change_pct_1d": None,
            }
    except Exception:
        results["NIFTY50"] = {"value": None}

    # Gold-Silver ratio
    try:
        gold_task   = _av_commodity("GOLD")
        silver_task = _av_commodity("SILVER")
        gold_rows, silver_rows = await asyncio.gather(gold_task, silver_task)

        if gold_rows and silver_rows:
            gold_p   = float(gold_rows[-1]["value"])
            silver_p = float(silver_rows[-1]["value"])
            results["GOLD_SILVER_RATIO"] = {
                "value": round(gold_p / silver_p, 2)
            }
    except Exception:
        pass

    results["fetched_at"] = datetime.utcnow().isoformat()
    return results


async def get_fred_data() -> dict:
    """Full FRED macro data — Fed rate, CPI, PCE, unemployment, GDP."""
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
    """Latest news from NewsAPI for a given query."""
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