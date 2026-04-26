"""
agents/llm_analyst.py

Tier 3 — Gemini 1.5 Flash analysis layer.

STRICT RULES:
    1. Only uses data passed in from Tier 1/2 (data_fetcher.py)
    2. If any value is None → writes "Data unavailable" for that metric
    3. Never estimates, infers, or fills missing numbers
    4. Never contradicts the raw data provided
"""
from google import genai
from core.config import get_settings

settings = get_settings()
client   = genai.Client(api_key=settings.gemini_api_key)

STRICT_PREFIX = """
STRICT DATA RULES (follow without exception):
- Only use the exact numbers provided below. Do not estimate or infer any value.
- If a metric shows None or is missing, write "Data unavailable" for that point.
- Do not use your training knowledge to fill in prices, ratios, or economic figures.
- All numbers in your report must come directly from the data provided below.
"""


def _fmt(val, suffix="", fallback="Data unavailable"):
    """Format a value safely. Returns fallback string if None."""
    if val is None:
        return fallback
    return f"{val}{suffix}"


async def analyse_commodity(symbol: str, data: dict, macro: dict, analysis_type: str = "full") -> dict:
    """
    Generate commodity intelligence report.
    data  → output of get_commodity_data()
    macro → output of get_macro_snapshot()
    """
    news_block = ""
    if data.get("news"):
        headlines = "\n".join(f"- {n['title']} ({n['source']})" for n in data["news"][:5] if n.get("title"))
        news_block = f"\nRecent News Headlines:\n{headlines}"

    prompt = f"""
{STRICT_PREFIX}

You are a senior commodity analyst writing a professional investment-grade report for Indian retail investors.
Asset: {symbol}

=== MARKET DATA (from Finnhub) ===
Current Price : {_fmt(data.get('current_price'), ' USD')}
52-Week High  : {_fmt(data.get('week_52_high'), ' USD')}
52-Week Low   : {_fmt(data.get('week_52_low'), ' USD')}
% from 52W High: {_fmt(data.get('pct_from_52w_high'), '%')}
RSI-14        : {_fmt(data.get('rsi_14'))}
SMA-20        : {_fmt(data.get('sma_20'), ' USD')}
SMA-50        : {_fmt(data.get('sma_50'), ' USD')}
Data Source   : {data.get('data_source', 'Finnhub')}
Fetched At    : {data.get('fetched_at')}

=== MACRO CONTEXT (from FRED + Finnhub + nsepython) ===
DXY (USD Index)    : {_fmt(macro.get('DXY', {}).get('value'))}
US 10Y Yield       : {_fmt(macro.get('US_10Y_YIELD', {}).get('value'), '%')}
Fed Funds Rate     : {_fmt(macro.get('FED_FUNDS_RATE', {}).get('value'), '%')}
CPI (US)           : {_fmt(macro.get('CPI_YOY', {}).get('value'))}
VIX                : {_fmt(macro.get('VIX_US', {}).get('value'))}
USD/INR            : {_fmt(macro.get('USDINR', {}).get('value'))}
Gold Price         : {_fmt(macro.get('GOLD_PRICE', {}).get('value'), ' USD')}
Silver Price       : {_fmt(macro.get('SILVER_PRICE', {}).get('value'), ' USD')}
Gold-Silver Ratio  : {_fmt(macro.get('GOLD_SILVER_RATIO', {}).get('value'))}
Nifty 50           : {_fmt(macro.get('NIFTY50', {}).get('value'))}
USD/INR Impact     : A rising DXY typically pressures commodity prices in USD terms.
                     For Indian investors, a weaker INR means higher import cost even if USD price falls.
{news_block}

=== REPORT STRUCTURE ===
Write exactly these 5 sections with these exact headings:

## 1. Executive Summary
2-3 sentences. Current price, trend direction, key signal.

## 2. Technical Analysis
RSI interpretation, price vs SMA-20/SMA-50, 52W range position, momentum.

## 3. Macro Context & India Impact
How DXY, US yields, Fed rate affect {symbol}.
How USD/INR affects Indian investors specifically (INR import cost angle).
FII/DII flows if relevant.

## 4. Key Risks
3-4 specific risks with data backing. If data is unavailable for a risk factor, say so.

## 5. Outlook & Price Targets
Near-term (1 month) and medium-term (3 month) view.
Support and resistance levels from the 52W range.
State confidence level: High / Medium / Low based on data availability.

Tone: Professional, direct, no fluff. Written for an Indian retail investor who understands basic finance.
"""

    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
        )
        return {"text": response.text, "symbol": symbol}
    except Exception as e:
        return {"error": str(e), "symbol": symbol}


