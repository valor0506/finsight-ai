"""
test_apis.py — Run this before deploying.
Usage: cd backend && python test_apis.py
"""
import asyncio, os, sys
from dotenv import load_dotenv
load_dotenv()

print("\n" + "="*55)
print("  FinSight AI — API Diagnostic v2")
print("="*55)

KEYS = {
    "GEMINI_API_KEY":       os.getenv("GEMINI_API_KEY",""),
    "FINNHUB_API_KEY":      os.getenv("FINNHUB_API_KEY",""),
    "GROWW_API_KEY":        os.getenv("GROWW_API_KEY",""),
    "GROWW_API_SECRET":     os.getenv("GROWW_API_SECRET",""),
    "FRED_API_KEY":         os.getenv("FRED_API_KEY",""),
    "NEWS_API_KEY":         os.getenv("NEWS_API_KEY",""),
    "SUPABASE_URL":         os.getenv("SUPABASE_URL",""),
    "SUPABASE_SERVICE_KEY": os.getenv("SUPABASE_SERVICE_KEY",""),
    "DATABASE_URL":         os.getenv("DATABASE_URL",""),
    "REDIS_URL":            os.getenv("REDIS_URL",""),
}

print("\n[1] ENV KEYS")
for k,v in KEYS.items():
    print(f"  {'OK' if v else 'MISSING'} {k}: {v[:10]+'...' if v else 'NOT SET'}")

async def test_finnhub():
    import httpx
    key = os.getenv("FINNHUB_API_KEY","")
    if not key: return "SKIP"
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            # Forex rates
            r1 = await c.get("https://finnhub.io/api/v1/forex/rates",
                             params={"base": "USD", "token": key})
            quote = r1.json().get("quote", {})
            inr   = quote.get("INR")
            # Show first 5 available keys if INR missing
            available = list(quote.keys())[:5] if not inr else []

            # Commodity quote
            r2 = await c.get("https://finnhub.io/api/v1/quote",
                             params={"symbol": "FOREXCOM:XAUUSD", "token": key})
            gold = r2.json().get("c")

            # Candles test
            import time
            r3 = await c.get("https://finnhub.io/api/v1/stock/candle", params={
                "symbol": "FOREXCOM:XAUUSD", "resolution": "D",
                "from": int(time.time()) - 86400*7,
                "to":   int(time.time()),
                "token": key,
            })
            candle_status = r3.json().get("s")

        msg = f"USD/INR={inr}  Gold=${gold}  candles={candle_status}"
        if available:
            msg += f"  (INR missing, sample keys: {available})"
        return f"OK  {msg}"
    except Exception as e:
        return f"FAIL {e}"

async def test_fred():
    import httpx
    key = os.getenv("FRED_API_KEY","")
    if not key: return "SKIP"
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get("https://api.stlouisfed.org/fred/series/observations",
                params={"series_id":"GS10","api_key":key,"file_type":"json","sort_order":"desc","limit":1})
            obs = r.json().get("observations",[])
            return f"OK  10Y={obs[0]['value']}% ({obs[0]['date']})" if obs else "EMPTY"
    except Exception as e: return f"FAIL {e}"

async def test_newsapi():
    import httpx
    key = os.getenv("NEWS_API_KEY","")
    if not key: return "SKIP"
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get("https://newsapi.org/v2/everything",
                params={"q":"gold silver India","apiKey":key,"pageSize":1})
            d = r.json()
            arts = d.get("articles",[])
            return f"OK  '{arts[0]['title'][:50]}'" if arts else f"status={d.get('status')}"
    except Exception as e: return f"FAIL {e}"

async def test_gemini():
    key = os.getenv("GEMINI_API_KEY","")
    if not key: return "SKIP"
    try:
        from google import genai
        c = genai.Client(api_key=key)
        r = c.models.generate_content(model="gemini-1.5-flash", contents="Reply OK only.")
        return f"OK  {r.text.strip()}"
    except Exception as e: return f"FAIL {str(e)[:100]}"

async def test_groww():
    key = os.getenv("GROWW_API_KEY","")
    sec = os.getenv("GROWW_API_SECRET","")
    if not key or not sec: return "SKIP — set GROWW_API_KEY and GROWW_API_SECRET"
    try:
        from growwapi import GrowwAPI
        token = GrowwAPI.get_access_token(api_key=key, secret=sec)
        g     = GrowwAPI(token)
        q     = g.get_ltp(trading_symbol="RELIANCE", exchange="NSE", segment="CASH")
        return f"OK  RELIANCE LTP=Rs{q.get('ltp')}" if q else "EMPTY"
    except Exception as e: return f"FAIL {str(e)[:100]}"

async def test_nse():
    try:
        from nsepython import nse_get_index_quote
        d = nse_get_index_quote("NIFTY 50")
        return f"OK  Nifty50={d.get('last')}" if d else "EMPTY"
    except Exception as e: return f"FAIL {str(e)[:100]}"

async def test_supabase():
    url = os.getenv("SUPABASE_URL","")
    key = os.getenv("SUPABASE_SERVICE_KEY","")
    if not url or not key: return "SKIP"
    try:
        from supabase import create_client
        sb = create_client(url, key)
        sb.table("users").select("id").limit(1).execute()
        return "OK  connected, users table exists"
    except Exception as e:
        err = str(e)
        if "does not exist" in err: return "CONNECTED — run: alembic upgrade head"
        return f"FAIL {err[:100]}"

async def test_pipeline():
    sys.path.insert(0, os.path.dirname(__file__))
    try:
        from agents.data_fetcher import get_commodity_data
        print("  fetching GOLD via Finnhub...", flush=True)
        r = await get_commodity_data("GOLD")
        if r.get("error"): return f"ERROR {r['error']}"
        return f"OK  price=${r.get('current_price')}  RSI={r.get('rsi_14')}  src={r.get('data_source')}"
    except Exception as e: return f"FAIL {e}"

async def main():
    print("\n[2] API TESTS")
    for name, fn in [
        ("Finnhub",   test_finnhub),
        ("FRED",      test_fred),
        ("NewsAPI",   test_newsapi),
        ("Gemini",    test_gemini),
        ("Groww",     test_groww),
        ("nsepython", test_nse),
        ("Supabase",  test_supabase),
    ]:
        print(f"  {name:<12}", end=" → ", flush=True)
        print(await fn())

    print("\n[3] PIPELINE TEST")
    print("  get_commodity_data('GOLD') →", await test_pipeline())
    print("\n" + "="*55)
    print("  Fix any FAIL/SKIP before deploying.")
    print("="*55 + "\n")

asyncio.run(main())