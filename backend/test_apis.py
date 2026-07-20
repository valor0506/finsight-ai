"""
test_apis.py — Comprehensive Diagnostic Tool for FinSight AI Backend

Usage:
    cd backend
    python test_apis.py
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

print("\n" + "=" * 65)
print("  FinSight AI — Comprehensive System & Data Pipeline Diagnostic")
print("=" * 65)

KEYS = {
    "OPENROUTER_API_KEY":   os.getenv("OPENROUTER_API_KEY", ""),
    "FINNHUB_API_KEY":      os.getenv("FINNHUB_API_KEY", ""),
    "GROWW_API_KEY":        os.getenv("GROWW_API_KEY", ""),
    "GROWW_TOTP_SECRET":    os.getenv("GROWW_TOTP_SECRET", ""),
    "FRED_API_KEY":         os.getenv("FRED_API_KEY", ""),
    "NEWS_API_KEY":         os.getenv("NEWS_API_KEY", ""),
    "SUPABASE_URL":         os.getenv("SUPABASE_URL", ""),
    "SUPABASE_SERVICE_KEY": os.getenv("SUPABASE_SERVICE_KEY", ""),
    "DATABASE_URL":         os.getenv("DATABASE_URL", ""),
    "REDIS_URL":            os.getenv("REDIS_URL", ""),
}

print("\n[1] ENVIRONMENT KEYS CHECK")
all_present = True
for k, v in KEYS.items():
    if v:
        print(f"  ✓ {k:<22} : {v[:10]}...")
    else:
        print(f"  ✗ {k:<22} : NOT SET")
        all_present = False

if not all_present:
    print("\n⚠ Some env vars are missing. Check backend/.env before deploying.")


async def test_finnhub():
    import httpx
    key = KEYS["FINNHUB_API_KEY"]
    if not key:
        return "SKIP — FINNHUB_API_KEY not set"
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r1 = await c.get("https://finnhub.io/api/v1/quote", params={"symbol": "OANDA:USD_INR", "token": key})
            usd_inr = r1.json().get("c")
            r2 = await c.get("https://finnhub.io/api/v1/quote", params={"symbol": "FOREXCOM:XAUUSD", "token": key})
            gold = r2.json().get("c")
        return f"OK — USD/INR={usd_inr}, Gold=${gold}"
    except Exception as e:
        return f"FAIL — {e}"


async def test_fred():
    import httpx
    key = KEYS["FRED_API_KEY"]
    if not key:
        return "SKIP — FRED_API_KEY not set"
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(
                "https://api.stlouisfed.org/fred/series/observations",
                params={"series_id": "GS10", "api_key": key, "file_type": "json", "sort_order": "desc", "limit": 1},
            )
            obs = r.json().get("observations", [])
            return f"OK — US 10Y Yield: {obs[0]['value']}% on {obs[0]['date']}" if obs else "EMPTY"
    except Exception as e:
        return f"FAIL — {e}"


async def test_newsapi():
    import httpx
    key = KEYS["NEWS_API_KEY"]
    if not key:
        return "SKIP — NEWS_API_KEY not set"
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(
                "https://newsapi.org/v2/everything",
                params={"q": "Nifty 50 India", "apiKey": key, "pageSize": 1},
            )
            d = r.json()
            arts = d.get("articles", [])
            return f"OK — '{arts[0]['title'][:50]}...'" if arts else f"Status: {d.get('status')}"
    except Exception as e:
        return f"FAIL — {e}"


async def test_openrouter():
    key = KEYS["OPENROUTER_API_KEY"]
    if not key:
        return "SKIP — OPENROUTER_API_KEY not set"
    try:
        from openai import OpenAI
        c = OpenAI(api_key=key, base_url="https://openrouter.ai/api/v1")
        res = c.chat.completions.create(
            model="meta-llama/llama-3.3-70b-instruct:free",
            messages=[{"role": "user", "content": "Reply with OK."}],
            max_tokens=10,
        )
        return f"OK — Response: {res.choices[0].message.content.strip()}"
    except Exception as e:
        return f"FAIL — {e}"


async def test_groww():
    key = KEYS["GROWW_API_KEY"]
    totp_sec = KEYS["GROWW_TOTP_SECRET"]
    if not key or not totp_sec:
        return "SKIP — GROWW_API_KEY or GROWW_TOTP_SECRET not set"
    try:
        import pyotp
        from growwapi import GrowwAPI
        totp = pyotp.TOTP(totp_sec).now()
        access_token = GrowwAPI.get_access_token(api_key=key, totp=totp)
        g = GrowwAPI(access_token)
        q = g.get_quote(trading_symbol="RELIANCE", exchange="NSE", segment="CASH")
        return f"OK — RELIANCE price: ₹{q.get('last_price')}" if q else "EMPTY"
    except Exception as e:
        return f"FAIL — {e}"


async def test_nse():
    try:
        from nsepython import nse_get_index_quote
        d = nse_get_index_quote("NIFTY 50")
        return f"OK — Nifty50={d.get('last')}" if d else "EMPTY"
    except Exception as e:
        return f"FAIL — {e}"


async def test_supabase():
    url = KEYS["SUPABASE_URL"]
    key = KEYS["SUPABASE_SERVICE_KEY"]
    if not url or not key:
        return "SKIP — SUPABASE_URL or SUPABASE_SERVICE_KEY not set"
    try:
        from supabase import create_client
        sb = create_client(url, key)
        res = sb.table("users").select("id").limit(1).execute()
        return "OK — Connected to Supabase ('users' table accessible)"
    except Exception as e:
        err = str(e)
        if "does not exist" in err:
            return "CONNECTED — Database tables missing. Run: alembic upgrade head"
        return f"FAIL — {err[:120]}"


async def test_pipeline():
    sys.path.insert(0, os.path.dirname(__file__))
    try:
        from agents.data_fetcher import get_commodity_data
        print("\n  Executing get_commodity_data('GOLD')...", flush=True)
        r = await get_commodity_data("GOLD")
        if r.get("error"):
            return f"ERROR — {r['error']}"
        return f"OK — Price: ${r.get('current_price')} | RSI: {r.get('rsi_14')} | Source: {r.get('data_source')}"
    except Exception as e:
        return f"FAIL — {e}"


async def main():
    print("\n[2] API & SERVICE CONNECTIVITY TESTS")
    for name, fn in [
        ("Finnhub",   test_finnhub),
        ("FRED",      test_fred),
        ("NewsAPI",   test_newsapi),
        ("OpenRouter", test_openrouter),
        ("Groww TOTP", test_groww),
        ("nsepython", test_nse),
        ("Supabase",  test_supabase),
    ]:
        print(f"  {name:<14} → ", end="", flush=True)
        print(await fn())

    print("\n[3] END-TO-END DATA PIPELINE TEST")
    print("  Pipeline test → ", await test_pipeline())

    print("\n" + "=" * 65)
    print("  Diagnostic complete. Review any FAIL/SKIP items above.")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    asyncio.run(main())