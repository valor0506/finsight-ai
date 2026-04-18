# import google.generativeai as genai
# from core.config import get_settings

from google import genai
client = genai.Client(api_key=settings.gemini_api_key)

settings = get_settings()
genai.configure(api_key=settings.gemini_api_key)
model = genai.GenerativeModel("gemini-1.5-flash")


async def analyse_commodity(symbol: str, data: dict, macro: dict, analysis_type: str = "full") -> dict:
    prompt = f"""
You are a senior commodity analyst. Write a professional investment-grade report for {symbol}.

Market Data:
- Current Price: {data.get('current_price')} {data.get('currency')}
- 52W High: {data.get('week_52_high')} | 52W Low: {data.get('week_52_low')}
- % from 52W High: {data.get('pct_from_52w_high')}%
- RSI-14: {data.get('rsi_14')}
- SMA-20: {data.get('sma_20')} | SMA-50: {data.get('sma_50')}

Macro Context:
- DXY: {macro.get('DXY', {}).get('value')}
- US 10Y Yield: {macro.get('US_10Y_YIELD', {}).get('value')}
- Gold-Silver Ratio: {macro.get('GOLD_SILVER_RATIO', {}).get('value')}
- USD/INR: {macro.get('USDINR', {}).get('value')}

Write these sections:
1. Executive Summary
2. Technical Analysis
3. Macro Context & Correlations
4. Key Risks
5. Outlook & Price Targets

Be specific with numbers. Professional tone. No fluff.
"""
    try:
        response = model.generate_content(prompt)
        return {"text": response.text, "symbol": symbol}
    except Exception as e:
        return {"error": str(e)}


async def analyse_equity(symbol: str, data: dict, macro: dict) -> dict:
    prompt = f"""
You are a senior equity analyst. Write a professional investment-grade report for {symbol}.

Fundamentals:
- Company: {data.get('company_name')}
- Sector: {data.get('sector')} | Industry: {data.get('industry')}
- Market Cap: {data.get('market_cap')}
- Current Price: {data.get('current_price')} {data.get('currency')}
- PE Ratio: {data.get('pe_ratio')} | Forward PE: {data.get('forward_pe')}
- PB Ratio: {data.get('pb_ratio')} | EV/EBITDA: {data.get('ev_ebitda')}
- Revenue Growth: {data.get('revenue_growth')} | ROE: {data.get('roe')}
- Debt/Equity: {data.get('debt_to_equity')}
- Analyst Target: {data.get('analyst_target_price')} | Recommendation: {data.get('analyst_recommendation')}
- RSI-14: {data.get('rsi_14')} | Beta: {data.get('beta')}

Macro Context:
- Nifty50: {macro.get('NIFTY50', {}).get('value')}
- USD/INR: {macro.get('USDINR', {}).get('value')}
- VIX India: {macro.get('VIX_INDIA', {}).get('value')}

Write these sections:
1. Executive Summary
2. Fundamental Analysis
3. Technical Analysis
4. Risk Factors
5. Valuation & Target Price

Professional tone. Specific numbers only.
"""
    try:
        # response = model.generate_content(prompt)
        # return {"text": response.text, "symbol": symbol}
        response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents=prompt
        )
        return {"text": response.text, "symbol": symbol}
    except Exception as e:
        return {"error": str(e)}