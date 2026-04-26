import asyncio
import httpx
from datetime import datetime, timedelta
from typing import Optional, Any, Dict, List
from core.config import get_settings
from supabase import create_client, Client

# Note: You'll need to install nsepython and supabase python client
from nsepython import nse_quote, nse_fii_dii

settings = get_settings()

# Initialize Supabase Client (Tier 2)
supabase: Client = create_client(settings.supabase_url, settings.supabase_key)

# ── TTL Configuration (Tier 2) ──────────────────────────────────
TTL_CONFIG = {
    "commodity": 6,   # hours
    "equity": 1,      # hour
    "macro": 24,      # hours
    "news": 0.5       # 30 mins (0.5 hours)
}

# ── Tier 2: Cache Layer Logic ───────────────────────────────────

async def get_cached_data(key: str, category: str) -> Optional[Dict]:
    """Check Supabase for valid cached data based on TTL."""
    try:
        response = supabase.table("cached_data").select("*").eq("key", key).single().execute()
        if not response.data:
            return None
        
        cached_at = datetime.fromisoformat(response.data["updated_at"])
        ttl_hours = TTL_CONFIG.get(category, 1)
        
        if datetime.utcnow() > cached_at + timedelta(hours=ttl_hours):
            return None # Cache expired
            
        return response.data["payload"]
    except Exception:
        return None

async def set_cache_data(key: str, payload: Any):
    """Upsert data into Supabase cache."""
    try:
        supabase.table("cached_data").upsert({
            "key": key,
            "payload": payload,
            "updated_at": datetime.utcnow().isoformat()
        }).execute()
    except Exception as e:
        print(f"Cache write error: {e}")

# ── Tier 1: Live APIs (Source of Truth) ─────────────────────────

async def fetch_groww_price(symbol: str) -> Dict:
    """Mock implementation for Groww API (NSE/BSE)."""
    # In a real scenario, use Groww's internal endpoint or a wrapper
    # For now, we simulate the fetch for Indian Equities
    return {"price": 2500.50, "exchange": "NSE", "ohlc": {}}

async def fetch_finnhub_price(ticker: str) -> Dict:
    """Fetch US Stocks/Forex from Finnhub."""
    url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={settings.finnhub_key}"
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        data = r.json()
        return {
            "current_price": data.get("c"),
            "change": data.get("d"),
            "pc": data.get("pc")
        }

async def fetch_fred_metric(series_id: str) -> Optional[float]:
    """Fetch macro indicators from FRED."""
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": settings.fred_api_key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 1
    }
    async with httpx.AsyncClient() as client:
        r = await client.get(url, params=params)
        obs = r.json().get("observations", [])
        return float(obs[0]["value"]) if obs and obs[0]["value"] != "." else None

# ── Public Interface (The Logic Flow) ──────────────────────────

async def get_equity_data(ticker: str, is_indian: bool = True) -> Dict:
    """Tier 2 -> Tier 1 Logic for Stocks."""
    cache = await get_cached_data(ticker, "equity")
    if cache: return cache

    # Tier 1 Fetch
    if is_indian:
        # Using nsepython for Indian Data
        data = nse_quote(ticker)
        result = {
            "ticker": ticker,
            "current_price": data.get("lastPrice"),
            "source": "NSE",
            "fetched_at": datetime.utcnow().isoformat()
        }
    else:
        data = await fetch_finnhub_price(ticker)
        result = {
            "ticker": ticker,
            "current_price": data["current_price"],
            "source": "Finnhub",
            "fetched_at": datetime.utcnow().isoformat()
        }

    await set_cache_data(ticker, result)
    return result

async def get_macro_snapshot() -> Dict:
    """Tier 1 + 2 for Global & Indian Macro."""
    cache = await get_cached_data("macro_snapshot", "macro")
    if cache: return cache

    # Parallel Tier 1 calls
    fred_ids = {"US_10Y": "GS10", "DXY": "DTWEXBGS", "VIX": "VIXCLS"}
    
    tasks = [fetch_fred_metric(sid) for sid in fred_ids.values()]
    fred_results = await asyncio.gather(*tasks)
    
    # nsepython for Indian Flows
    fii_dii = nse_fii_dii()

    snapshot = {
        "us_10y": fred_results[0],
        "dxy": fred_results[1],
        "vix": fred_results[2],
        "fii_dii_flow": fii_dii,
        "fetched_at": datetime.utcnow().isoformat()
    }

    await set_cache_data("macro_snapshot", snapshot)
    return snapshot

async def get_news_data(query: str) -> List[Dict]:
    """Tier 2 -> Tier 1 Logic for News."""
    cache_key = f"news_{query.replace(' ', '_')}"
    cache = await get_cached_data(cache_key, "news")
    if cache: return cache

    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "apiKey": settings.news_api_key,
        "pageSize": 5,
        "language": "en"
    }
    
    async with httpx.AsyncClient() as client:
        r = await client.get(url, params=params)
        articles = r.json().get("articles", [])
        
    result = [{
        "title": a["title"],
        "url": a["url"],
        "source": a["source"]["name"]
    } for a in articles]

    await set_cache_data(cache_key, result)
    return result