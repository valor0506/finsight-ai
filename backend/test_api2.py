"""
test_api2.py — Run this to test the NEW Tier 1 + Tier 2 Architecture.

Usage:
    cd backend
    python test_api2.py

This tests Finnhub, nsepython, FRED, NewsAPI, Gemini, and the Supabase cache layer.
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# ── Check keys exist ───────────────────────────────────────────
print("\n" + "="*60)
print("  FinSight AI — V2 Architecture Diagnostic (Cache-First)")
print("="*60)

keys = {
    "FINNHUB_KEY":        os.getenv("FINNHUB_KEY", ""),
    "FRED_API_KEY":       os.getenv("FRED_API_KEY", ""),
    "NEWS_API_KEY":       os.getenv("NEWS_API_KEY", ""),
    "GEMINI_API_KEY":     os.getenv("GEMINI_API_KEY", ""),
    "SUPABASE_URL":       os.getenv("SUPABASE_URL", ""),
    "SUPABASE_KEY":       os.getenv("SUPABASE_KEY", ""), # Or SUPABASE_SERVICE_KEY
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


# ── Test Finnhub (US/Forex) ────────────────────────────────────
async def test_finnhub():
    import httpx
    key = os.getenv("FINNHUB_KEY", "")
    if not key:
        return "SKIP — key not set"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"https://finnhub.io/api/v1/quote?symbol=AAPL&token={key}")
            if r.status_code == 401:
                return "ERROR: Unauthorized (Invalid API Key)"
            data = r.json()
            if "c" in data and data["c"] != 0:
                return f"OK — AAPL latest: ${data['c']}"
            return f"EMPTY / ERROR — raw response: {data}"
    except Exception as e:
        return f"EXCEPTION: {e}"


# ── Test NSEPython (Indian Equities) ───────────────────────────
async def test_nsepython():
    try:
        from nsepython import nse_quote
        data = nse_quote("RELIANCE")
        if data and "lastPrice" in data:
            return f"OK — RELIANCE latest: ₹{data['lastPrice']}"
        return f"EMPTY — data returned without lastPrice key"
    except ImportError:
        return "ERROR: nsepython not installed (pip install nsepython)"
    except Exception as e:
        return f"EXCEPTION: {e}"


# ── Test FRED (Macro) ──────────────────────────────────────────
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
                params={"q": "Nifty 50", "apiKey": key, "pageSize": 1},
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


# ── Test Supabase (Cache Layer) ────────────────────────────────
async def test_supabase_cache():
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY", "") or os.getenv("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        return "SKIP — SUPABASE_URL or SUPABASE_KEY not set"
    try:
        from supabase import create_client
        sb = create_client(url, key)
        # Check if cached_data table exists by selecting 1 row
        result = sb.table("cached_data").select("key").limit(1).execute()
        return "OK — Connected. 'cached_data' table exists and is accessible."
    except Exception as e:
        err = str(e)
        if "relation" in err and "does not exist" in err:
            return "CONNECTED but 'cached_data' table missing — create it in Supabase SQL editor!"
        return f"EXCEPTION: {err[:120]}"


# ── Test Gemini ────────────────────────────────────────────────
async def test_gemini():
    key = os.getenv("GEMINI_API_KEY", "")
    if not key:
        return "SKIP — key not set"
    try:
        from google import genai
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model="gemini-2.5-flash", # Or whichever model version you are using
            contents="Say 'OK' and nothing else.",
        )
        return f"OK — Response: {response.text.strip()}"
    except Exception as e:
        return f"EXCEPTION: {e}"


# ── Full End-to-End Fetch (Tier 1 + 2) ─────────────────────────
async def test_full_tier_logic():
    """Calls the new data_fetcher to test end-to-end logic."""
    sys.path.insert(0, os.path.dirname(__file__))
    try:
        from agents.data_fetcher import get_equity_data, get_macro_snapshot
        
        print("\n  [A] Fetching Indian Equity (RELIANCE) via nsepython + Supabase...")
        eq_result = await get_equity_data("RELIANCE", is_indian=True)
        if eq_result and eq_result.get("current_price"):
             print(f"      ✓ Success: ₹{eq_result['current_price']} (Source: {eq_result['source']})")
        else:
             print(f"      ✗ Failed: {eq_result}")

        print("  [B] Fetching Global Macro Snapshot via FRED/NSE + Supabase...")
        macro_result = await get_macro_snapshot()
        if macro_result and macro_result.get("us_10y"):
             print(f"      ✓ Success: US 10Y Yield = {macro_result['us_10y']}%")
        else:
             print(f"      ✗ Failed: {macro_result}")

        return "OK — End-to-End tests executed."
    except ImportError as e:
         return f"ERROR: Could not import data_fetcher. Is it saved in agents/data_fetcher.py? ({e})"
    except Exception as e:
        return f"EXCEPTION: {e}"


async def main():
    print("\n[2] API & ARCHITECTURE CONNECTIVITY TESTS")

    print(f"  Finnhub (US/FX) →", end=" ", flush=True)
    print(await test_finnhub())

    print(f"  NSEPython       →", end=" ", flush=True)
    print(await test_nsepython())

    print(f"  FRED            →", end=" ", flush=True)
    print(await test_fred())

    print(f"  NewsAPI         →", end=" ", flush=True)
    print(await test_newsapi())

    print(f"  Gemini          →", end=" ", flush=True)
    print(await test_gemini())

    print(f"  Supabase Cache  →", end=" ", flush=True)
    print(await test_supabase_cache())

    print("\n[3] END-TO-END TIERED LOGIC (data_fetcher.py)")
    print(await test_full_tier_logic())

    print("\n" + "="*60)
    print("  Done. Fix any ✗ or ERROR above before deploying.")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())