async def analyse_equity(symbol: str, data: dict, macro: dict) -> dict:
    """
    Generate equity intelligence report.
    Works for both Indian (NSE/BSE) and US stocks.
    """
    exchange = data.get("exchange", "NSE")
    currency = data.get("currency", "INR")
    is_indian = exchange in ("NSE", "BSE")

    news_block = ""
    if data.get("news"):
        headlines = "\n".join(f"- {n['title']} ({n['source']})" for n in data["news"][:5] if n.get("title"))
        news_block = f"\nRecent News Headlines:\n{headlines}"

    india_context = ""
    if is_indian:
        fii_dii = macro.get("FII_DII", {})
        india_context = f"""
=== INDIA MARKET CONTEXT ===
Nifty 50      : {_fmt(macro.get('NIFTY50', {}).get('value'))}
Bank Nifty    : {_fmt(macro.get('BANKNIFTY', {}).get('value'))}
Sensex        : {_fmt(macro.get('SENSEX', {}).get('value'))}
USD/INR       : {_fmt(macro.get('USDINR', {}).get('value'))}
FII Net Flow  : {_fmt(fii_dii.get('fii_net'))} (Date: {fii_dii.get('date', 'N/A')})
DII Net Flow  : {_fmt(fii_dii.get('dii_net'))}
"""

    prompt = f"""
{STRICT_PREFIX}

You are a senior equity analyst writing a professional investment-grade report for Indian retail investors.
Stock: {symbol} | Exchange: {exchange} | Currency: {currency}

=== MARKET DATA (from {data.get('data_source', 'Groww/Finnhub')}) ===
Current Price : {_fmt(data.get('current_price'), f' {currency}')}
52-Week High  : {_fmt(data.get('week_52_high'), f' {currency}')}
52-Week Low   : {_fmt(data.get('week_52_low'), f' {currency}')}
RSI-14        : {_fmt(data.get('rsi_14'))}
SMA-50        : {_fmt(data.get('sma_50'), f' {currency}')}
SMA-200       : {_fmt(data.get('sma_200'), f' {currency}')}
Fetched At    : {data.get('fetched_at')}

=== US MACRO CONTEXT (from FRED) ===
US 10Y Yield  : {_fmt(macro.get('US_10Y_YIELD', {}).get('value'), '%')}
DXY           : {_fmt(macro.get('DXY', {}).get('value'))}
Fed Rate      : {_fmt(macro.get('FED_FUNDS_RATE', {}).get('value'), '%')}
VIX           : {_fmt(macro.get('VIX_US', {}).get('value'))}
{india_context}
{news_block}

=== REPORT STRUCTURE ===
Write exactly these 5 sections:

## 1. Executive Summary
Current price, trend, key signal. 2-3 sentences.

## 2. Technical Analysis
RSI interpretation, SMA-50 vs SMA-200 (golden/death cross if applicable),
52W range position, momentum direction.

## 3. {"India Market & Macro Context" if is_indian else "Macro Context"}
{"How Nifty trend, FII/DII flows, and USD/INR affect this stock specifically." if is_indian else "How US macro (Fed rate, DXY, yields) affects this stock."}
Connect global macro to this specific stock's sector.

## 4. Key Risks
3-4 specific risks. Use only provided data. Say "Data unavailable" for missing factors.

## 5. Valuation & Outlook
Near-term (1 month) and medium-term (3 month) view.
Support/resistance from 52W range.
Confidence level: High / Medium / Low.

Tone: Professional, specific, no fluff. For Indian retail investors.
"""

    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
        )
        return {"text": response.text, "symbol": symbol}
    except Exception as e:
        return {"error": str(e), "symbol": symbol}