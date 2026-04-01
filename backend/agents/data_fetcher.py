import yfinance as yf
import httpx
from datetime import datetime
from typing import Optional
from core.config import get_settings

settings = get_settings()

COMMODITY_TICKERS = {
    "SILVER":       "SI=F",
    "GOLD":         "GC=F",
    "CRUDE_BRENT":  "BZ=F",
    "CRUDE_WTI":    "CL=F",
    "NATURAL_GAS":  "NG=F",
    "COPPER":       "HG=F",
    "ALUMINIUM":    "ALI=F",
}

MACRO_TICKERS = {
    "US_10Y_YIELD": "^TNX",
    "DXY":          "DX-Y.NYB",
    "NIFTY50":      "^NSEI",
    "USDINR":       "INR=X",
    "VIX_US":       "^VIX",
    "VIX_INDIA":    "^NSEVIN",
}


async def get_commodity_data(symbol: str) -> dict:
    ticker_str = COMMODITY_TICKERS.get(symbol.upper())
    if not ticker_str:
        return {"error": f"Unknown symbol: {symbol}"}

    try:
        ticker = yf.Ticker(ticker_str)
        info = ticker.info
        hist = ticker.history(period="3mo", interval="1d")

        current_price = info.get("regularMarketPrice") or info.get("previousClose", 0)
        week_52_high = info.get("fiftyTwoWeekHigh", 0)
        week_52_low = info.get("fiftyTwoWeekLow", 0)
        pct_from_high = (
            (current_price - week_52_high) / week_52_high * 100
        ) if week_52_high else 0

        price_history = []
        if not hist.empty:
            for date, row in hist.tail(60).iterrows():
                price_history.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "open": round(row["Open"], 2),
                    "high": round(row["High"], 2),
                    "low":  round(row["Low"], 2),
                    "close": round(row["Close"], 2),
                    "volume": int(row["Volume"]),
                })

        closes = [d["close"] for d in price_history]
        sma_20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else None
        sma_50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else None
        rsi    = _calculate_rsi(closes) if len(closes) >= 15 else None

        return {
            "symbol": symbol,
            "ticker": ticker_str,
            "current_price": current_price,
            "currency": info.get("currency", "USD"),
            "week_52_high": week_52_high,
            "week_52_low": week_52_low,
            "pct_from_52w_high": round(pct_from_high, 2),
            "volume": info.get("regularMarketVolume"),
            "sma_20": round(sma_20, 2) if sma_20 else None,
            "sma_50": round(sma_50, 2) if sma_50 else None,
            "rsi_14": round(rsi, 2) if rsi else None,
            "price_history": price_history,
            "fetched_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {"error": str(e), "symbol": symbol}


async def get_equity_data(ticker: str) -> dict:
    try:
        stock = yf.Ticker(ticker)
        info  = stock.info
        hist  = stock.history(period="1y", interval="1d")

        closes = hist["Close"].tolist() if not hist.empty else []
        price_history = []
        if not hist.empty:
            for date, row in hist.tail(60).iterrows():
                price_history.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "close": round(row["Close"], 2),
                    "volume": int(row["Volume"]),
                })

        sma_50  = sum(closes[-50:])  / 50  if len(closes) >= 50  else None
        sma_200 = sum(closes[-200:]) / 200 if len(closes) >= 200 else None
        rsi     = _calculate_rsi(closes) if len(closes) >= 15 else None

        return {
            "ticker": ticker,
            "company_name": info.get("longName", ticker),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "market_cap": info.get("marketCap"),
            "current_price": info.get("currentPrice") or info.get("previousClose"),
            "currency": info.get("currency", "INR"),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "pb_ratio": info.get("priceToBook"),
            "ev_ebitda": info.get("enterpriseToEbitda"),
            "revenue": info.get("totalRevenue"),
            "revenue_growth": info.get("revenueGrowth"),
            "gross_margin": info.get("grossMargins"),
            "operating_margin": info.get("operatingMargins"),
            "profit_margin": info.get("profitMargins"),
            "roe": info.get("returnOnEquity"),
            "roa": info.get("returnOnAssets"),
            "debt_to_equity": info.get("debtToEquity"),
            "current_ratio": info.get("currentRatio"),
            "free_cashflow": info.get("freeCashflow"),
            "dividend_yield": info.get("dividendYield"),
            "week_52_high": info.get("fiftyTwoWeekHigh"),
            "week_52_low": info.get("fiftyTwoWeekLow"),
            "beta": info.get("beta"),
            "analyst_target_price": info.get("targetMeanPrice"),
            "analyst_recommendation": info.get("recommendationKey"),
            "analyst_count": info.get("numberOfAnalystOpinions"),
            "sma_50": round(sma_50, 2) if sma_50 else None,
            "sma_200": round(sma_200, 2) if sma_200 else None,
            "rsi_14": round(rsi, 2) if rsi else None,
            "price_history": price_history,
            "fetched_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {"error": str(e), "ticker": ticker}


async def get_macro_snapshot() -> dict:
    results = {}
    for name, ticker_str in MACRO_TICKERS.items():
        try:
            ticker = yf.Ticker(ticker_str)
            hist   = ticker.history(period="5d", interval="1d")
            latest = hist["Close"].iloc[-1] if not hist.empty else None
            prev   = hist["Close"].iloc[-2] if len(hist) >= 2 else None
            change = ((latest - prev) / prev * 100) if (latest and prev) else None
            results[name] = {
                "value": round(latest, 4) if latest else None,
                "change_pct_1d": round(change, 2) if change else None,
            }
        except Exception as e:
            results[name] = {"error": str(e)}

    # Gold-Silver Ratio
    try:
        gold   = await get_commodity_data("GOLD")
        silver = await get_commodity_data("SILVER")
        if gold.get("current_price") and silver.get("current_price"):
            results["GOLD_SILVER_RATIO"] = {
                "value": round(gold["current_price"] / silver["current_price"], 2)
            }
    except Exception:
        pass

    results["fetched_at"] = datetime.utcnow().isoformat()
    return results


async def get_fred_data() -> dict:
    if not settings.fred_api_key:
        return {"error": "FRED API key not configured"}

    fred_series = {
        "fed_funds_rate":    "FEDFUNDS",
        "cpi_yoy":           "CPIAUCSL",
        "core_pce":          "PCEPILFE",
        "unemployment":      "UNRATE",
        "us_10y_yield":      "GS10",
        "us_real_gdp_growth":"A191RL1Q225SBEA",
    }

    base_url = "https://api.stlouisfed.org/fred/series/observations"
    results = {}

    async with httpx.AsyncClient(timeout=10.0) as client:
        for name, series_id in fred_series.items():
            try:
                resp = await client.get(base_url, params={
                    "series_id": series_id,
                    "api_key":   settings.fred_api_key,
                    "file_type": "json",
                    "sort_order":"desc",
                    "limit":     2,
                })
                obs = resp.json().get("observations", [])
                if obs:
                    val  = float(obs[0]["value"]) if obs[0]["value"] != "." else None
                    prev = float(obs[1]["value"]) if len(obs) > 1 and obs[1]["value"] != "." else None
                    results[name] = {
                        "value": val,
                        "date": obs[0]["date"],
                        "prev_value": prev,
                        "change": round(val - prev, 3) if (val and prev) else None,
                    }
            except Exception as e:
                results[name] = {"error": str(e)}

    results["fetched_at"] = datetime.utcnow().isoformat()
    return results


def _calculate_rsi(closes: list, period: int = 14) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains  = [d if d > 0 else 0 for d in deltas]
    losses = [abs(d) if d < 0 else 0 for d in deltas]
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    return 100 - (100 / (1 + avg_gain / avg_loss))