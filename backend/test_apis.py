"""
test_apis.py — Run this FIRST before anything else.

Usage:
    cd backend
    python test_apis.py

This tests every API key and data fetch independently.
If something returns None, this will tell you exactly why.
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# ── Check keys exist ───────────────────────────────────────────
print("\n" + "="*55)
print("  FinSight AI — API Key & Data Diagnostic")
print("="*55)

keys = {
    "ALPHA_VANTAGE_KEY":  os.getenv("ALPHA_VANTAGE_KEY", ""),
    "FRED_API_KEY":       os.getenv("FRED_API_KEY", ""),
    "NEWS_API_KEY":       os.getenv("NEWS_API_KEY", ""),
    "GEMINI_API_KEY":     os.getenv("GEMINI_API_KEY", ""),
    "SUPABASE_URL":       os.getenv("SUPABASE_URL", ""),
    "REDIS_URL":          os.getenv("REDIS_URL", ""),
}

print("\n[1] ENV KEYS")
all_ok = True
for k, v in keys.items():
    if v:
        print(f"  ✓ {k}: {v[:8]}...")
    else:
        print(f"  ✗ {k}: NOT SET")
        all_ok = False

if not all_ok:
    print("\n⚠ Fix missing keys in .env before continuing.\n")


# ── Test Alpha Vantage ─────────────────────────────────────────
async def test_alpha_vantage():
    import httpx
    key = os.getenv("ALPHA_VANTAGE_KEY", "")
    if not key:
        return "SKIP — key not set"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                "https://www.alphavantage.co/query",
                params={"function": "SILVER", "interval": "monthly", "apikey": key},
            )
            data = r.json()
            if "Note" in data:
                return f"RATE LIMITED: {data['Note'][:80]}"
            if "Information" in data:
                return f"ERROR: {data['Information'][:80]}"
            rows = data.get("data", [])
            if rows:
                latest = rows[0]
                return f"OK — Silver latest: {latest['date']} = ${latest['value']}"
            return f"EMPTY — raw keys: {list(data.keys())}"
    except Exception as e:
        return f"EXCEPTION: {e}"


# ── Test FRED ──────────────────────────────────────────────────
async def test_fred():
    import httpx
    key = os.getenv("FRED_API_KEY", "")
    if not key:
        return "SKIP — key not set"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                "https://api.stlouisfed.org/fred/series/observations",
                params={
                    "series_id":  "GS10",
                    "api_key":    key,
                    "file_type":  "json",
                    "sort_order": "desc",
                    "limit":      1,
                },
            )
            obs = r.json().get("observations", [])
            if obs:
                return f"OK — US 10Y Yield: {obs[0]['value']}% on {obs[0]['date']}"
            return f"EMPTY — raw: {r.text[:100]}"
    except Exception as e:
        return f"EXCEPTION: {e}"


# ── Test NewsAPI ───────────────────────────────────────────────
async def test_newsapi():
    import httpx
    key = os.getenv("NEWS_API_KEY", "")
    if not key:
        return "SKIP — key not set"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                "https://newsapi.org/v2/everything",
                params={"q": "gold silver commodities", "apiKey": key, "pageSize": 1},
            )
            data = r.json()
            if data.get("status") == "ok":
                articles = data.get("articles", [])
                if articles:
                    return f"OK — '{articles[0]['title'][:60]}...'"
                return "OK — but 0 articles returned"
            return f"ERROR: {data.get('message', data)}"
    except Exception as e:
        return f"EXCEPTION: {e}"


# ── Test Gemini ────────────────────────────────────────────────
async def test_gemini():
    key = os.getenv("GEMINI_API_KEY", "")
    if not key:
        return "SKIP — key not set"
    try:
        from google import genai
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents="Say 'OK' and nothing else.",
        )
        return f"OK — Response: {response.text.strip()}"
    except Exception as e:
        return f"EXCEPTION: {e}"


# ── Test Supabase ──────────────────────────────────────────────
async def test_supabase():
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        return "SKIP — SUPABASE_URL or SUPABASE_SERVICE_KEY not set"
    try:
        from supabase import create_client
        sb = create_client(url, key)
        # Try a simple query — will fail if tables don't exist yet (that's okay)
        result = sb.table("users").select("id").limit(1).execute()
        return f"OK — Connected. Users table exists."
    except Exception as e:
        err = str(e)
        if "relation" in err and "does not exist" in err:
            return "CONNECTED but tables not created yet — run migrations first"
        return f"EXCEPTION: {err[:120]}"


# ── Full commodity fetch ───────────────────────────────────────
async def test_full_commodity_fetch():
    """Actually calls your data_fetcher to test end-to-end."""
    sys.path.insert(0, os.path.dirname(__file__))
    try:
        from agents.data_fetcher import get_commodity_data
        print("\n  Fetching SILVER data (this may take 15s due to AV rate limits)...")
        result = await get_commodity_data("SILVER")
        if result.get("error"):
            return f"ERROR: {result['error']}"
        return (
            f"OK — Price: ${result['current_price']} | "
            f"RSI: {result['rsi_14']} | "
            f"SMA20: {result['sma_20']}"
        )
    except Exception as e:
        return f"EXCEPTION: {e}"


async def main():
    print("\n[2] API CONNECTIVITY TESTS")

    print(f"  Alpha Vantage  →", end=" ", flush=True)
    print(await test_alpha_vantage())

    print(f"  FRED           →", end=" ", flush=True)
    print(await test_fred())

    print(f"  NewsAPI        →", end=" ", flush=True)
    print(await test_newsapi())

    print(f"  Gemini         →", end=" ", flush=True)
    print(await test_gemini())

    print(f"  Supabase       →", end=" ", flush=True)
    print(await test_supabase())

    print("\n[3] END-TO-END DATA FETCH (data_fetcher.py)")
    print(f"  get_commodity_data('SILVER') →", end=" ", flush=True)
    print(await test_full_commodity_fetch())

    print("\n" + "="*55)
    print("  Done. Fix any ✗ or ERROR above before deploying.")
    print("="*55 + "\n")


if __name__ == "__main__":
    asyncio.run(main())