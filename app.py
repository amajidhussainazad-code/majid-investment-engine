"""
MCIS Dashboard v1.0 — Majid Capital Investment System
Streamlit dynamic dashboard
Deploy: streamlit run app.py
"""

import streamlit as st
import requests
import pandas as pd
import time
import json
import os
from datetime import datetime

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="MCIS — Majid Capital Investment System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    .stApp { background-color: #f8f9fa; }

    .mcis-header {
        background: linear-gradient(135deg, #1a3c5e 0%, #2d6a9f 100%);
        color: white;
        padding: 20px 30px;
        border-radius: 12px;
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(26,60,94,0.3);
    }
    .mcis-title { font-size: 2.5em; font-weight: 800; color: white; margin: 0; }
    .mcis-subtitle { font-size: 1em; color: #c9a84c; margin: 4px 0 0 0; font-weight: 500; }

    .metric-card {
        background: white;
        border-radius: 10px;
        padding: 18px 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border-left: 4px solid #1a3c5e;
        margin-bottom: 10px;
    }
    .metric-value { font-size: 2em; font-weight: 700; color: #1a3c5e; }
    .metric-label { font-size: 0.85em; color: #666; font-weight: 500; margin-top: 2px; }

    .tier1-card { border-left-color: #1b5e20; }
    .tier2-card { border-left-color: #006064; }
    .tier3-card { border-left-color: #e65100; }
    .cash-card  { border-left-color: #c9a84c; }

    .section-header {
        background: #1a3c5e;
        color: white;
        padding: 10px 16px;
        border-radius: 8px;
        font-weight: 700;
        font-size: 1em;
        margin: 16px 0 10px 0;
    }

    .halal-pass { background: #e8f5e9; color: #1b5e20; padding: 3px 8px;
                  border-radius: 4px; font-size: 0.8em; font-weight: 600; }
    .halal-cond { background: #fff3e0; color: #e65100; padding: 3px 8px;
                  border-radius: 4px; font-size: 0.8em; font-weight: 600; }
    .halal-fail { background: #ffebee; color: #b71c1c; padding: 3px 8px;
                  border-radius: 4px; font-size: 0.8em; font-weight: 600; }

    .score-high { color: #1b5e20; font-weight: 700; }
    .score-mid  { color: #006064; font-weight: 700; }
    .score-low  { color: #e65100; font-weight: 700; }

    .stButton>button {
        background: linear-gradient(135deg, #1a3c5e, #2d6a9f);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: 600;
        font-size: 1em;
        width: 100%;
    }
    .stButton>button:hover { opacity: 0.9; }

    /* Sidebar background and all text */
    [data-testid="stSidebar"] {
        background-color: #1a3c5e !important;
    }
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    [data-testid="stSidebar"] .stRadio label {
        color: white !important;
        font-size: 0.95em !important;
    }
    [data-testid="stSidebar"] .stRadio div {
        color: white !important;
    }
    [data-testid="stSidebar"] p {
        color: white !important;
    }
    [data-testid="stSidebar"] span {
        color: white !important;
    }
    [data-testid="stSidebar"] hr {
        border-color: #c9a84c !important;
    }

    .sidebar-title { color: #c9a84c; font-size: 1.3em; font-weight: 700; }
    .sidebar-text  { color: white !important; font-size: 0.9em; }

    .info-box {
        background: #e3f2fd;
        border-left: 4px solid #1565c0;
        padding: 12px 16px;
        border-radius: 6px;
        margin: 10px 0;
        font-size: 0.9em;
        color: #1a237e;
    }
    .warning-box {
        background: #fff8e1;
        border-left: 4px solid #f9a825;
        padding: 12px 16px;
        border-radius: 6px;
        margin: 10px 0;
        font-size: 0.9em;
        color: #e65100;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────
# API key — reads from Streamlit Cloud Secrets if set (recommended), else falls back
try:
    API_KEY = st.secrets["FMP_API_KEY"]
except Exception:
    API_KEY = "fQUnMh24O1zf1FQ2kO7ldTELkf0qwRGz"
BASE    = "https://financialmodelingprep.com/stable"

NO_FLY = ["alcohol","tobacco","gambling","casino","conventional bank",
           "pork","adult entertainment","weapons of mass"]
HALAL_FAIL_SECTORS  = ["Financial Services","Banks","Banking","Insurance"]
HALAL_CLEAN_SECTORS = ["Technology","Healthcare","Industrials"]

CURATED = [
    "NVDA","MSFT","GOOGL","META","AMZN","ORCL","ADBE","CRM","NOW","SNOW",
    "DDOG","MDB","HUBS","AVGO","AMD","QCOM","MRVL","TXN","AMAT","KLAC",
    "LRCX","ENTG","MU","ARMH","CRWD","PANW","FTNT","ZS","S","CYBR",
    "ETN","PWR","VST","CEG","GEV","V","MA","PYPL","GPN","FIS","TOST",
    "LLY","NVO","ISRG","DXCM","PODD","VEEV","DOCS","ROK","ABB","FANUY",
    "MELI","SE","NU","CPNG","MNDY","PCTY","PAYC","ANSS","CDNS","SNPS",
    "EQIX","DLR","AMT","ASML","TSM","SAP","SPUS","HLAL","SPTE","SPWO",
    "MPWR","LSCC","ONTO","ACLS","ENTG","MKSI","MANH","EPAM","PTC",
]

# ─────────────────────────────────────────────
# FMP API FUNCTIONS
# ─────────────────────────────────────────────

@st.cache_data(ttl=3600)
def fmp_get(endpoint, params):
    try:
        p = dict(params)
        p["apikey"] = API_KEY
        r = requests.get(f"{BASE}/{endpoint}", params=p, timeout=15)
        return r.json()
    except:
        return []

def fetch_company(ticker):
    d = {"ticker": ticker, "ok": False}
    try:
        # Profile
        raw = fmp_get("profile", {"symbol": ticker})
        if not isinstance(raw, list) or not raw:
            return d
        p = raw[0]
        d.update({
            "name":    p.get("companyName") or ticker,
            "sector":  p.get("sector","Unknown"),
            "industry":p.get("industry","Unknown"),
            "price":   p.get("price",0),
            "mktcap":  p.get("marketCap",0),
            "desc":    p.get("description",""),
            "profile": p,
        })

        d["metrics"] = fmp_get("key-metrics",       {"symbol":ticker,"period":"annual","limit":4})
        d["ttm"]     = fmp_get("key-metrics-ttm",   {"symbol":ticker})
        d["income"]  = fmp_get("income-statement",  {"symbol":ticker,"period":"annual","limit":4})
        d["cashflow"]= fmp_get("cash-flow-statement",{"symbol":ticker,"period":"annual","limit":4})
        d["ratios"]  = fmp_get("ratios",            {"symbol":ticker,"period":"annual","limit":4})

        if isinstance(d["ttm"], list) and d["ttm"]:
            d["ttm"] = d["ttm"][0]
        elif not isinstance(d["ttm"], dict):
            d["ttm"] = {}

        # Extract FCF, shares, and net_debt for Fair Value calculation
        try:
            # FCF = Operating CF - CapEx (most recent year)
            cf = d.get("cashflow", [])
            if cf and isinstance(cf, list) and len(cf) > 0 and isinstance(cf[0], dict):
                ocf = cf[0].get("operatingCashFlow") or cf[0].get("operatingCashflows")
                capex = cf[0].get("capitalExpenditure") or cf[0].get("capitalExpenditures")
                if ocf is not None and capex is not None:
                    fcf_val = float(ocf) - abs(float(capex))
                    if fcf_val > 0:
                        d["fcf"] = fcf_val
        except Exception as e:
            pass
        
        try:
            # Shares Outstanding - try multiple sources
            shares = None
            
            # Try TTM first
            ttm_data = d.get("ttm", {})
            if isinstance(ttm_data, dict):
                shares = ttm_data.get("weightedAverageShsOut") or ttm_data.get("weightedAverageShsOutDil") or ttm_data.get("numberOfShares") or ttm_data.get("sharesOutstanding")
            
            # Try metrics
            if not shares:
                met = d.get("metrics", [])
                if met and isinstance(met, list) and len(met) > 0 and isinstance(met[0], dict):
                    shares = met[0].get("weightedAverageShsOut") or met[0].get("weightedAverageShsOutDil") or met[0].get("numberOfShares") or met[0].get("sharesOutstanding")
            
            # Try profile
            if not shares and d.get("profile"):
                shares = d["profile"].get("shFloat") or d["profile"].get("sharesOutstanding") or d["profile"].get("sharesFloat")
            
            if shares and shares > 0:
                d["shares"] = float(shares)
        except Exception as e:
            pass
        
        try:
            # Net Debt = Total Debt - Cash
            ttm = d.get("ttm", {})
            if isinstance(ttm, dict):
                total_debt = ttm.get("totalDebt") or ttm.get("longTermDebt") or ttm.get("totalLiabilities", 0)
                cash = ttm.get("cashAndCashEquivalents") or ttm.get("cash") or ttm.get("shortTermInvestments", 0)
                
                if total_debt and cash is not None:
                    d["net_debt"] = float(total_debt) - float(cash)
                elif total_debt:
                    d["net_debt"] = float(total_debt)
        except Exception as e:
            pass

        d["ok"] = True
    except Exception as e:
        d["err"] = str(e)
    return d

def fetch_valuation_data(ticker):
    """Fetch 6 years of financials for valuation and dossier."""
    d = fetch_company(ticker)
    if not d.get("ok"): return d
    d["income6"]   = fmp_get("income-statement",     {"symbol": ticker, "period": "annual", "limit": 6})
    d["cashflow6"] = fmp_get("cash-flow-statement",  {"symbol": ticker, "period": "annual", "limit": 6})
    d["balance"]   = fmp_get("balance-sheet-statement", {"symbol": ticker, "period": "annual", "limit": 2})
    q = fmp_get("quote", {"symbol": ticker})
    d["quote"] = q[0] if isinstance(q, list) and q else {}
    d["metrics6"]  = fmp_get("key-metrics", {"symbol": ticker, "period": "annual", "limit": 6})
    return d

# ─────────────────────────────────────────────
# HALAL CHECK
# ─────────────────────────────────────────────

def check_halal(d):
    desc    = d.get("desc","").lower()
    sector  = d.get("sector","")
    industry= d.get("industry","").lower()
    if any(k in desc     for k in NO_FLY):          return "FAIL",        "Prohibited activity"
    if any(s in sector   for s in HALAL_FAIL_SECTORS):return "FAIL",       "Conventional finance"
    if any(k in industry for k in ["bank","insur","alcohol","tobacco","casino","gambling"]):
        return "FAIL", f"Prohibited: {industry}"
    if sector in HALAL_CLEAN_SECTORS:               return "PASS",        "Clean sector"
    return "CONDITIONAL", "Verify via Zoya"

# ─────────────────────────────────────────────
# EXTRACT METRICS
# ─────────────────────────────────────────────

def extract_metrics(d):
    m   = {}
    met = d.get("metrics",[])
    ttm = d.get("ttm",{})
    rat = d.get("ratios",[])
    inc = d.get("income",[])
    cf  = d.get("cashflow",[])

    # ROIC
    for yr in met[:2]:
        v = yr.get("returnOnInvestedCapital") or yr.get("roic")
        if v is not None: m["roic"] = round(float(v)*100,1); break
    if "roic" not in m:
        v = ttm.get("returnOnInvestedCapitalTTM") or ttm.get("roicTTM")
        if v is not None: m["roic"] = round(float(v)*100,1)

    # FCF
    fcf_list = []
    for yr in cf[:4]:
        v = yr.get("freeCashFlow")
        if v is not None: fcf_list.append(float(v))
    m["fcf_list"] = fcf_list

    # Gross Margin
    for yr in rat[:2]:
        v = yr.get("grossProfitMargin") or yr.get("grossMargin")
        if v is not None: m["gm"] = round(float(v)*100,1); break
    if "gm" not in m:
        for yr in inc[:1]:
            rev,gp = yr.get("revenue",0),yr.get("grossProfit",0)
            if rev and gp: m["gm"] = round((gp/rev)*100,1)

    # Revenue CAGR
    revs = [float(yr["revenue"]) for yr in inc[:4] if yr.get("revenue")]
    if len(revs) >= 3:
        m["rev_cagr"] = round(((revs[0]/revs[-1])**(1/(len(revs)-1))-1)*100,1)

    # Debt/EBITDA
    for yr in met[:2]:
        v = yr.get("debtToEbitda") or yr.get("netDebtToEBITDA")
        if v is not None: m["debt_ebitda"] = round(float(v),2); break
    if "debt_ebitda" not in m:
        v = ttm.get("debtToEbitdaTTM") or ttm.get("netDebtToEBITDATTM")
        if v is not None: m["debt_ebitda"] = round(float(v),2)

    # PE
    for yr in met[:1]:
        v = yr.get("peRatio") or yr.get("priceToEarningsRatio")
        if v: m["pe"] = round(float(v),1)
    if "pe" not in m:
        v = ttm.get("peRatioTTM")
        if v: m["pe"] = round(float(v),1)
    
    # Fallback: Calculate P/E from Price / EPS if not available
    if "pe" not in m and d.get("price") and d.get("income"):
        try:
            price = float(d.get("price", 0))
            eps = float(d.get("income", [{}])[0].get("eps", 0))
            if price > 0 and eps > 0:
                m["pe"] = round(price / eps, 1)
        except:
            pass

    # EV/EBITDA
    v = ttm.get("evToEbitdaTTM") or ttm.get("enterpriseValueOverEBITDATTM")
    if v: m["ev_ebitda"] = round(float(v),1)

    # FCF Yield
    v = ttm.get("freeCashFlowYieldTTM")
    if v: m["fcf_yield"] = round(float(v)*100,1)

    return m

# ─────────────────────────────────────────────
# RUN MCIS FILTERS
# ─────────────────────────────────────────────

def run_filters(d):
    r = {
        "ticker":  d["ticker"],
        "name":    d.get("name",d["ticker"]),
        "sector":  d.get("sector","Unknown"),
        "price":   d.get("price",0),
        "mktcap":  d.get("mktcap",0),
        # Add financial data for Fair Value calculation
        "fcf":     d.get("fcf", 0),
        "shares":  d.get("shares", 0),
        "net_debt": d.get("net_debt", 0),
        "passed":  [], "failed": [], "warnings": [],
        "score":   0,  "metrics": {},
        "verdict": "", "layer":   "",
        "halal":   "", "halal_reason": "",
    }

    desc = d.get("desc","").lower()
    if any(k in desc for k in NO_FLY):
        r["verdict"] = "REJECTED — No Fly Zone"; return r

    h_status, h_reason = check_halal(d)
    r["halal"] = h_status; r["halal_reason"] = h_reason
    if h_status == "FAIL":
        r["verdict"] = "REJECTED — Halal Fail"; return r

    m = extract_metrics(d)
    r["metrics"] = m

    # Filter 1 — ROIC
    if "roic" in m:
        if   m["roic"] >= 15: r["passed"].append(f"ROIC {m['roic']}%");  r["score"]+=25
        elif m["roic"] >= 10: r["warnings"].append(f"ROIC {m['roic']}%");r["score"]+=10
        else:                 r["failed"].append(f"ROIC {m['roic']}% low")
    else: r["warnings"].append("ROIC unavailable")

    # Filter 2 — FCF
    fcf = m.get("fcf_list",[])
    if fcf:
        if   fcf[0]>0 and len(fcf)>=2 and fcf[0]>fcf[-1]:
            r["passed"].append("FCF positive+growing"); r["score"]+=20
        elif fcf[0]>0:
            r["warnings"].append("FCF positive"); r["score"]+=10
        else: r["failed"].append("FCF negative")
    else: r["warnings"].append("FCF unavailable")

    # Filter 3 — Gross Margin
    if "gm" in m:
        if   m["gm"]>=35: r["passed"].append(f"GM {m['gm']}%");  r["score"]+=20
        elif m["gm"]>=20: r["warnings"].append(f"GM {m['gm']}%");r["score"]+=8
        else:             r["failed"].append(f"GM {m['gm']}% low")
    else: r["warnings"].append("GM unavailable")

    # Filter 4 — Revenue Growth
    if "rev_cagr" in m:
        if   m["rev_cagr"]>=8: r["passed"].append(f"RevCAGR {m['rev_cagr']}%"); r["score"]+=20
        elif m["rev_cagr"]>=3: r["warnings"].append(f"RevCAGR {m['rev_cagr']}%");r["score"]+=8
        else:                  r["failed"].append(f"RevCAGR {m['rev_cagr']}% low")
    else: r["warnings"].append("RevCAGR unavailable")

    # Filter 5 — Debt/EBITDA
    if "debt_ebitda" in m:
        if   m["debt_ebitda"]<0:  r["passed"].append("Net cash");         r["score"]+=15
        elif m["debt_ebitda"]<=3: r["passed"].append(f"D/E {m['debt_ebitda']}x"); r["score"]+=15
        elif m["debt_ebitda"]<=5: r["warnings"].append(f"D/E {m['debt_ebitda']}x elevated");r["score"]+=5
        else:                     r["failed"].append(f"D/E {m['debt_ebitda']}x high")
    else: r["warnings"].append("Debt/EBITDA unavailable")

    fails = len(r["failed"]); s = r["score"]
    if   fails==0 and s>=75: r["verdict"]="TIER 1"; r["layer"]="LONG_TERM"
    elif fails<=1 and s>=55: r["verdict"]="TIER 2"; r["layer"]="MID_TERM"
    elif fails<=2 and s>=35: r["verdict"]="TIER 3"; r["layer"]="SWING"
    else:                    r["verdict"]="REJECTED";r["layer"]="REJECTED"

    return r

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown('<p class="sidebar-title">⚡ MCIS</p>', unsafe_allow_html=True)
    st.markdown('<p class="sidebar-text">Majid Capital Investment System</p>', unsafe_allow_html=True)
    st.markdown("---")

    page = st.radio(
        "Navigate",
        ["🏠 Dashboard", "🔍 Scanner", "📊 Rankings", "🔎 Company Lookup",
         "🏛 Valuation Engine", "🚨 Qualitative Alerts", "📄 Company Dossier",
         "📋 Watchlist", "⚡ Swing Trades", "📅 Quarterly Review", "🔬 Data Audit"],
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.markdown('<p class="sidebar-text" style="font-size:0.8em">Blueprint v1.1 | Not investment advice</p>',
                unsafe_allow_html=True)

# ─────────────────────────────────────────────
# PERSISTENT STORAGE
# ─────────────────────────────────────────────
SAVE_FILE = "mcis_data.json"

def save_to_disk():
    try:
        data = {
            "scan_results": st.session_state.get("scan_results", []),
            "watchlist":    st.session_state.get("watchlist", []),
            "swing_trades": st.session_state.get("swing_trades", []),
            "last_scan":    st.session_state.get("last_scan", None),
        }
        with open(SAVE_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        pass

def load_from_disk():
    try:
        if os.path.exists(SAVE_FILE):
            with open(SAVE_FILE, "r") as f:
                return json.load(f)
    except:
        pass
    return None

# ─────────────────────────────────────────────
# SESSION STATE — load from disk on startup
# ─────────────────────────────────────────────
_saved = load_from_disk()

if "scan_results" not in st.session_state:
    st.session_state.scan_results = _saved["scan_results"] if _saved and "scan_results" in _saved else []
if "watchlist" not in st.session_state:
    st.session_state.watchlist = _saved["watchlist"] if _saved and "watchlist" in _saved else []
if "swing_trades" not in st.session_state:
    st.session_state.swing_trades = _saved["swing_trades"] if _saved and "swing_trades" in _saved else []
if "last_scan" not in st.session_state:
    st.session_state.last_scan = _saved["last_scan"] if _saved and "last_scan" in _saved else None

# ─────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────

def halal_badge(status):
    if status == "PASS":        return "🟢 PASS"
    elif status == "CONDITIONAL": return "🟡 CHECK"
    else:                       return "🔴 FAIL"

def score_color(score):
    if score >= 75:   return "🟢"
    elif score >= 55: return "🟡"
    else:             return "🔴"

def fmt_mktcap(v):
    if not v: return "N/A"
    if v >= 1e12: return f"${v/1e12:.1f}T"
    if v >= 1e9:  return f"${v/1e9:.1f}B"
    return f"${v/1e6:.0f}M"

def analyze_etf_prices(etf_ticker):
    """Fetch and analyze 5-year ETF price history with caching"""
    try:
        # Try historical prices with caching
        hist = fmp_get("historical-price-full", {"symbol": etf_ticker, "serietype": "line"})
        
        if isinstance(hist, dict) and "historical" in hist:
            prices = hist.get("historical", [])
            if prices and len(prices) > 0:
                # Get current and historical stats
                current = float(prices[0].get("close", 0)) or float(prices[0].get("adjClose", 0)) or 0
                
                # Get 5-year data (1250 trading days ≈ 5 years)
                five_year = prices[:min(1250, len(prices))]
                closes = [float(p.get("close", 0)) or float(p.get("adjClose", 0)) for p in five_year if (p.get("close") or p.get("adjClose"))]
                
                if closes and current > 0:
                    high_5y = max(closes)
                    low_5y = min(closes)
                    buy_target = low_5y * 0.95
                    
                    return {
                        "current": current,
                        "high": high_5y,
                        "low": low_5y,
                        "target": buy_target,
                        "status": "✅ Data"
                    }
    except Exception as e:
        pass
    
    # Fallback: Get current quote and show note
    try:
        quote = fmp_get("quote", {"symbol": etf_ticker})
        if quote and isinstance(quote, list) and len(quote) > 0:
            current = float(quote[0].get("price", 0)) or 0
            if current > 0:
                return {
                    "current": current,
                    "high": current * 1.15,  # Estimate
                    "low": current * 0.75,
                    "target": current * 0.80,
                    "status": "⏳ Estimated"
                }
    except:
        pass
    
    return None

def calculate_blended_fair_value(r):
    """
    Calculate Fair Value using 6 weighted methods.
    Uses available data from scanner results.
    """
    valuations = {}
    weights = {
        "reverse_dcf": 0.20,
        "historical_multiples": 0.15,
        "lynch": 0.10,
        "buffett": 0.05,
        "fcf_yield": 0.05,
        "graham": 0.05,
    }
    
    price = float(r.get("price", 0) or 0)
    metrics = r.get("metrics", {})
    
    if not price or price <= 0:
        return None
    
    pe = float(metrics.get("pe", 0) or 0)
    rev_cagr = float(metrics.get("rev_cagr", 0) or 0)
    roic = float(metrics.get("roic", 0) or 0)
    gm = float(metrics.get("gm", 0) or 0)  # Gross margin as proxy for quality
    
    try:
        # 1. REVERSE DCF (20%) - Conservative: assume fair value 5% above current
        valuations["reverse_dcf"] = price * 1.05
    except:
        pass
    
    try:
        # 2. HISTORICAL MULTIPLES (15%) - P/E based
        if pe > 1 and pe < 100 and rev_cagr > 1:
            # Fair P/E = Growth Rate * 1.5 (PEG = 1.5)
            fair_pe = max((rev_cagr / 100) * 1.5 * 100, 10)
            fair_price = price * (fair_pe / pe)
            valuations["historical_multiples"] = fair_price
    except:
        pass
    
    try:
        # 3. PETER LYNCH (10%) - Growth as fair P/E
        if pe > 1 and rev_cagr > 1:
            # Lynch: Fair P/E = Growth Rate
            fair_pe = rev_cagr
            lynch_price = price * (fair_pe / pe)
            valuations["lynch"] = lynch_price
    except:
        pass
    
    try:
        # 4. BUFFETT QUALITY PREMIUM (5%) - ROIC-based
        if roic > 15:  # Only if ROIC > 15% (Buffett threshold)
            # Premium: 1.2x + (ROIC-15%)*0.1
            premium = 1.2 + ((roic - 15) / 100) * 0.1
            buffett_price = price * min(premium, 2.0)
            valuations["buffett"] = buffett_price
    except:
        pass
    
    try:
        # 5. FCF YIELD (5%) - Quality companies should trade at lower yield
        if gm > 35:  # Good gross margin = healthy FCF
            # Assume 4% FCF yield is fair for quality
            # Price / FCF yield should be reasonable
            fcf_yield_price = price * 1.25  # 25% premium for FCF quality
            valuations["fcf_yield"] = fcf_yield_price
    except:
        pass
    
    try:
        # 6. GRAHAM NUMBER (5%) - Fundamental safety margin
        # Simplified: Fair value = Price * sqrt(Quality Score)
        # Using gross margin as quality proxy
        if gm > 20:
            quality_factor = (gm / 50) ** 0.5  # Normalize to ~1.0
            graham_price = price * max(quality_factor, 0.8)
            valuations["graham"] = graham_price
    except:
        pass
    
    # Calculate weighted average
    if valuations:
        total_weight = sum([weights.get(k, 0) for k in valuations.keys()])
        if total_weight > 0:
            blended = sum([valuations[k] * weights.get(k, 0) for k in valuations.keys()]) / total_weight
            return blended if blended > price * 0.5 else price * 1.1  # Sanity check
    
    return None

def results_to_df(results):
    rows = []
    for r in results:
        m = r.get("metrics",{})
        
        # Calculate Target Entry using blended valuation
        target_entry = "N/A"
        try:
            price = float(r.get("price", 0) or 0)
            
            if price > 0:
                # Use blended fair value calculation
                fair_value = calculate_blended_fair_value(r)
                
                if fair_value and fair_value > 1:
                    # Target Entry = Fair Value with 30-50% margin of safety
                    target_bear = fair_value * 0.50  # 50% discount
                    target_base = fair_value * 0.70  # 30% discount
                    target_entry = f"${target_bear:,.0f} - ${target_base:,.0f}"
                else:
                    # Fallback if blended fails
                    target_bear = price * 0.60  # 40% discount
                    target_base = price * 0.80  # 20% discount
                    target_entry = f"${target_bear:,.0f} - ${target_base:,.0f}"
        except:
            pass
        
        rows.append({
            "Ticker":    r["ticker"],
            "Company":   r["name"],
            "Sector":    r["sector"],
            "Score":     r["score"],
            "Tier":      r["verdict"],
            "ROIC%":     m.get("roic","N/A"),
            "GM%":       m.get("gm","N/A"),
            "RevCAGR%":  m.get("rev_cagr","N/A"),
            "Debt/EB":   m.get("debt_ebitda","N/A"),
            "P/E":       m.get("pe","N/A"),
            "Price":     f"${r['price']:,.2f}" if r.get('price') else "N/A",
            "Target Entry": target_entry,
            "Mkt Cap":   fmt_mktcap(r.get("mktcap",0)),
            "Halal":     r.get("halal","?"),
        })
    return pd.DataFrame(rows)

# ═════════════════════════════════════════════
# PRICE CHART & DATA VALIDATION FUNCTIONS
# ═════════════════════════════════════════════

@st.cache_data(ttl=3600)
def fetch_historical_prices_yahoo(ticker, days=1825):
    """Fetch 5 years of historical daily close prices from FMP (now unlocked with premium)."""
    try:
        raw = fmp_get("historical-price-full", {"symbol": ticker, "timeseries": days})
        
        # Debug: check what we got back
        if isinstance(raw, dict):
            if "historical" in raw:
                prices = raw["historical"]
                if prices and len(prices) > 0:
                    return sorted(prices, key=lambda x: x["date"])
            elif "error" in raw:
                return None  # Silent fail, will show message to user
            else:
                # Got dict but no historical or error key
                return None
        
        if isinstance(raw, list) and len(raw) > 0:
            return raw
        
        return []
    except Exception as e:
        return []

def plot_5year_price_chart_yahoo(prices, ticker, current_price=None):
    """Create interactive 5-year price chart from Yahoo Finance data using Plotly."""
    import plotly.graph_objects as go
    
    if not prices or len(prices) < 2:
        return None
    
    # Handle both list of dicts and dict with summary stats
    if isinstance(prices, dict):
        # Summary stats only, no daily data
        fig = go.Figure()
        fig.add_annotation(
            text=f"<b>{ticker} Price Summary</b><br>" +
                 f"Current: ${prices.get('current_price', 0):,.2f}<br>" +
                 f"52W High: ${prices.get('52w_high', 0):,.2f}<br>" +
                 f"52W Low: ${prices.get('52w_low', 0):,.2f}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14),
            align="center"
        )
        fig.update_layout(height=300, template="plotly_white", margin=dict(l=50, r=50, t=50, b=50))
        return fig
    
    # Has daily data
    dates = [p["date"] for p in prices]
    closes = [float(p["close"]) for p in prices]
    highs = [float(p.get("high", p["close"])) for p in prices]
    lows = [float(p.get("low", p["close"])) for p in prices]
    
    closes_52w = closes[-252:] if len(closes) > 252 else closes
    high_52w = max(closes_52w) if closes_52w else max(closes)
    low_52w = min(closes_52w) if closes_52w else min(closes)
    high_5y = max(closes)
    low_5y = min(closes)
    
    fig = go.Figure()
    
    # Price line
    fig.add_trace(go.Scatter(
        x=dates, y=closes, mode="lines", 
        name="Close Price",
        line=dict(color="#1a3c5e", width=2),
        hovertemplate="<b>%{x}</b><br>Close: $%{y:,.2f}<extra></extra>"
    ))
    
    # 52-week range
    fig.add_hline(y=high_52w, line_dash="dash", line_color="#e65100", line_width=1,
                 annotation_text=f"52W High: ${high_52w:,.0f}", annotation_position="right")
    fig.add_hline(y=low_52w, line_dash="dash", line_color="#e65100", line_width=1,
                 annotation_text=f"52W Low: ${low_52w:,.0f}", annotation_position="right")
    
    # Current price
    if current_price:
        fig.add_hline(y=current_price, line_dash="solid", line_color="#1b5e20", line_width=3,
                     annotation_text=f"Current: ${current_price:,.2f}", annotation_position="right")
    
    fig.update_layout(
        title=f"{ticker} — 5-Year Price History | High: ${high_5y:,.0f} | Low: ${low_5y:,.0f}",
        xaxis_title="Date", yaxis_title="Close Price ($)",
        hovermode="x unified", height=380, template="plotly_white",
        margin=dict(l=50, r=120, t=60, b=50))
    
    return fig

def validate_financial_data(d, result):
    """Check for suspicious or impossible financial metrics."""
    m = result.get("metrics", {})
    flags = []
    quality = "🟢 VALIDATED"
    
    gm = m.get("gm")
    if gm is not None:
        if gm > 90:
            flags.append(f"⚠️ Gross margin {gm}% is unusually high — verify vs SEC filing")
            quality = "🟡 CAUTION"
        elif gm < 0:
            flags.append(f"🔴 Gross margin {gm}% is negative — data error or distressed")
            quality = "🔴 REQUIRES REVIEW"
    
    inc = d.get("income", []) or []
    if inc and inc[0].get("revenue"):
        nm = (float(inc[0].get("netIncome") or 0) / float(inc[0]["revenue"])) * 100
        if nm > 50:
            flags.append(f"⚠️ Net margin {nm:.1f}% is very high — verify vs competitors")
            quality = "🟡 CAUTION"
        elif nm < -50:
            flags.append(f"🔴 Net margin {nm:.1f}% — deeply unprofitable")
            quality = "🔴 REQUIRES REVIEW"
    
    revs = [float(yr.get("revenue") or 0) for yr in inc[:4] if yr.get("revenue")]
    if len(revs) >= 2:
        yoy_growth = ((revs[0] / revs[-1]) - 1) * 100
        if yoy_growth > 200:
            flags.append(f"⚠️ YoY revenue growth {yoy_growth:.0f}% — verify vs press release")
            quality = "🟡 CAUTION"
        elif yoy_growth < -50:
            flags.append(f"🔴 Revenue down {yoy_growth:.0f}% YoY — significant contraction")
            quality = "🔴 REQUIRES REVIEW"
    
    de = m.get("debt_ebitda")
    if de is not None:
        if de > 8:
            flags.append(f"🔴 Debt/EBITDA {de:.1f}x is dangerously high")
            quality = "🔴 REQUIRES REVIEW"
        elif de > 5:
            flags.append(f"⚠️ Debt/EBITDA {de:.1f}x — elevated leverage")
            quality = "🟡 CAUTION"
    
    return {"quality_badge": quality, "flags": flags}

@st.cache_data(ttl=86400)
def audit_fmp_vs_yahoo(ticker):
    """Compare FMP data against Yahoo Finance for validation."""
    audit = {"ticker": ticker, "matches": {}, "discrepancies": []}
    try:
        import requests
        # FMP data
        fmp_data = fetch_company(ticker)
        if not fmp_data.get("ok"):
            return audit
        
        # Yahoo Finance data
        yf_url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=financialData,incomeStatementHistory"
        yf_resp = requests.get(yf_url, timeout=15)
        yf_data = yf_resp.json()
        
        if "quoteSummary" not in yf_data or not yf_data["quoteSummary"].get("result"):
            return audit
        
        yf = yf_data["quoteSummary"]["result"][0]
        
        # Compare revenue (most recent year)
        fmp_rev = fmp_data.get("income", [])
        yf_rev = yf.get("incomeStatementHistory", {}).get("incomeStatementHistory", [])
        
        if fmp_rev and yf_rev:
            fmp_val = float(fmp_rev[0].get("revenue") or 0)
            yf_val = float(yf_rev[0].get("totalRevenue", {}).get("raw") or 0)
            if fmp_val and yf_val:
                pct_diff = abs((fmp_val - yf_val) / yf_val) * 100
                audit["matches"]["revenue"] = f"FMP ${fmp_val/1e9:.1f}B vs Yahoo ${yf_val/1e9:.1f}B (diff: {pct_diff:.1f}%)"
                if pct_diff > 5:
                    audit["discrepancies"].append(f"Revenue mismatch {pct_diff:.1f}%")
        
        # Compare price
        fmp_price = fmp_data.get("price", 0)
        yf_price = yf.get("financialData", {}).get("currentPrice", {}).get("raw", 0)
        if fmp_price and yf_price:
            pct_diff = abs((fmp_price - yf_price) / yf_price) * 100
            audit["matches"]["price"] = f"FMP ${fmp_price:,.2f} vs Yahoo ${yf_price:,.2f} (diff: {pct_diff:.1f}%)"
            if pct_diff > 2:
                audit["discrepancies"].append(f"Price mismatch {pct_diff:.1f}%")
        
        audit["status"] = "✅ MATCH" if not audit["discrepancies"] else "⚠️ REVIEW"
    except Exception as e:
        audit["error"] = str(e)
    
    return audit

# ═════════════════════════════════════════════
# VALUATION ENGINE FUNCTIONS (global scope)
# ═════════════════════════════════════════════

def _val_inputs(d):
    """Extract the raw numbers the valuation engine needs."""
    v = {}
    q   = d.get("quote", {})
    bal = d.get("balance", []) or []
    cf  = d.get("cashflow6", []) or []
    inc = d.get("income6", []) or []
    v["price"]  = float(q.get("price") or d.get("price") or 0)
    v["shares"] = float(q.get("sharesOutstanding") or 0)
    if not v["shares"] and v["price"] and d.get("mktcap"):
        v["shares"] = d["mktcap"] / v["price"]
    v["mktcap"] = float(q.get("marketCap") or d.get("mktcap") or 0)
    b0 = bal[0] if bal else {}
    cash = float(b0.get("cashAndShortTermInvestments") or b0.get("cashAndCashEquivalents") or 0)
    debt = float(b0.get("totalDebt") or 0)
    v["net_debt"] = debt - cash
    fcf_hist = [float(y["freeCashFlow"]) for y in reversed(cf) if y.get("freeCashFlow") is not None]
    v["fcf_hist"] = fcf_hist
    ttm = d.get("ttm", {}) or {}
    v["fcf0"] = float(ttm.get("freeCashFlowTTM") or (fcf_hist[-1] if fcf_hist else 0))
    if not v["fcf0"] and fcf_hist: v["fcf0"] = fcf_hist[-1]
    def cagr(series):
        s = [x for x in series if x and x > 0]
        if len(s) >= 3: return (s[-1]/s[0])**(1/(len(s)-1)) - 1
        return None
    v["fcf_cagr"] = cagr(fcf_hist)
    revs = [float(y["revenue"]) for y in reversed(inc) if y.get("revenue")]
    v["rev_hist"] = revs
    v["rev_cagr"] = cagr(revs)
    eps  = [float(y["eps"]) for y in reversed(inc) if y.get("eps") is not None]
    v["eps_hist"] = eps
    v["eps_cagr"] = cagr([e for e in eps if e > 0]) if any(e > 0 for e in eps) else None
    v["ni_hist"]  = [float(y.get("netIncome") or 0) for y in reversed(inc)]
    v["shares_hist"] = [float(y.get("weightedAverageShsOutDil") or y.get("weightedAverageShsOut") or 0)
                        for y in reversed(inc)]
    return v

def dcf_equity_value(fcf0, g1, wacc, terminal_g, net_debt, fade_years=5, growth_years=5):
    """Two-stage DCF: growth_years at g1, then linear fade to terminal_g, plus terminal value."""
    if fcf0 <= 0 or wacc <= terminal_g: return None, []
    flows, fcf = [], fcf0
    for yr in range(1, growth_years + 1):
        fcf *= (1 + g1); flows.append(fcf)
    for i in range(1, fade_years + 1):
        g = g1 + (terminal_g - g1) * i / fade_years
        fcf *= (1 + g); flows.append(fcf)
    pv = sum(f / (1 + wacc) ** (i + 1) for i, f in enumerate(flows))
    tv = flows[-1] * (1 + terminal_g) / (wacc - terminal_g)
    pv += tv / (1 + wacc) ** len(flows)
    return pv - net_debt, flows

def reverse_dcf(price, shares, fcf0, wacc, terminal_g, net_debt):
    """Bisection: what growth rate is priced in at the current market price?"""
    if fcf0 <= 0 or not shares or not price: return None
    target = price * shares
    lo, hi = -0.10, 0.60
    for _ in range(60):
        mid = (lo + hi) / 2
        ev, _ = dcf_equity_value(fcf0, mid, wacc, terminal_g, net_debt)
        if ev is None: return None
        if ev < target: lo = mid
        else: hi = mid
    return (lo + hi) / 2

def buffett_test(d, v):
    """10-point Buffett quality checklist on real data. Returns (checks, score, max)."""
    checks = []
    met  = d.get("metrics6", []) or []
    rat  = d.get("ratios", []) or []
    inc  = d.get("income6", []) or []
    def add(name, ok, detail):
        checks.append({"check": name, "ok": ok, "detail": detail})
    roics = []
    for y in met:
        r = y.get("returnOnInvestedCapital") or y.get("roic")
        if r is not None: roics.append(float(r) * 100)
    add("ROIC ≥ 15% (latest)", bool(roics) and roics[0] >= 15,
        f"{roics[0]:.1f}%" if roics else "n/a")
    add("ROIC ≥ 12% every year (consistency)", bool(roics) and len(roics) >= 3 and min(roics[:5]) >= 12,
        f"min {min(roics[:5]):.1f}% over {min(len(roics),5)} yrs" if roics else "n/a")
    gm = None
    for y in rat[:1]:
        g = y.get("grossProfitMargin") or y.get("grossMargin")
        if g is not None: gm = float(g) * 100
    if gm is None and inc:
        rev, gp = inc[0].get("revenue"), inc[0].get("grossProfit")
        if rev and gp: gm = gp / rev * 100
    add("Gross margin ≥ 40% (pricing power)", gm is not None and gm >= 40,
        f"{gm:.1f}%" if gm is not None else "n/a")
    nm = None
    if inc and inc[0].get("revenue"):
        nm = float(inc[0].get("netIncome") or 0) / float(inc[0]["revenue"]) * 100
    add("Net margin ≥ 15%", nm is not None and nm >= 15, f"{nm:.1f}%" if nm is not None else "n/a")
    fm = None
    if v["fcf_hist"] and v["rev_hist"]:
        fm = v["fcf_hist"][-1] / v["rev_hist"][-1] * 100
    add("FCF margin ≥ 12%", fm is not None and fm >= 12, f"{fm:.1f}%" if fm is not None else "n/a")
    de = d.get("metrics", [])
    dv = None
    for y in (de[:2] if isinstance(de, list) else []):
        x = y.get("debtToEbitda") or y.get("netDebtToEBITDA")
        if x is not None: dv = float(x); break
    add("Debt/EBITDA ≤ 2.5x or net cash", dv is not None and dv <= 2.5,
        f"{dv:.2f}x" if dv is not None else "n/a")
    add("Revenue CAGR ≥ 8%", v["rev_cagr"] is not None and v["rev_cagr"] >= 0.08,
        f"{v['rev_cagr']*100:.1f}%" if v["rev_cagr"] is not None else "n/a")
    add("EPS growing over 5 yrs", v["eps_cagr"] is not None and v["eps_cagr"] > 0,
        f"{v['eps_cagr']*100:.1f}% CAGR" if v["eps_cagr"] is not None else "n/a")
    sh = [s for s in v["shares_hist"] if s > 0]
    add("Share count flat or shrinking (buybacks)", len(sh) >= 3 and sh[-1] <= sh[0] * 1.02,
        f"{(sh[-1]/sh[0]-1)*100:+.1f}% over {len(sh)} yrs" if len(sh) >= 3 else "n/a")
    conv = None
    if v["fcf_hist"] and v["ni_hist"] and v["ni_hist"][-1] > 0:
        conv = v["fcf_hist"][-1] / v["ni_hist"][-1] * 100
    add("FCF / Net Income ≥ 80% (earnings are real cash)", conv is not None and conv >= 80,
        f"{conv:.0f}%" if conv is not None else "n/a")
    score = sum(1 for c in checks if c["ok"])
    return checks, score, len(checks)

def lynch_classify(d, v, pe):
    """Peter Lynch category + PEG verdict."""
    g = v["eps_cagr"] if v["eps_cagr"] is not None else v["rev_cagr"]
    g_pct = g * 100 if g is not None else None
    mktcap = v["mktcap"]
    sector = d.get("sector", "")
    cyclical_sectors = ["Energy", "Basic Materials", "Consumer Cyclical", "Industrials", "Materials"]
    eps = v["eps_hist"]
    if eps and eps[-1] < 0 and len(eps) >= 2 and max(eps) > 0:
        cat, note = "Turnaround", "Earnings currently negative after being positive — thesis depends on recovery, size positions small."
    elif g_pct is None:
        cat, note = "Unclassified", "Not enough growth history to classify."
    elif g_pct >= 20:
        cat, note = "Fast Grower", "Lynch's favourite — 20%+ growers. Watch for the growth fade; pay up only with a reasonable PEG."
    elif g_pct >= 10:
        cat = "Stalwart" if mktcap > 10e9 else "Mid-pace Grower"
        note = "Solid 10-20% grower. Lynch expects 30-50% gains then rotate — do not expect a ten-bagger."
    elif sector in cyclical_sectors:
        cat, note = "Cyclical", "Earnings follow the economic cycle — low P/E can be a TOP not a bottom. Time the cycle, not the P/E."
    else:
        cat, note = "Slow Grower", "Sub-10% growth — only interesting for dividends. Rarely a fit for MCIS Tier 1."
    peg = None
    if pe and g_pct and g_pct > 0:
        peg = pe / g_pct
    if peg is None:            peg_verdict = "PEG unavailable"
    elif peg <= 1.0:           peg_verdict = "PEG ≤ 1.0 — attractively priced for its growth (Lynch buy zone)"
    elif peg <= 1.5:           peg_verdict = "PEG 1.0-1.5 — fairly priced"
    elif peg <= 2.0:           peg_verdict = "PEG 1.5-2.0 — expensive, needs execution"
    else:                      peg_verdict = "PEG > 2.0 — priced for perfection"
    return cat, note, peg, peg_verdict, g_pct

def moat_assessment(d, v):
    """Quantitative moat evidence score 0-10."""
    ev, score = [], 0
    rat = d.get("ratios", []) or []
    gms = []
    for y in rat:
        g = y.get("grossProfitMargin") or y.get("grossMargin")
        if g is not None: gms.append(float(g) * 100)
    if gms:
        avg = sum(gms) / len(gms)
        if avg >= 50: score += 2; ev.append(f"🟢 Avg gross margin {avg:.0f}% — strong pricing power (+2)")
        elif avg >= 35: score += 1; ev.append(f"🟡 Avg gross margin {avg:.0f}% — decent (+1)")
        else: ev.append(f"🔴 Avg gross margin {avg:.0f}% — weak pricing power (+0)")
        if len(gms) >= 3 and (max(gms) - min(gms)) <= 6:
            score += 1; ev.append(f"🟢 Margin stability — range only {max(gms)-min(gms):.1f} pts (+1)")
    met = d.get("metrics6", []) or []
    roics = [float(y.get("returnOnInvestedCapital") or y.get("roic") or 0) * 100
             for y in met if (y.get("returnOnInvestedCapital") or y.get("roic")) is not None]
    if roics:
        if min(roics[:5]) >= 15 and len(roics) >= 3:
            score += 3; ev.append(f"🟢 ROIC ≥ 15% every year for {min(len(roics),5)} yrs — durable advantage (+3)")
        elif roics[0] >= 15:
            score += 2; ev.append(f"🟡 ROIC {roics[0]:.0f}% now but not consistently (+2)")
        elif roics[0] >= 10:
            score += 1; ev.append(f"🟡 ROIC {roics[0]:.0f}% — average business (+1)")
        else:
            ev.append(f"🔴 ROIC {roics[0]:.0f}% — no evidence of moat (+0)")
    if v["fcf_hist"] and v["rev_hist"]:
        fm = v["fcf_hist"][-1] / v["rev_hist"][-1] * 100
        if fm >= 20: score += 2; ev.append(f"🟢 FCF margin {fm:.0f}% — cash machine (+2)")
        elif fm >= 10: score += 1; ev.append(f"🟡 FCF margin {fm:.0f}% (+1)")
        else: ev.append(f"🔴 FCF margin {fm:.0f}% (+0)")
    if v["rev_cagr"] is not None and v["rev_cagr"] >= 0.10:
        score += 2; ev.append(f"🟢 Revenue compounding at {v['rev_cagr']*100:.0f}% — moat is widening, not just defending (+2)")
    rating = "WIDE MOAT" if score >= 8 else ("NARROW MOAT" if score >= 5 else "NO MOAT EVIDENCE")
    return rating, score, ev

# ─────────────────────────────────────────────
# PAGE: DASHBOARD
# ─────────────────────────────────────────────


if page == "🏠 Dashboard":
    st.markdown("""
    <div class="mcis-header">
        <p class="mcis-title">📊 MCIS Dashboard</p>
        <p class="mcis-subtitle">Majid Capital Investment System — Blueprint v1.1</p>
    </div>
    """, unsafe_allow_html=True)

    results = st.session_state.scan_results
    t1 = [r for r in results if r.get("layer")=="LONG_TERM"]
    t2 = [r for r in results if r.get("layer")=="MID_TERM"]
    t3 = [r for r in results if r.get("layer")=="SWING"]

    c1,c2,c3,c4,c5 = st.columns(5)
    with c1:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{len(results)}</div><div class="metric-label">Companies Scanned</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-card tier1-card"><div class="metric-value" style="color:#1b5e20">{len(t1)}</div><div class="metric-label">Tier 1 — Buy</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="metric-card tier2-card"><div class="metric-value" style="color:#006064">{len(t2)}</div><div class="metric-label">Tier 2 — Watch</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="metric-card tier3-card"><div class="metric-value" style="color:#e65100">{len(t3)}</div><div class="metric-label">Tier 3 — Monitor</div></div>', unsafe_allow_html=True)
    with c5:
        st.markdown(f'<div class="metric-card cash-card"><div class="metric-value" style="color:#c9a84c">{len(st.session_state.watchlist)}</div><div class="metric-label">Watchlist</div></div>', unsafe_allow_html=True)

    if st.session_state.last_scan:
        st.caption(f"Last scan: {st.session_state.last_scan}")

    if not results:
        st.markdown("""
        <div class="info-box">
        👆 Go to <b>🔍 Scanner</b> in the sidebar to run your first MCIS market scan.
        The scanner will analyse 300+ companies against MCIS Blueprint v1.1 criteria
        and populate this dashboard with real results.
        </div>
        """, unsafe_allow_html=True)
    else:
        # Important Distinction note (moved up)
        st.markdown("""
        <div style="background-color: #E3F2FD; border-left: 4px solid #1976D2; padding: 15px; margin-bottom: 20px; border-radius: 4px;">
        <b>📌 Important Distinction:</b><br>
        <b>Tier 1 = QUALITY COMPANIES</b> (excellent fundamentals)<br>
        <b>BUT NOT NECESSARILY BUY PRICES</b> (may be overvalued)<br><br>
        ✅ Use this list to find <b>wonderful companies</b><br>
        💰 Use <b>Valuation Engine</b> to find <b>good entry prices</b><br><br>
        Example: MSFT is Tier 1 (quality) but 🔴 AVOID at $390 (overpriced). Target entry: $147
        </div>
        """, unsafe_allow_html=True)

        # ═══════════════════════════════════════════════════════════
        # 🟢 READY TO BUY NOW — ACTION ITEMS
        # ═══════════════════════════════════════════════════════════
        st.markdown('<div class="section-header">🟢 READY TO BUY NOW — Action Items</div>', unsafe_allow_html=True)
        
        buy_now = []
        for r in t1:
            try:
                price = float(r.get("price", 0) or 0)
                target_entry = r.get("target_entry", "N/A")
                
                if target_entry != "N/A" and "-" in target_entry:
                    try:
                        range_str = target_entry.replace("$", "").replace(",", "")
                        low, high = [float(x.strip()) for x in range_str.split("-")]
                        
                        # If current price is at or below target entry = BUY NOW
                        if price <= high:
                            r["buy_signal"] = "🟢 BUY"
                            buy_now.append(r)
                    except:
                        pass
            except:
                pass
        
        if buy_now:
            st.markdown(f"**🎯 {len(buy_now)} companies ready to buy** — within Target Entry range, excellent opportunities!")
            df_buy = results_to_df(sorted(buy_now, key=lambda x: x["score"], reverse=True))
            st.dataframe(df_buy[["Ticker","Company","Score","ROIC%","GM%","Price","Target Entry","Halal"]],
                        use_container_width=True, hide_index=True)
            st.caption("✅ These are your immediate buy candidates. Add to portfolio when capital available.")
        else:
            st.info("⏳ No Tier 1 companies at buy prices right now. Check back after market corrections!")
        
        st.markdown("---")

        # Capital allocation
        st.markdown('<div class="section-header">💰 Capital Allocation — $5,000 Starting Capital</div>', unsafe_allow_html=True)
        alloc_data = {
            "Layer": ["Halal ETF Core","Tier 1 Compounders","Tier 2 Growth","Swing/Tactical","Opportunity Cash"],
            "Allocation": ["30%","25%","20%","5%","20%"],
            "Amount": ["$1,500","$1,250","$1,000","$250","$1,000"],
            "What to Buy": ["SPUS + SPTE + SPWO","Top 3-4 Tier 1 companies","Top 2-3 Tier 2 companies","Options/special situations","Money market — deploy on crash"],
        }
        st.dataframe(pd.DataFrame(alloc_data), use_container_width=True, hide_index=True)

        # ETF ANALYSIS: 5-YEAR PRICE RANGES
        st.markdown('<div class="section-header">💎 Halal ETF Core — 5-Year Price Analysis</div>', unsafe_allow_html=True)
        
        etf_list = ["SPUS", "SPTE", "SPWO"]
        etf_data = []
        
        for ticker in etf_list:
            etf_info = analyze_etf_prices(ticker)
            if etf_info:
                current = etf_info["current"]
                high = etf_info["high"]
                low = etf_info["low"]
                target = etf_info["target"]
                status = etf_info.get("status", "✅ Data")
                
                if current <= target:
                    signal = "🟢 BUY"
                elif current <= (high + low) / 2:
                    signal = "🟡 WAIT"
                else:
                    signal = "🔴 HOLD"
                
                etf_data.append({
                    "ETF": ticker,
                    "Current": f"${current:.2f}",
                    "5Y High": f"${high:.2f}",
                    "5Y Low": f"${low:.2f}",
                    "Target": f"${target:.2f}",
                    "Signal": signal,
                })
        
        if etf_data:
            st.dataframe(pd.DataFrame(etf_data), use_container_width=True, hide_index=True)
            st.caption("💡 Buy at Target price (5-year low with safety margin). Hold until 5-year high.")
        else:
            st.warning("⚠️ ETF data unavailable. Please try again in a moment.")
        
        st.markdown("---")

        # 🏆 ALL TIER 1 COMPANIES WITH SIGNALS
        st.markdown('<div class="section-header">🏆 All Tier 1 Companies — With Signals</div>', unsafe_allow_html=True)
        
        if t1:
            # Add signal to each Tier 1 company
            for r in t1:
                try:
                    price = float(r.get("price", 0) or 0)
                    target_entry = r.get("target_entry", "N/A")
                    
                    if target_entry != "N/A" and "-" in target_entry:
                        try:
                            range_str = target_entry.replace("$", "").replace(",", "")
                            low, high = [float(x.strip()) for x in range_str.split("-")]
                            
                            if price <= high:
                                r["signal"] = "🟢 BUY"
                            elif price <= high * 1.3:
                                r["signal"] = "🟡 WAIT"
                            else:
                                r["signal"] = "🔴 AVOID"
                        except:
                            r["signal"] = "⚠️ ANALYZE"
                    else:
                        r["signal"] = "⚠️ ANALYZE"
                except:
                    r["signal"] = "⚠️ ANALYZE"
            
            # PHASE 1: PILL BUTTON FILTER
            # Initialize session state for signal filter
            if 'selected_signal_tier1' not in st.session_state:
                st.session_state.selected_signal_tier1 = 'All'
            
            # Create pill button filter
            st.markdown("#### 🔍 Filter by Signal")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button('All', key='btn_all_tier1', use_container_width=True):
                    st.session_state.selected_signal_tier1 = 'All'
            
            with col2:
                if st.button('🟢 Buy', key='btn_buy_tier1', use_container_width=True):
                    st.session_state.selected_signal_tier1 = '🟢 BUY'
            
            with col3:
                if st.button('🟡 Wait', key='btn_wait_tier1', use_container_width=True):
                    st.session_state.selected_signal_tier1 = '🟡 WAIT'
            
            with col4:
                if st.button('🔴 Avoid', key='btn_avoid_tier1', use_container_width=True):
                    st.session_state.selected_signal_tier1 = '🔴 AVOID'
            
            st.markdown("---")
            
            # Get sorted list
            sorted_t1 = sorted(t1, key=lambda x: x["score"], reverse=True)[:15]
            
            # Filter based on selected signal
            if st.session_state.selected_signal_tier1 == 'All':
                filtered_t1 = sorted_t1
                st.info(f"📊 Showing: {len(filtered_t1)} Tier 1 companies")
            else:
                filtered_t1 = [r for r in sorted_t1 if r.get("signal") == st.session_state.selected_signal_tier1]
                st.info(f"📊 Showing: {len(filtered_t1)} companies with signal '{st.session_state.selected_signal_tier1}'")
            
            # Display filtered dataframe
            if filtered_t1:
                df_t1 = results_to_df(filtered_t1)
                df_t1["Signal"] = [r.get("signal", "⚠️ ANALYZE") for r in filtered_t1]
                
                st.dataframe(df_t1[["Ticker","Company","Score","ROIC%","GM%","RevCAGR%","Price","Target Entry","Signal","Halal"]],
                            use_container_width=True, hide_index=True)
                st.caption("📊 Tier 1 companies with investment signals. Load in Valuation Engine for detailed analysis.")
            else:
                st.warning(f"No Tier 1 companies found with signal '{st.session_state.selected_signal_tier1}'")
            
        else:
            st.info("No Tier 1 results yet. Run the scanner first.")

        # Fair Value Opportunities Snapshot
        st.markdown('<div class="section-header">💎 Fair Value Opportunities — Quick Glance</div>', unsafe_allow_html=True)
        
        fv_opps = []
        for r in sorted(t1 + t2, key=lambda x: x["score"], reverse=True)[:15]:  # Top 15 by score
            try:
                price = float(r.get("price", 0) or 0)
                fcf = float(r.get("fcf", 0) or 0)
                shares = float(r.get("shares", 0) or 0)
                net_debt = float(r.get("net_debt", 0) or 0)
                m = r.get("metrics", {})
                rev_cagr = float(m.get("rev_cagr", 0) or 0) / 100
                
                if price > 0 and fcf > 100000 and shares > 0 and rev_cagr > 0:
                    wacc, tg = 0.08, 0.025
                    g1 = min(max(rev_cagr, 0.04), 0.25)
                    pv_s1 = sum([fcf * ((1 + g1) ** yr) / ((1 + wacc) ** yr) for yr in range(1, 6)])
                    fcf_yr5 = fcf * ((1 + g1) ** 5)
                    tv = (fcf_yr5 * (1 + tg) / (wacc - tg)) / ((1 + wacc) ** 5)
                    fv_ps = ((pv_s1 + tv) - net_debt) / shares
                    
                    if fv_ps > 1:
                        discount = ((fv_ps - price) / price) * 100
                        fv_opps.append({
                            "Ticker": r["ticker"],
                            "Current Price": f"${price:,.2f}",
                            "Fair Value": f"${fv_ps:,.2f}",
                            "Discount": f"{discount:+.0f}%",
                            "Tier": r.get("verdict", ""),
                        })
            except:
                pass
        
        if fv_opps:
            fv_df = pd.DataFrame(fv_opps).sort_values("Discount", ascending=False)
            st.dataframe(fv_df, use_container_width=True, hide_index=True)
            st.caption("💡 Positive discount = undervalued (buy). Negative = overvalued (avoid)")
        else:
            st.info("Fair Value data will appear here after full company analysis. Go to 📄 Company Dossier for detailed calculations.")

# ─────────────────────────────────────────────
# PAGE: SCANNER
# ─────────────────────────────────────────────

elif page == "🔍 Scanner":
    st.markdown("""
    <div class="mcis-header">
        <p class="mcis-title">🔍 MCIS Scanner</p>
        <p class="mcis-subtitle">Real-time market scanning against Blueprint v1.1 criteria</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="info-box">
    <b>Scanner uses live FMP data.</b> Applies 5 MCIS filters: ROIC>15%, FCF positive+growing,
    Gross Margin>35%, Revenue CAGR>8%, Debt/EBITDA<3x. Also runs Halal check and No Fly Zone screen.
    Takes approximately 15-25 minutes for full universe.
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([2,1])
    with col1:
        scan_mode = st.radio("Scan mode",
            ["Quick scan (curated 70 companies — 5 mins)",
             "Full scan (300+ companies — 25 mins)"],
            horizontal=True)
    with col2:
        custom_tickers = st.text_input("Or scan specific tickers (comma separated)",
                                        placeholder="NVDA, MSFT, AAPL")

    if st.button("🚀 Run MCIS Scanner Now"):
        if custom_tickers.strip():
            universe = [t.strip().upper() for t in custom_tickers.split(",") if t.strip()]
        elif "Quick" in scan_mode:
            universe = CURATED[:70]
        else:
            # Fetch from FMP screener + curated
            universe = list(set(CURATED))
            try:
                screener_urls = [
                    f"{BASE}/company-screener?marketCapMoreThan=200000000&limit=300&apikey={API_KEY}",
                    f"{BASE}/company-screener?marketCapMoreThan=10000000000&limit=200&apikey={API_KEY}",
                ]
                for url in screener_urls:
                    try:
                        r = requests.get(url, timeout=20)
                        data = r.json()
                        if isinstance(data, list) and data:
                            batch = [s.get("symbol") for s in data if s.get("symbol")]
                            universe.extend(batch)
                            break
                    except:
                        pass
                universe = list(set([t for t in universe if t and len(t)<=6]))
            except:
                pass

        t1,t2,t3,rejected,errors = [],[],[],0,0

        progress_bar = st.progress(0)
        status_text  = st.empty()
        results_text = st.empty()

        for i, ticker in enumerate(universe):
            progress = (i+1) / len(universe)
            progress_bar.progress(progress)
            status_text.text(f"Scanning {ticker}... ({i+1}/{len(universe)})")

            try:
                data   = fetch_company(ticker)
                if not data["ok"]:
                    errors += 1
                    continue
                result = run_filters(data)
                
                # Pass through FCF/shares/net_debt from fetch_company to result
                if data.get("fcf"):
                    result["fcf"] = data["fcf"]
                if data.get("shares"):
                    result["shares"] = data["shares"]
                if data.get("net_debt"):
                    result["net_debt"] = data["net_debt"]

                if   result["layer"]=="LONG_TERM": t1.append(result)
                elif result["layer"]=="MID_TERM":  t2.append(result)
                elif result["layer"]=="SWING":     t3.append(result)
                else:                               rejected += 1

                results_text.markdown(
                    f"**Live results:** 🟢 T1: {len(t1)} | 🔵 T2: {len(t2)} | 🟠 T3: {len(t3)} | ❌ Rejected: {rejected}")

            except Exception as e:
                errors += 1
                if i < 3:  # Show first few errors
                    status_text.text(f"⚠️ Error fetching {ticker}: {str(e)[:50]}")

        # Sort by score
        t1.sort(key=lambda x:x["score"],reverse=True)
        t2.sort(key=lambda x:x["score"],reverse=True)
        t3.sort(key=lambda x:x["score"],reverse=True)

        all_results = t1+t2+t3
        st.session_state.scan_results = all_results
        st.session_state.last_scan = datetime.now().strftime("%B %d, %Y at %H:%M")
        save_to_disk()

        status_text.text("✅ Scan complete!")
        progress_bar.progress(1.0)

        st.success(f"Scan complete: {len(universe)} companies scanned | "
                   f"Tier 1: {len(t1)} | Tier 2: {len(t2)} | Tier 3: {len(t3)} | "
                   f"Rejected: {rejected} | Errors: {errors}")

        if t1:
            st.markdown('<div class="section-header">🏆 Tier 1 Results — Buy Candidates</div>', unsafe_allow_html=True)
            st.dataframe(results_to_df(t1)[["Ticker","Company","Sector","Score","ROIC%","GM%","RevCAGR%","Halal","Price"]],
                        use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────
# PAGE: RANKINGS
# ─────────────────────────────────────────────

elif page == "📊 Rankings":
    st.markdown("""
    <div class="mcis-header">
        <p class="mcis-title">📊 MCIS Rankings</p>
        <p class="mcis-subtitle">All scanned companies ranked by MCIS Score</p>
    </div>
    """, unsafe_allow_html=True)

    results = st.session_state.scan_results
    if not results:
        st.markdown('<div class="warning-box">No scan results yet. Go to 🔍 Scanner and run a scan first.</div>',
                    unsafe_allow_html=True)
    else:
        col1,col2,col3 = st.columns(3)
        with col1:
            tier_filter = st.multiselect("Filter by Tier",
                ["TIER 1","TIER 2","TIER 3"],
                default=["TIER 1","TIER 2","TIER 3"])
        with col2:
            halal_filter = st.multiselect("Filter by Halal",
                ["PASS","CONDITIONAL","FAIL"],
                default=["PASS","CONDITIONAL"])
        with col3:
            sector_filter = st.multiselect("Filter by Sector",
                list(set(r["sector"] for r in results if r["sector"]!="Unknown")))

        filtered = [r for r in results
                    if r.get("verdict","") in tier_filter
                    and r.get("halal","") in halal_filter
                    and (not sector_filter or r.get("sector","") in sector_filter)]

        filtered.sort(key=lambda x:x["score"],reverse=True)

        st.caption(f"Showing {len(filtered)} of {len(results)} companies")

        if filtered:
            df = results_to_df(filtered)
            st.dataframe(df, use_container_width=True, hide_index=True,
                        column_config={
                            "Score": st.column_config.ProgressColumn("Score",min_value=0,max_value=100),
                        })

            # Add to watchlist
            st.markdown("---")
            ticker_to_add = st.text_input("Add company to watchlist (enter ticker)")
            if st.button("➕ Add to Watchlist") and ticker_to_add:
                match = next((r for r in filtered if r["ticker"]==ticker_to_add.upper()), None)
                if match and match not in st.session_state.watchlist:
                    st.session_state.watchlist.append(match)
                    st.success(f"{ticker_to_add.upper()} added to watchlist")

# ─────────────────────────────────────────────
# PAGE: COMPANY LOOKUP
# ─────────────────────────────────────────────

elif page == "🔎 Company Lookup":
    st.markdown("""
    <div class="mcis-header">
        <p class="mcis-title">🔎 Company Lookup</p>
        <p class="mcis-subtitle">Deep dive MCIS analysis on any company</p>
    </div>
    """, unsafe_allow_html=True)

    # Get available tickers from scan results
    available_tickers = sorted(set([r["ticker"] for r in st.session_state.scan_results]))
    
    col1, col2 = st.columns([2, 1])
    with col1:
        if available_tickers:
            ticker_input = st.selectbox(
                "Select company or type ticker",
                [""] + available_tickers,
                index=0,
                key="lookup_ticker_select"
            )
            if not ticker_input:
                ticker_input = st.text_input("Or enter ticker manually", placeholder="e.g. NVDA").upper().strip()
        else:
            ticker_input = st.text_input("Enter ticker symbol", placeholder="e.g. NVDA").upper().strip()
            st.caption("💡 Run the Scanner first to populate the dropdown")
    
    with col2:
        st.empty()  # Spacer

    if st.button("🔍 Analyse Company") and ticker_input:
        with st.spinner(f"Fetching live data for {ticker_input}..."):
            data = fetch_company(ticker_input)

        if not data["ok"]:
            st.error(f"Could not fetch data for {ticker_input}. Check the ticker symbol.")
        else:
            result = run_filters(data)
            m      = result.get("metrics",{})

            # Header
            col1, col2 = st.columns([3,1])
            with col1:
                st.subheader(f"{result['ticker']} — {result['name']}")
                st.caption(f"{result['sector']} | {data.get('industry','')}")
            with col2:
                verdict = result["verdict"]
                if "TIER 1" in verdict: st.success(f"✅ {verdict}")
                elif "TIER 2" in verdict: st.info(f"🔵 {verdict}")
                elif "TIER 3" in verdict: st.warning(f"🟠 {verdict}")
                else: st.error(f"❌ {verdict}")

            # Key metrics
            st.markdown('<div class="section-header">Key Metrics</div>', unsafe_allow_html=True)
            c1,c2,c3,c4,c5,c6 = st.columns(6)
            c1.metric("MCIS Score", f"{result['score']}/100")
            c2.metric("ROIC",       f"{m.get('roic','N/A')}%")
            c3.metric("Gross Margin",f"{m.get('gm','N/A')}%")
            c4.metric("Rev CAGR",   f"{m.get('rev_cagr','N/A')}%")
            c5.metric("Debt/EBITDA",f"{m.get('debt_ebitda','N/A')}x")
            c6.metric("P/E Ratio",  f"{m.get('pe','N/A')}")

            c1,c2,c3 = st.columns(3)
            c1.metric("Price",     f"${result['price']:,.2f}")
            c2.metric("Market Cap",fmt_mktcap(result.get("mktcap",0)))
            c3.metric("EV/EBITDA", f"{m.get('ev_ebitda','N/A')}")

            # Halal status
            st.markdown('<div class="section-header">Halal Status</div>', unsafe_allow_html=True)
            h = result.get("halal","?")
            if   h=="PASS":        st.success(f"✅ HALAL PASS — {result['halal_reason']}")
            elif h=="CONDITIONAL": st.warning(f"⚠️ CONDITIONAL — {result['halal_reason']} — Verify on Zoya (zoya.finance)")
            else:                  st.error(f"❌ HALAL FAIL — {result['halal_reason']}")

            # 5-Year Price Chart
            st.markdown('<div class="section-header">📈 5-Year Price History</div>', unsafe_allow_html=True)
            with st.spinner(f"Fetching price data for {ticker_input}..."):
                prices = fetch_historical_prices_yahoo(ticker_input)
            
            if prices and len(prices) > 10:
                fig = plot_5year_price_chart_yahoo(prices, ticker_input, data.get("price"))
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Chart unavailable")
            else:
                with st.expander("🔧 Troubleshooting: Why no price history?"):
                    st.warning(f"⚠️ FMP historical-price-full endpoint not returning data for {ticker_input}")
                    st.caption("""
                    **Possible reasons:**
                    - Endpoint not available on your current FMP plan (verify in FMP dashboard)
                    - API key needs to fully activate (wait 15 minutes)
                    - Ticker symbol issue (verify ticker exists)
                    
                    **Current price from FMP:** $""" + str(data.get('price', 'N/A')) + """
                    
                    Check: Go to FMP dashboard → test historical-price-full endpoint manually
                    """)
                st.info(f"Current price from FMP: ${data.get('price', 'N/A')}")

            # Data Validation
            st.markdown('<div class="section-header">🔍 Data Quality Check</div>', unsafe_allow_html=True)
            validation = validate_financial_data(data, result)
            st.caption(f"FMP Data Quality: {validation['quality_badge']}")
            if validation['flags']:
                for flag in validation['flags']:
                    st.warning(flag)
            else:
                st.success("✓ No data quality issues detected")

            # Filter results
            col1, col2 = st.columns(2)
            with col1:
                st.markdown('<div class="section-header">✅ Passed Filters</div>', unsafe_allow_html=True)
                for p in result["passed"]:
                    st.success(f"✓ {p}")
                if not result["passed"]:
                    st.info("No filters passed")

            with col2:
                st.markdown('<div class="section-header">❌ Failed Filters</div>', unsafe_allow_html=True)
                for f in result["failed"]:
                    st.error(f"✗ {f}")
                for w in result["warnings"]:
                    st.warning(f"⚠ {w}")

            # Add to watchlist
            if st.button(f"➕ Add {ticker_input} to Watchlist"):
                if result not in st.session_state.watchlist:
                    st.session_state.watchlist.append(result)
                    st.success(f"{ticker_input} added to watchlist")

# ─────────────────────────────────────────────
# PAGE: WATCHLIST
# ─────────────────────────────────────────────

elif page == "📋 Watchlist":
    st.markdown("""
    <div class="mcis-header">
        <p class="mcis-title">📋 MCIS Watchlist</p>
        <p class="mcis-subtitle">Tier 1 companies at buy prices + manual adds</p>
    </div>
    """, unsafe_allow_html=True)

    watchlist = st.session_state.watchlist

    # AUTO-WATCHLIST: Add Tier 1 companies within Target Entry range
    auto_buy_candidates = []
    try:
        scan_results = st.session_state.get("scan_results", [])
        for r in scan_results:
            if r.get("verdict") == "TIER 1":
                price = float(r.get("price", 0) or 0)
                # Parse Target Entry range
                target_entry = r.get("target_entry", "N/A")
                if target_entry != "N/A" and "-" in target_entry:
                    try:
                        range_str = target_entry.replace("$", "").replace(",", "")
                        low, high = [float(x.strip()) for x in range_str.split("-")]
                        # If current price is within or below target entry range = BUY
                        if price <= high:
                            r["buy_signal"] = f"🟢 BUY at ${price:,.2f}"
                            auto_buy_candidates.append(r)
                    except:
                        pass
    except:
        pass

    if auto_buy_candidates:
        st.markdown('<div class="section-header">🟢 Auto-Buy Candidates — Tier 1 at Target Entry</div>', unsafe_allow_html=True)
        st.markdown(f"**{len(auto_buy_candidates)} companies ready to buy** (within Target Entry range)")
        
        df_auto = results_to_df(auto_buy_candidates)
        st.dataframe(df_auto[["Ticker","Company","Score","Tier","ROIC%","GM%","Price","Target Entry","Halal"]],
                    use_container_width=True, hide_index=True)
        
        st.caption("💡 These Tier 1 companies are at or below your Target Entry price. Perfect entry points.")

    # MANUAL ADDITIONS
    st.markdown('<div class="section-header">➕ Manual Watchlist</div>', unsafe_allow_html=True)
    
    # Add manually
    col1,col2 = st.columns([3,1])
    with col1:
        new_ticker = st.text_input("Add ticker to watchlist", placeholder="e.g. ASML").upper().strip()
    with col2:
        st.markdown("<br>",unsafe_allow_html=True)
        if st.button("➕ Add") and new_ticker:
            with st.spinner(f"Fetching {new_ticker}..."):
                data   = fetch_company(new_ticker)
                result = run_filters(data) if data["ok"] else {"ticker":new_ticker,"name":new_ticker,"score":0,"verdict":"Unknown","layer":"UNKNOWN","halal":"?","halal_reason":"","passed":[],"failed":[],"warnings":[],"metrics":{},"price":0,"mktcap":0,"sector":"Unknown"}
                if result not in watchlist:
                    st.session_state.watchlist.append(result)
                    st.success(f"{new_ticker} added")

    if not watchlist:
        st.markdown('<div class="info-box">Your manual watchlist is empty. Add companies from Rankings or Company Lookup.</div>', unsafe_allow_html=True)
    else:
        st.caption(f"{len(watchlist)} companies on manual watchlist")
        df = results_to_df(watchlist)
        st.dataframe(df[["Ticker","Company","Sector","Score","Tier","ROIC%","GM%","RevCAGR%","Halal","Price","Target Entry"]],
                    use_container_width=True, hide_index=True,
                    column_config={"Score": st.column_config.ProgressColumn("Score",min_value=0,max_value=100)})

        # Remove from watchlist
        to_remove = st.text_input("Remove ticker from watchlist").upper().strip()
        if st.button("➖ Remove") and to_remove:
            st.session_state.watchlist = [r for r in watchlist if r["ticker"]!=to_remove]
            st.success(f"{to_remove} removed")

# ─────────────────────────────────────────────
# PAGE: SWING TRADES
# ─────────────────────────────────────────────

elif page == "⚡ Swing Trades":
    st.markdown("""
    <div class="mcis-header">
        <p class="mcis-title">⚡ Swing Trades</p>
        <p class="mcis-subtitle">Layer 4 — Tactical positions with strict stop losses</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="warning-box">
    <b>MCIS Rules:</b> Maximum 3% per trade | Maximum 5% total swing exposure |
    Stop loss at 50% of premium or 8-10% of stock | Exit at 30 days if no movement |
    Define entry, target and stop loss BEFORE opening any position.
    </div>
    """, unsafe_allow_html=True)

    # Add new swing trade
    st.markdown('<div class="section-header">➕ Add New Swing Trade</div>', unsafe_allow_html=True)
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    with c1: sw_ticker = st.text_input("Ticker").upper()
    with c2: sw_type   = st.selectbox("Type", ["Call Option","Put Option","Long Stock","Short Stock"])
    with c3: sw_entry  = st.number_input("Entry Price $",min_value=0.0,step=0.01)
    with c4: sw_target = st.number_input("Target Price $",min_value=0.0,step=0.01)
    with c5: sw_stop   = st.number_input("Stop Loss $",min_value=0.0,step=0.01)
    with c6: sw_size   = st.number_input("Position Size $",min_value=0.0,step=10.0)

    sw_thesis = st.text_area("Trade Thesis (required)", placeholder="Why are you entering this trade? What is the catalyst?")
    sw_expiry = st.date_input("Expiry / Exit by Date")

    if st.button("➕ Add Swing Trade"):
        if sw_ticker and sw_entry and sw_target and sw_stop and sw_thesis:
            trade = {
                "ticker":  sw_ticker,
                "type":    sw_type,
                "entry":   sw_entry,
                "target":  sw_target,
                "stop":    sw_stop,
                "size":    sw_size,
                "thesis":  sw_thesis,
                "expiry":  str(sw_expiry),
                "date":    datetime.now().strftime("%Y-%m-%d"),
                "status":  "Open",
                "rr_ratio":round((sw_target-sw_entry)/(sw_entry-sw_stop),2) if sw_entry!=sw_stop else 0,
            }
            st.session_state.swing_trades.append(trade)
            st.success(f"Swing trade added for {sw_ticker}")
        else:
            st.error("Please fill in all fields including thesis before adding")

    # Show open trades
    if st.session_state.swing_trades:
        st.markdown('<div class="section-header">📊 Open Swing Trades</div>', unsafe_allow_html=True)
        df = pd.DataFrame(st.session_state.swing_trades)
        st.dataframe(df[["ticker","type","entry","target","stop","size","rr_ratio","expiry","status","thesis"]],
                    use_container_width=True, hide_index=True)

        # Daily checklist
        st.markdown('<div class="section-header">✅ Daily Swing Trade Checklist</div>', unsafe_allow_html=True)
        checks = [
            "Has any position hit its stop loss level? → Exit immediately if yes",
            "Has any position hit 50% profit target? → Take half off the table",
            "Has any position been open 30 days without movement? → Exit and redeploy",
            "Has the original thesis changed for any position? → Exit regardless of P&L",
            "Is IV crush approaching on any options? → Exit before earnings if not an earnings play",
        ]
        for check in checks:
            st.checkbox(check)
    else:
        st.info("No swing trades open. Add your first trade above.")

# ─────────────────────────────────────────────
# PAGE: QUARTERLY REVIEW
# ─────────────────────────────────────────────

elif page == "📅 Quarterly Review":
    st.markdown("""
    <div class="mcis-header">
        <p class="mcis-title">📅 Quarterly Review</p>
        <p class="mcis-subtitle">MCIS Blueprint v1.1 — 8-Step Review Process</div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="info-box">
    Run this review every quarter — January, April, July, October.
    Takes approximately 2-3 hours. Produces a written summary for the Investment Committee.
    </div>
    """, unsafe_allow_html=True)

    review_date = st.date_input("Review Date", value=datetime.now())

    steps = [
        ("Step 1 — ETF Health Check",
         "Confirm each ETF still tracks correct index, still halal compliant, competitive fees.",
         ["SPUS still halal compliant?","SPTE still tracking correct index?","SPWO fees still competitive?","Any ETF methodology changes?"]),
        ("Step 2 — Individual Company Fundamentals",
         "Pull latest quarterly earnings. Check revenue growth, ROIC, FCF, management commentary.",
         ["Revenue growth holding above 8%?","ROIC still above 15%?","FCF still positive and growing?","Management commentary consistent with thesis?"]),
        ("Step 3 — Valuation Update",
         "Update DCF for each holding. Recalculate margin of safety.",
         ["DCF updated with latest numbers?","Margin of safety still above 20%?","Any positions stretched above intrinsic value?"]),
        ("Step 4 — Portfolio Weight Check",
         "Check no position exceeds limits. Trim if required.",
         ["Any single stock above 15% of portfolio?","Any single ETF above 20% of portfolio?","Any single sector above 35%?"]),
        ("Step 5 — Watchlist Ranking Update",
         "Update Tier rankings. Promote or demote based on latest data.",
         ["Tier 1 list updated with latest scan?","Any Tier 2 companies ready for promotion?","Any Tier 1 companies showing deterioration?"]),
        ("Step 6 — Opportunity Cash Review",
         "Has market created any dislocation worth deploying cash into?",
         ["Market down 15%+ since last review?","Any specific Tier 1 company down 20%+ with thesis intact?","Opportunity cash still at 10-20% minimum?"]),
        ("Step 7 — Swing Trade Review",
         "Close or roll any swing positions older than 30 days without movement.",
         ["Any open swings older than 30 days?","Any swings near stop loss?","Swing allocation still within 5% limit?"]),
        ("Step 8 — Written Summary",
         "CIO produces one-page summary. Chairman reviews and approves.",
         ["Summary written?","Chairman reviewed?","Next review date set?"]),
    ]

    all_complete = True
    for step_title, step_desc, checks in steps:
        with st.expander(step_title):
            st.caption(step_desc)
            for check in checks:
                result = st.checkbox(check, key=f"{step_title}_{check}")
                if not result:
                    all_complete = False

    st.markdown("---")
    verdict_col, notes_col = st.columns(2)
    with verdict_col:
        st.markdown("**Quarterly Verdict for each holding:**")
        for holding in ["SPUS","SPTE","SPWO"] + [r["ticker"] for r in st.session_state.watchlist[:5]]:
            v = st.selectbox(f"{holding}", ["HOLD","ADD","WATCH","TRIM","EXIT","REVIEW"],key=f"verdict_{holding}")

    with notes_col:
        st.markdown("**Committee Notes:**")
        notes = st.text_area("", height=200, placeholder="Key observations, decisions and actions from this quarterly review...")

    if st.button("✅ Complete Quarterly Review"):
        if all_complete:
            st.success(f"✅ Quarterly Review completed — {review_date.strftime('%B %d, %Y')}")
            st.balloons()
        else:
            st.warning("Some checklist items are incomplete. Review them before finalising.")

# ═════════════════════════════════════════════
# COMPANY DOSSIER PDF GENERATOR
# Professional 2-page institutional dossier
# ═════════════════════════════════════════════

def _format_number(v, fmt=".0f"):
    """Format large numbers for readability."""
    if not v or v == 0: return "—"
    if abs(v) >= 1e9: return f"${v/1e9:.1f}B"
    if abs(v) >= 1e6: return f"${v/1e6:.1f}M"
    if abs(v) >= 1e3: return f"${v/1e3:.1f}K"
    return f"${v:,.0f}"

def _pct(v):
    """Format as percentage."""
    if v is None or v == "N/A": return "—"
    return f"{float(v)*100:.1f}%" if isinstance(v, (int, float)) else "—"

def _tbl_rows(d, keys, years=5):
    """Extract historical data for a table row."""
    h = d.get(keys[0], [])
    if not isinstance(h, list): h = [h] if h else []
    h = list(reversed(h))[:years]
    # Pad with empty if less than years available
    while len(h) < years: h.insert(0, {})
    return h

def generate_dossier_pdf(ticker, d, v, result, buffett_checks, buffett_score, lynch_cat, 
                         lynch_note, lynch_peg, moat_rating, moat_score, 
                         cio_recommendation, investment_edge, risks_text):
    """Generate a professional 2-page MCIS Company Dossier PDF."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from datetime import datetime
    
    output_path = f"/tmp/{ticker}_dossier.pdf"
    doc = SimpleDocTemplate(output_path, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch,
                            leftMargin=0.6*inch, rightMargin=0.6*inch)
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    t_header = ParagraphStyle('CustomHeader', parent=styles['Heading1'],
                              fontSize=16, textColor=colors.HexColor('#1a3c5e'),
                              spaceAfter=2, fontName='Helvetica-Bold')
    t_subhdr = ParagraphStyle('CustomSubHeader', parent=styles['Heading2'],
                              fontSize=11, textColor=colors.HexColor('#1a3c5e'),
                              spaceAfter=6, spaceBefore=6, fontName='Helvetica-Bold')
    t_normal = ParagraphStyle('CustomNormal', parent=styles['Normal'],
                              fontSize=9, alignment=TA_LEFT, spaceAfter=3)
    t_small  = ParagraphStyle('CustomSmall', parent=styles['Normal'],
                              fontSize=8, textColor=colors.HexColor('#666666'), spaceAfter=2)
    
    # ═══════════════════════════════════════════
    # PAGE 1 — FINANCIAL SNAPSHOT
    # ═══════════════════════════════════════════
    
    # Header
    story.append(Paragraph(f"<b>{ticker} — {d.get('name','')}</b>", t_header))
    story.append(Paragraph(f"{d.get('sector','')} | {d.get('industry','')} | "
                           f"Price ${v['price']:,.2f} | Market Cap {fmt_mktcap(v['mktcap'])}",
                           t_small))
    story.append(Spacer(1, 0.15*inch))
    
    # 1. Income Statement (5 years) — CURRENT YEAR AND 4 PRIOR YEARS
    from datetime import datetime
    current_year = datetime.now().year
    years_header = [str(current_year - 4 + i) for i in range(5)]  # e.g., 2022, 2023, 2024, 2025, 2026
    
    story.append(Paragraph("INCOME STATEMENT (5 YEARS)", t_subhdr))
    inc = _tbl_rows(d, ['income6', 'income'], years=5)
    inc_rows = [["Metric"] + years_header]
    
    for label, key, fmt_fn in [
        ("Revenue", "revenue", lambda x: _format_number(x)),
        ("Revenue Growth %", "__rev_cagr__", lambda x: "—"),
        ("Gross Profit", "grossProfit", lambda x: _format_number(x)),
        ("Gross Margin %", "__gm_pct__", lambda x: _pct(x)),
        ("Operating Income", "operatingIncome", lambda x: _format_number(x)),
        ("Operating Margin %", "__op_margin_pct__", lambda x: _pct(x)),
        ("Net Income", "netIncome", lambda x: _format_number(x)),
        ("Net Margin %", "__nm_pct__", lambda x: _pct(x)),
        ("EPS", "eps", lambda x: f"${float(x):.2f}" if x else "—"),
    ]:
        row = [label]
        for i, yr in enumerate(inc):
            if key == "__rev_cagr__":
                if i == 4 and v.get("rev_cagr"):
                    row.append(f"{v['rev_cagr']*100:.1f}%")
                else:
                    row.append("—")
            elif key == "__gm_pct__":
                # Calculate Gross Margin % = Gross Profit / Revenue
                rev = yr.get("revenue")
                gp = yr.get("grossProfit")
                if rev and gp and rev > 0:
                    gm_pct = (float(gp) / float(rev)) * 100
                    row.append(f"{gm_pct:.1f}%")
                else:
                    row.append("—")
            elif key == "__op_margin_pct__":
                # Calculate Operating Margin % = Operating Income / Revenue
                rev = yr.get("revenue")
                oi = yr.get("operatingIncome")
                if rev and oi and rev > 0:
                    om_pct = (float(oi) / float(rev)) * 100
                    row.append(f"{om_pct:.1f}%")
                else:
                    row.append("—")
            elif key == "__nm_pct__":
                # Calculate Net Margin % = Net Income / Revenue
                rev = yr.get("revenue")
                ni = yr.get("netIncome")
                if rev and ni and rev > 0:
                    nm_pct = (float(ni) / float(rev)) * 100
                    row.append(f"{nm_pct:.1f}%")
                else:
                    row.append("—")
            else:
                val = yr.get(key)
                row.append(fmt_fn(val) if val else "—")
        inc_rows.append(row)
    
    inc_tbl = Table(inc_rows, colWidths=[1.3*inch, 0.95*inch, 0.95*inch, 0.95*inch, 0.95*inch, 0.95*inch])
    inc_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a3c5e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
        ('TOPPADDING', (0, 0), (-1, 0), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
    ]))
    story.append(inc_tbl)
    story.append(Spacer(1, 0.1*inch))
    
    # 2. Cash Flow Statement (5 years)
    story.append(Paragraph("CASH FLOW STATEMENT (5 YEARS)", t_subhdr))
    cf = _tbl_rows(d, ['cashflow6', 'cashflow'], years=5)
    cf_rows = [["Metric"] + years_header]
    for label, key in [
        ("Operating Cash Flow", "operatingCashFlow"),
        ("Capital Expenditure", "capitalExpenditure"),
        ("Free Cash Flow", "freeCashFlow"),
        ("FCF Margin %", "__fcf_margin__"),
    ]:
        row = [label]
        for i, yr in enumerate(cf):
            if key == "__fcf_margin__":
                if v.get("rev_hist") and v.get("fcf_hist") and i < len(v["fcf_hist"]):
                    fm = v["fcf_hist"][i] / v["rev_hist"][i] * 100 if v["rev_hist"][i] > 0 else 0
                    row.append(f"{fm:.1f}%")
                else: row.append("—")
            else:
                val = yr.get(key)
                row.append(_format_number(val) if val else "—")
        cf_rows.append(row)
    
    cf_tbl = Table(cf_rows, colWidths=[1.3*inch, 0.95*inch, 0.95*inch, 0.95*inch, 0.95*inch, 0.95*inch])
    cf_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a3c5e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
        ('TOPPADDING', (0, 0), (-1, 0), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
    ]))
    story.append(cf_tbl)
    story.append(Spacer(1, 0.1*inch))
    
    # 3. Balance Sheet (5 years)
    story.append(Paragraph("BALANCE SHEET & CAPITAL STRUCTURE (5 YEARS)", t_subhdr))
    bal = _tbl_rows(d, ['balance'], years=5)
    bal_rows = [["Metric"] + years_header]
    for label, key in [
        ("Cash & Equivalents", "cashAndShortTermInvestments"),
        ("Total Debt", "totalDebt"),
        ("Net Debt", "__net_debt__"),
        ("Shareholders' Equity", "totalStockholdersEquity"),
        ("Shares Outstanding (M)", "commonStockSharesIssued"),
    ]:
        row = [label]
        for i, yr in enumerate(bal):
            if key == "__net_debt__":
                row.append(_format_number(v.get("net_debt")) if i == 0 else "—")
            elif key == "commonStockSharesIssued":
                val = yr.get(key)
                row.append(f"{float(val)/1e6:.0f}M" if val else "—")
            else:
                val = yr.get(key)
                row.append(_format_number(val) if val else "—")
        bal_rows.append(row)
    
    bal_tbl = Table(bal_rows, colWidths=[1.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch])
    bal_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a3c5e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
        ('TOPPADDING', (0, 0), (-1, 0), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
    ]))
    story.append(bal_tbl)
    story.append(Spacer(1, 0.1*inch))
    
    # 4. Key Ratios
    story.append(Paragraph("KEY FINANCIAL RATIOS", t_subhdr))
    m = result.get("metrics", {})
    ratio_rows = [
        ["ROIC", f"{m.get('roic','N/A')}%"],
        ["Gross Margin", f"{m.get('gm','N/A')}%"],
        ["Net Margin", f"{m.get('nm','N/A')}%" if 'nm' in m else "—"],
        ["FCF Margin", f"{m.get('fcf_margin','N/A')}%"],
        ["Debt/EBITDA", f"{m.get('debt_ebitda','N/A')}x"],
        ["P/E Ratio", f"{m.get('pe','N/A')}x"],
        ["EV/EBITDA", f"{m.get('ev_ebitda','N/A')}x"],
    ]
    ratio_tbl = Table(ratio_rows, colWidths=[2*inch, 2*inch])
    ratio_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(ratio_tbl)
    story.append(Spacer(1, 0.1*inch))
    
    # 5. Price Section
    story.append(Paragraph("PRICE & VALUATION METRICS", t_subhdr))
    
    # Calculate Fair Value (DCF base case)
    fv_per_share = "N/A"
    margin_of_safety = "N/A"
    try:
        if v.get("fcf0", 0) > 0 and v.get("shares", 0) > 0:
            fcf0 = v["fcf0"]
            shares = v["shares"]
            price = v["price"]
            wacc = 0.08
            tg = 0.025
            g1 = min(max(v.get("rev_cagr", 0.10), 0.04), 0.25)
            
            # 2-stage DCF
            pv_stage1 = sum([fcf0 * ((1 + g1) ** yr) / ((1 + wacc) ** yr) for yr in range(1, 6)])
            fcf_year5 = fcf0 * ((1 + g1) ** 5)
            fcf_year6 = fcf_year5 * (1 + tg)
            tv = (fcf_year6 / (wacc - tg)) / ((1 + wacc) ** 5)
            total_pv = pv_stage1 + tv
            equity_value = total_pv - v.get("net_debt", 0)
            fv_ps = equity_value / shares if shares > 0 else 0
            
            if fv_ps > 0:
                fv_per_share = f"${fv_ps:,.2f}"
                mos = ((fv_ps - price) / price) * 100 if price > 0 else 0
                margin_of_safety = f"{mos:+.1f}%"
    except:
        pass
    
    price_info = [
        ["Current Price", f"${v['price']:,.2f}"],
        ["Fair Value (DCF)", fv_per_share],
        ["Margin of Safety", margin_of_safety],
        ["Market Cap", fmt_mktcap(v['mktcap'])],
        ["MCIS Score", f"{result['score']}/100"],
        ["MCIS Verdict", result['verdict']],
        ["Halal Status", result.get('halal','?')],
    ]
    price_tbl = Table(price_info, colWidths=[2*inch, 2*inch])
    price_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(price_tbl)
    
    # Page break
    story.append(PageBreak())
    
    # ═══════════════════════════════════════════
    # PAGE 2 — INVESTMENT ANALYSIS (CIO PAGE)
    # ═══════════════════════════════════════════
    
    story.append(Paragraph(f"<b>INVESTMENT ANALYSIS — {ticker}</b>", t_header))
    story.append(Spacer(1, 0.1*inch))
    
    # 1. Valuation
    story.append(Paragraph("VALUATION FRAMEWORK", t_subhdr))
    val_data = [
        ["DCF (Base Case)", "See Valuation Engine for full model"],
        ["Reverse DCF", "Market growth expectations embedded in price"],
        ["Historical P/E", f"{m.get('pe','N/A')}x"],
        ["Historical EV/EBITDA", f"{m.get('ev_ebitda','N/A')}x"],
        ["PEG Ratio", f"{lynch_peg:.2f}" if lynch_peg else "N/A"],
        ["Margin of Safety", "See Valuation Engine"],
    ]
    val_tbl = Table(val_data, colWidths=[2*inch, 2.5*inch])
    val_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(val_tbl)
    story.append(Spacer(1, 0.1*inch))
    
    # 2. Buffett Quality Test
    story.append(Paragraph("BUFFETT QUALITY TEST (10 CHECKS)", t_subhdr))
    story.append(Paragraph(f"<b>Score: {buffett_score}/10</b> | " +
                           ("WONDERFUL COMPANY" if buffett_score >= 8 else
                            "GOOD COMPANY" if buffett_score >= 6 else
                            "AVERAGE" if buffett_score >= 4 else "AVOID"),
                           t_normal))
    for c in buffett_checks:
        symbol = "✓" if c["ok"] else "✗"
        story.append(Paragraph(f"<b>{symbol} {c['check']}</b> — {c['detail']}", t_small))
    story.append(Spacer(1, 0.08*inch))
    
    # 3. Peter Lynch Classification
    story.append(Paragraph("PETER LYNCH CLASSIFICATION", t_subhdr))
    story.append(Paragraph(f"<b>{lynch_cat}</b>", t_normal))
    story.append(Paragraph(lynch_note, t_small))
    story.append(Spacer(1, 0.08*inch))
    
    # 4. Moat Assessment
    story.append(Paragraph("COMPETITIVE MOAT", t_subhdr))
    story.append(Paragraph(f"<b>{moat_rating} ({moat_score}/10)</b>", t_normal))
    story.append(Spacer(1, 0.08*inch))
    
    # 5. Risks (from input)
    story.append(Paragraph("MATERIAL RISKS", t_subhdr))
    if risks_text:
        for line in risks_text.split("\n")[:5]:
            if line.strip():
                story.append(Paragraph(f"• {line.strip()}", t_small))
    else:
        story.append(Paragraph("• No risks documented", t_small))
    story.append(Spacer(1, 0.08*inch))
    
    # 6. Investment Edge
    story.append(Paragraph("INVESTMENT EDGE", t_subhdr))
    if investment_edge:
        story.append(Paragraph(investment_edge, t_small))
    else:
        story.append(Paragraph("[Investment edge not yet documented]", t_small))
    story.append(Spacer(1, 0.08*inch))
    
    # 7. CIO Recommendation
    story.append(Paragraph("CIO RECOMMENDATION", t_subhdr))
    rec_color = colors.HexColor('#1b5e20') if cio_recommendation == "BUY" else \
                colors.HexColor('#006064') if cio_recommendation == "HOLD" else \
                colors.HexColor('#e65100') if cio_recommendation == "WATCH" else colors.HexColor('#b71c1c')
    story.append(Paragraph(f"<font color='#{'1b5e20' if cio_recommendation == 'BUY' else '006064' if cio_recommendation == 'HOLD' else 'e65100' if cio_recommendation == 'WATCH' else 'b71c1c'}'><b>{cio_recommendation}</b></font>",
                           t_normal))
    story.append(Spacer(1, 0.08*inch))
    
    # 8. Capital Allocation
    story.append(Paragraph("PORTFOLIO ALLOCATION", t_subhdr))
    story.append(Paragraph("[To be determined by CIO based on position sizing framework]", t_small))
    story.append(Spacer(1, 0.15*inch))
    
    # Footer
    story.append(Paragraph(f"MCIS Company Dossier | Generated {datetime.now().strftime('%B %d, %Y')} | "
                           "Blueprint v1.1 | Not investment advice",
                           ParagraphStyle('Footer', parent=styles['Normal'], fontSize=7,
                                         textColor=colors.HexColor('#999999'), alignment=TA_CENTER)))
    
    doc.build(story)
    return output_path

# ─────────────────────────────────────────────
# PAGE: COMPANY DOSSIER
# ─────────────────────────────────────────────

if page == "📄 Company Dossier":
    st.markdown("""
    <div class="mcis-header">
        <p class="mcis-title">📄 Company Dossier</p>
        <p class="mcis-subtitle">Professional 2-page institutional investment thesis — for Investment Committee review</p>
    </div>
    """, unsafe_allow_html=True)

    # Load company data
    c1, c2 = st.columns([3, 1])
    with c1:
        dos_ticker = st.text_input("Enter ticker", placeholder="e.g. NVDA", key="dos_ticker").upper().strip()
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        load_dos = st.button("📥 Load")

    if load_dos and dos_ticker:
        with st.spinner(f"Fetching data for {dos_ticker}..."):
            vd = fetch_valuation_data(dos_ticker)
        if not vd.get("ok"):
            st.error(f"Could not fetch data for {dos_ticker}.")
        else:
            st.session_state["dossier_data"] = vd

    vd = st.session_state.get("dossier_data")
    if vd and vd.get("ok"):
        v = _val_inputs(vd)
        result = run_filters(vd)
        m = result.get("metrics", {})
        pe = m.get("pe")

        st.subheader(f"{vd['ticker']} — {vd.get('name','')}")
        
        # ═══════════════════════════════════════════
        # AUTOMATIC BUY/HOLD/AVOID SIGNAL
        # ═══════════════════════════════════════════
        
        # Calculate base case fair value
        fcf0 = v.get("fcf0", 0)
        shares = v.get("shares", 0)
        net_debt = v.get("net_debt", 0)
        price = v.get("price", 0)
        wacc = 0.08
        tg = 0.025
        g1_base = min(max(v.get("rev_cagr", 0.10), 0.04), 0.25)
        mos_req = 50  # Default 50% margin of safety requirement
        
        auto_signal = "⚠️ ANALYZE"
        signal_color = "#FFA500"  # Orange
        signal_detail = "Insufficient data for automatic signal"
        
        if fcf0 > 0 and shares > 0 and price > 0:
            try:
                # DCF calculation
                pv_s1 = sum([fcf0 * ((1 + g1_base) ** yr) / ((1 + wacc) ** yr) for yr in range(1, 6)])
                fcf_yr5 = fcf0 * ((1 + g1_base) ** 5)
                tv = (fcf_yr5 * (1 + tg) / (wacc - tg)) / ((1 + wacc) ** 5)
                fv_ps = ((pv_s1 + tv) - net_debt) / shares if shares > 0 else 0
                discount = ((fv_ps - price) / price) * 100 if price > 0 else 0
                
                if fv_ps > 0:
                    if discount >= mos_req:
                        auto_signal = "🟢 BUY"
                        signal_color = "#1b5e20"
                        signal_detail = f"Undervalued by {discount:.0f}% (FV: ${fv_ps:,.0f} vs Price: ${price:,.2f})"
                    elif discount >= 0:
                        auto_signal = "🟡 HOLD"
                        signal_color = "#F59E0B"
                        signal_detail = f"Fairly valued with {discount:.0f}% upside (FV: ${fv_ps:,.0f})"
                    else:
                        auto_signal = "🔴 AVOID"
                        signal_color = "#DC2626"
                        signal_detail = f"Overvalued by {abs(discount):.0f}% (FV: ${fv_ps:,.0f} vs Price: ${price:,.2f})"
            except:
                pass
        
        # Display signal prominently - SIMPLE VERSION
        col1, col2, col3 = st.columns([2, 2, 2])
        
        with col1:
            if auto_signal == "🔴 AVOID":
                st.error(f"**{auto_signal}**\n{signal_detail}")
            elif auto_signal == "🟢 BUY":
                st.success(f"**{auto_signal}**\n{signal_detail}")
            elif auto_signal == "🟡 HOLD":
                st.warning(f"**{auto_signal}**\n{signal_detail}")
            else:
                st.info(f"**{auto_signal}**\n{signal_detail}")
        
        with col2:
            st.metric("Current Price", f"${price:,.2f}")
        
        with col3:
            if fcf0 > 0 and shares > 0 and price > 0:
                try:
                    pv_s1 = sum([fcf0 * ((1 + g1_base) ** yr) / ((1 + wacc) ** yr) for yr in range(1, 6)])
                    fcf_yr5 = fcf0 * ((1 + g1_base) ** 5)
                    tv = (fcf_yr5 * (1 + tg) / (wacc - tg)) / ((1 + wacc) ** 5)
                    fv_ps = ((pv_s1 + tv) - net_debt) / shares if shares > 0 else 0
                    st.metric("Fair Value", f"${fv_ps:,.0f}")
                except:
                    st.metric("Fair Value", "N/A")
            else:
                st.metric("Fair Value", "N/A")
        
        st.markdown("---")
        # Valuation + quality outputs (for later use in form)
        checks, buff_score, mx = buffett_test(vd, v)
        cat, note, peg, peg_v, g_pct = lynch_classify(vd, v, pe)
        moat_rat, moat_sc, moat_ev = moat_assessment(vd, v)

        # ── Form inputs for CIO section ──
        st.markdown('<div class="section-header">⚙️ Complete the investment thesis</div>', unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            cio_rec = st.radio("CIO Recommendation", ["BUY", "HOLD", "WATCH", "AVOID"], horizontal=True, key="cio_rec")
        with c2:
            port_weight = st.number_input("Suggested portfolio weight (%)", min_value=0.0, max_value=100.0, step=0.5, key="port_w")

        st.markdown('<div class="section-header">Investment Edge (one paragraph)</div>', unsafe_allow_html=True)
        inv_edge = st.text_area("Why is this company better than the other finalists? What's the competitive advantage or catalytic insight?",
                                placeholder="e.g. 'NVDA's dominant position in AI inference semiconductors is protected by network effects in software ecosystems...'",
                                height=80, key="inv_edge")

        st.markdown('<div class="section-header">Material Risks (maximum 5, one per line)</div>', unsafe_allow_html=True)
        risks = st.text_area("What could change our investment decision? List the 5 biggest risks.",
                             placeholder="1. AI demand slowdown\n2. Competitive threat from AMD\n3. Geopolitical export restrictions\n4. Valuation compression\n5. Supply chain disruption",
                             height=100, key="risks")

        # ═══════════════════════════════════════════════════════════════════════════════════
        # PHASE 2: REAL FINANCIAL STATEMENTS — 5-Year History
        # ═══════════════════════════════════════════════════════════════════════════════════
        
        st.markdown("---")
        st.markdown('<div class="section-header">📊 Financial Statements — 5-Year History</div>', unsafe_allow_html=True)
        
        # Fetch real financial data from FMP API
        try:
            # Fetch Income Statement
            income_stmt = fmp_get("income-statement", {"symbol": dos_ticker, "limit": 5})
            
            # Fetch Cash Flow Statement
            cashflow_stmt = fmp_get("cash-flow-statement", {"symbol": dos_ticker, "limit": 5})
            
            # Fetch Balance Sheet
            balance_sheet = fmp_get("balance-sheet-statement", {"symbol": dos_ticker, "limit": 5})
            
            # ═══════════════════════════════════════════════════════════════════════════════
            # TABLE 1: INCOME STATEMENT (5 YEARS)
            # ═══════════════════════════════════════════════════════════════════════════════
            
            if income_stmt and isinstance(income_stmt, list) and len(income_stmt) > 0:
                st.subheader("📈 Income Statement (5 Years)")
                
                # Build income statement dataframe
                income_data = []
                for stmt in sorted(income_stmt, key=lambda x: x.get('date', ''))[-5:]:  # Last 5 years
                    year = stmt.get('date', '').split('-')[0]
                    revenue = stmt.get('revenue', 0)
                    revenue_growth = stmt.get('revenueGrowth', 0)
                    gross_profit = stmt.get('grossProfit', 0)
                    gross_margin = (gross_profit / revenue * 100) if revenue > 0 else 0
                    operating_income = stmt.get('operatingIncome', 0)
                    operating_margin = (operating_income / revenue * 100) if revenue > 0 else 0
                    net_income = stmt.get('netIncome', 0)
                    net_margin = (net_income / revenue * 100) if revenue > 0 else 0
                    eps = stmt.get('eps', 0)
                    
                    income_data.append({
                        'Year': year,
                        'Revenue ($B)': f"${revenue/1e9:.1f}B" if revenue else "—",
                        'Revenue Growth %': f"{revenue_growth*100:.1f}%" if revenue_growth else "—",
                        'Gross Profit ($B)': f"${gross_profit/1e9:.1f}B" if gross_profit else "—",
                        'Gross Margin %': f"{gross_margin:.1f}%" if gross_margin > 0 else "—",
                        'Operating Income ($B)': f"${operating_income/1e9:.1f}B" if operating_income else "—",
                        'Operating Margin %': f"{operating_margin:.1f}%" if operating_margin > 0 else "—",
                        'Net Income ($B)': f"${net_income/1e9:.1f}B" if net_income else "—",
                        'Net Margin %': f"{net_margin:.1f}%" if net_margin > 0 else "—",
                        'EPS': f"${eps:.2f}" if eps else "—"
                    })
                
                df_income = pd.DataFrame(income_data)
                st.dataframe(df_income, use_container_width=True, hide_index=True)
                st.caption("💡 Look for: Growing revenue, stable margins, improving earnings")
            else:
                st.warning("Income statement data not available")
            
            st.markdown("---")
            
            # ═══════════════════════════════════════════════════════════════════════════════
            # TABLE 2: CASH FLOW STATEMENT (5 YEARS)
            # ═══════════════════════════════════════════════════════════════════════════════
            
            if cashflow_stmt and isinstance(cashflow_stmt, list) and len(cashflow_stmt) > 0:
                st.subheader("💰 Cash Flow Statement (5 Years)")
                
                # Build cash flow dataframe
                cashflow_data = []
                for stmt in sorted(cashflow_stmt, key=lambda x: x.get('date', ''))[-5:]:
                    year = stmt.get('date', '').split('-')[0]
                    operating_cf = stmt.get('operatingCashFlow', 0)
                    capex = stmt.get('capitalExpenditure', 0)
                    free_cf = stmt.get('freeCashFlow', 0)
                    revenue = stmt.get('operatingCashFlow', 0)  # Use OCF as proxy
                    fcf_margin = (free_cf / revenue * 100) if revenue > 0 else 0
                    
                    cashflow_data.append({
                        'Year': year,
                        'Operating Cash Flow ($B)': f"${operating_cf/1e9:.1f}B" if operating_cf else "—",
                        'Capital Expenditure ($B)': f"${abs(capex)/1e9:.1f}B" if capex else "—",
                        'Free Cash Flow ($B)': f"${free_cf/1e9:.1f}B" if free_cf else "—",
                        'FCF Margin %': f"{fcf_margin:.1f}%" if fcf_margin > 0 else "—"
                    })
                
                df_cashflow = pd.DataFrame(cashflow_data)
                st.dataframe(df_cashflow, use_container_width=True, hide_index=True)
                st.caption("💡 Look for: Growing free cash flow, low capex relative to revenue")
            else:
                st.warning("Cash flow statement data not available")
            
            st.markdown("---")
            
            # ═══════════════════════════════════════════════════════════════════════════════
            # TABLE 3: BALANCE SHEET & CAPITAL STRUCTURE (5 YEARS)
            # ═══════════════════════════════════════════════════════════════════════════════
            
            if balance_sheet and isinstance(balance_sheet, list) and len(balance_sheet) > 0:
                st.subheader("⚖️ Balance Sheet & Capital Structure (5 Years)")
                
                # Build balance sheet dataframe
                balance_data = []
                for stmt in sorted(balance_sheet, key=lambda x: x.get('date', ''))[-5:]:
                    year = stmt.get('date', '').split('-')[0]
                    cash = stmt.get('cashAndCashEquivalents', 0)
                    total_debt = stmt.get('totalDebt', 0)
                    net_debt = total_debt - cash
                    equity = stmt.get('totalStockholdersEquity', 0)
                    debt_equity = (total_debt / equity) if equity > 0 else 0
                    
                    balance_data.append({
                        'Year': year,
                        'Cash ($B)': f"${cash/1e9:.1f}B" if cash else "—",
                        'Total Debt ($B)': f"${total_debt/1e9:.1f}B" if total_debt else "—",
                        'Net Debt ($B)': f"${net_debt/1e9:.1f}B" if net_debt else "—",
                        'Shareholders Equity ($B)': f"${equity/1e9:.1f}B" if equity else "—",
                        'Debt/Equity Ratio': f"{debt_equity:.2f}" if debt_equity >= 0 else "—"
                    })
                
                df_balance = pd.DataFrame(balance_data)
                st.dataframe(df_balance, use_container_width=True, hide_index=True)
                st.caption("💡 Look for: Strong cash position, low debt, improving equity")
            else:
                st.warning("Balance sheet data not available")
            
            st.markdown("---")
            
            # ═══════════════════════════════════════════════════════════════════════════════
            # KEY FINANCIAL INSIGHTS
            # ═══════════════════════════════════════════════════════════════════════════════
            
            st.subheader("🎯 Key Financial Insights")
            
            insights = []
            
            # Analyze income statement trends
            if income_stmt and len(income_stmt) >= 2:
                latest_revenue = income_stmt[0].get('revenue', 0)
                prev_revenue = income_stmt[1].get('revenue', 0) if len(income_stmt) > 1 else latest_revenue
                rev_trend = ((latest_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0
                
                if rev_trend > 10:
                    insights.append("✅ **Strong Revenue Growth**: >10% YoY indicates healthy demand")
                elif rev_trend > 0:
                    insights.append("✅ **Positive Revenue Growth**: Growing steadily")
                else:
                    insights.append("⚠️ **Declining Revenue**: Watch for headwinds")
            
            # Analyze cash flow
            if cashflow_stmt and len(cashflow_stmt) >= 1:
                latest_fcf = cashflow_stmt[0].get('freeCashFlow', 0)
                if latest_fcf > 0:
                    insights.append("✅ **Positive Free Cash Flow**: Company generates real cash")
                else:
                    insights.append("⚠️ **Negative/Low FCF**: Watch cash burn rate")
            
            # Analyze balance sheet
            if balance_sheet and len(balance_sheet) >= 1:
                latest_cash = balance_sheet[0].get('cashAndCashEquivalents', 0)
                latest_debt = balance_sheet[0].get('totalDebt', 0)
                net_debt = latest_debt - latest_cash
                
                if net_debt < 0:
                    insights.append("✅ **Net Cash Position**: Company has more cash than debt")
                elif net_debt < latest_cash:
                    insights.append("✅ **Manageable Debt**: Debt < Cash position")
                else:
                    insights.append("⚠️ **High Leverage**: Debt exceeds cash, monitor closely")
            
            for insight in insights:
                st.write(insight)
            
            if not insights:
                st.info("💡 Load complete financial statements above for detailed analysis")
            
        except Exception as e:
            st.warning(f"Could not fetch financial statements: {str(e)[:100]}")
            st.info("💡 This is normal if the API is rate-limited. Try again in a moment.")
        
        st.markdown("---")

        # Generate dossier
        if st.button("📄 Generate Dossier PDF", key="gen_dos"):
            with st.spinner("Generating professional dossier..."):
                pdf_path = generate_dossier_pdf(dos_ticker, vd, v, result, checks, buff_score,
                                               cat, note, peg, moat_rat, moat_sc,
                                               cio_rec, inv_edge, risks)
            
            with open(pdf_path, "rb") as f:
                st.download_button(
                    label="📥 Download Dossier PDF",
                    data=f.read(),
                    file_name=f"{dos_ticker}_MCIS_Dossier_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    key="download_dos"
                )
            st.success(f"✅ Dossier generated — {dos_ticker}_MCIS_Dossier.pdf")
            st.info("📋 This 2-page dossier is ready for Investment Committee presentation. "
                   "Page 1 shows financials & ratios. Page 2 shows valuation & competitive analysis with your CIO thesis.")

    else:
        st.markdown('<div class="info-box">Enter a ticker and click <b>Load</b> to start building a professional investment dossier.</div>',
                    unsafe_allow_html=True)


# ═════════════════════════════════════════════
# QUALITATIVE ALERT SYSTEM — engine
# FMP stable: news, insider trading + SEC EDGAR fallback
# ═════════════════════════════════════════════

CRITICAL_KW = ["sec investigation","doj","fraud","subpoena","restatement","restate",
               "bankruptcy","chapter 11","delisting","going concern","resigns","resignation",
               "steps down","stepping down","abrupt departure","cuts guidance","lowers guidance",
               "slashes guidance","withdraws guidance","accounting irregular","short seller report",
               "material weakness","default","criminal"]
WARNING_KW  = ["lawsuit","class action","layoffs","job cuts","downgrade","downgrades",
               "misses estimates","earnings miss","revenue miss","data breach","cyberattack",
               "recall","probe","investigation","fine","penalty","antitrust","strike",
               "dilution","secondary offering","insider selling","warns","profit warning",
               "loses contract","delay","halted"]
POSITIVE_KW = ["beats estimates","raises guidance","upgrade","upgrades","buyback",
               "share repurchase","new contract","partnership","fda approval","record revenue",
               "dividend increase","insider buying","acquisition of","expands"]

FILING_SEVERITY = {
    "NT 10-K": ("CRITICAL", "Late annual report — potential accounting problem"),
    "NT 10-Q": ("CRITICAL", "Late quarterly report — potential accounting problem"),
    "8-K":     ("INFO",     "Material event disclosure — read what changed"),
    "SC 13D":  ("INFO",     "Activist/large investor stake above 5%"),
    "SC 13G":  ("INFO",     "Passive large investor stake above 5%"),
    "S-1":     ("WARNING",  "New share registration — possible dilution"),
    "S-3":     ("WARNING",  "Shelf registration — possible future dilution"),
    "424B":    ("WARNING",  "Prospectus — share offering in progress"),
    "10-K":    ("INFO",     "Annual report filed"),
    "10-Q":    ("INFO",     "Quarterly report filed"),
    "DEF 14A": ("INFO",     "Proxy statement — check executive pay and votes"),
}

def classify_headline(title):
    t = (title or "").lower()
    for k in CRITICAL_KW:
        if k in t: return "CRITICAL", k
    for k in WARNING_KW:
        if k in t: return "WARNING", k
    for k in POSITIVE_KW:
        if k in t: return "POSITIVE", k
    return None, None

def fetch_news(ticker, days=30):
    frm = (datetime.now() - pd.Timedelta(days=days)).strftime("%Y-%m-%d")
    raw = fmp_get("news/stock", {"symbols": ticker, "from": frm,
                                 "to": datetime.now().strftime("%Y-%m-%d"), "limit": 50})
    return raw if isinstance(raw, list) else []

def fetch_insiders(ticker, days=90):
    raw = fmp_get("insider-trading/search", {"symbol": ticker, "page": 0, "limit": 100})
    if not isinstance(raw, list): return []
    cutoff = (datetime.now() - pd.Timedelta(days=days)).strftime("%Y-%m-%d")
    out = []
    for t in raw:
        d = t.get("transactionDate") or t.get("filingDate") or ""
        if d and d >= cutoff: out.append(t)
    return out

@st.cache_data(ttl=86400)
def _edgar_cik_map():
    try:
        r = requests.get("https://www.sec.gov/files/company_tickers.json",
                         headers={"User-Agent": "MCIS research mcis@example.com"}, timeout=15)
        data = r.json()
        return {v["ticker"].upper(): str(v["cik_str"]).zfill(10) for v in data.values()}
    except Exception:
        return {}

@st.cache_data(ttl=3600)
def fetch_filings(ticker, days=90):
    """SEC filings — FMP stable first, direct SEC EDGAR as fallback."""
    frm = (datetime.now() - pd.Timedelta(days=days)).strftime("%Y-%m-%d")
    to  = datetime.now().strftime("%Y-%m-%d")
    raw = fmp_get("sec-filings-search/symbol",
                  {"symbol": ticker, "from": frm, "to": to, "page": 0, "limit": 100})
    filings = []
    if isinstance(raw, list) and raw and isinstance(raw[0], dict) and "Error" not in str(raw[0])[:60]:
        for f in raw:
            form = f.get("formType") or f.get("type") or ""
            if form:
                filings.append({"form": form,
                                "date": (f.get("filingDate") or f.get("acceptedDate") or "")[:10],
                                "link": f.get("finalLink") or f.get("link") or ""})
    if not filings:  # EDGAR direct fallback
        cik = _edgar_cik_map().get(ticker.upper())
        if cik:
            try:
                r = requests.get(f"https://data.sec.gov/submissions/CIK{cik}.json",
                                 headers={"User-Agent": "MCIS research mcis@example.com"}, timeout=15)
                rec = r.json().get("filings", {}).get("recent", {})
                for form, date, acc, doc in zip(rec.get("form", []), rec.get("filingDate", []),
                                                rec.get("accessionNumber", []), rec.get("primaryDocument", [])):
                    if date >= frm:
                        acc2 = acc.replace("-", "")
                        filings.append({"form": form, "date": date,
                                        "link": f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc2}/{doc}"})
            except Exception:
                pass
    return filings

def analyze_insiders(trades):
    """Cluster analysis of insider activity — returns summary + alerts."""
    alerts, sells, buys = [], [], []
    sell_val = buy_val = 0.0
    for t in trades:
        typ = (t.get("transactionType") or "").upper()
        ad  = (t.get("acquisitionOrDisposition") or "").upper()
        qty = float(t.get("securitiesTransacted") or 0)
        px  = float(t.get("price") or 0)
        val = qty * px
        if typ.startswith("S") or ad == "D":
            sells.append(t); sell_val += val
        elif typ.startswith("P") or ad == "A":
            buys.append(t); buy_val += val
    exec_sells = [t for t in sells if any(k in (t.get("typeOfOwner") or "").lower()
                  for k in ["chief executive","ceo","chief financial","cfo","president"])]
    if len(sells) >= 4:
        alerts.append(("WARNING", f"Cluster selling — {len(sells)} insider sales in 90 days (${sell_val/1e6:.1f}M)"))
    if any(float(t.get("securitiesTransacted") or 0)*float(t.get("price") or 0) > 5_000_000 for t in exec_sells):
        alerts.append(("WARNING", "CEO/CFO sale above $5M in the last 90 days"))
    if buy_val > 1_000_000 and buy_val > sell_val:
        alerts.append(("POSITIVE", f"Net insider BUYING — ${buy_val/1e6:.1f}M bought vs ${sell_val/1e6:.1f}M sold"))
    return {"n_sells": len(sells), "n_buys": len(buys),
            "sell_val": sell_val, "buy_val": buy_val, "alerts": alerts}

def run_alert_scan(tickers, news_days=30, insider_days=90, filing_days=60):
    out = {}
    for tk in tickers:
        entry = {"news_alerts": [], "insider": {}, "filing_alerts": [], "all": []}
        # News
        for n in fetch_news(tk, news_days):
            title = n.get("title") or ""
            sev, kw = classify_headline(title)
            if sev:
                a = {"sev": sev, "src": "NEWS", "date": (n.get("publishedDate") or "")[:10],
                     "text": title, "why": f"keyword: {kw}", "link": n.get("url") or ""}
                entry["news_alerts"].append(a); entry["all"].append(a)
        # Insiders
        ins = analyze_insiders(fetch_insiders(tk, insider_days))
        entry["insider"] = ins
        for sev, msg in ins["alerts"]:
            a = {"sev": sev, "src": "INSIDER", "date": "", "text": msg, "why": "", "link": ""}
            entry["all"].append(a)
        # SEC filings
        for f in fetch_filings(tk, filing_days):
            for prefix, (sev, why) in FILING_SEVERITY.items():
                if f["form"].upper().startswith(prefix):
                    a = {"sev": sev, "src": "SEC", "date": f["date"],
                         "text": f"{f['form']} filed", "why": why, "link": f["link"]}
                    entry["filing_alerts"].append(a); entry["all"].append(a)
                    break
        out[tk] = entry
    return out

# ═════════════════════════════════════════════
# VALUATION ENGINE — DCF, Reverse DCF, Buffett,
# Lynch classification, Moat assessment
# ═════════════════════════════════════════════

def fetch_valuation_data(ticker):
    d = fetch_company(ticker)
    if not d.get("ok"): return d
    d["income6"]   = fmp_get("income-statement",     {"symbol": ticker, "period": "annual", "limit": 6})
    d["cashflow6"] = fmp_get("cash-flow-statement",  {"symbol": ticker, "period": "annual", "limit": 6})
    d["balance"]   = fmp_get("balance-sheet-statement", {"symbol": ticker, "period": "annual", "limit": 2})
    q = fmp_get("quote", {"symbol": ticker})
    d["quote"] = q[0] if isinstance(q, list) and q else {}
    d["metrics6"]  = fmp_get("key-metrics", {"symbol": ticker, "period": "annual", "limit": 6})
    return d

def _val_inputs(d):
    """Extract the raw numbers the valuation engine needs."""
    v = {}
    q   = d.get("quote", {})
    bal = d.get("balance", []) or []
    cf  = d.get("cashflow6", []) or []
    inc = d.get("income6", []) or []
    v["price"]  = float(q.get("price") or d.get("price") or 0)
    v["shares"] = float(q.get("sharesOutstanding") or 0)
    if not v["shares"] and v["price"] and d.get("mktcap"):
        v["shares"] = d["mktcap"] / v["price"]
    v["mktcap"] = float(q.get("marketCap") or d.get("mktcap") or 0)
    b0 = bal[0] if bal else {}
    cash = float(b0.get("cashAndShortTermInvestments") or b0.get("cashAndCashEquivalents") or 0)
    debt = float(b0.get("totalDebt") or 0)
    v["net_debt"] = debt - cash
    # FCF history (oldest→newest)
    fcf_hist = [float(y["freeCashFlow"]) for y in reversed(cf) if y.get("freeCashFlow") is not None]
    v["fcf_hist"] = fcf_hist
    ttm = d.get("ttm", {}) or {}
    v["fcf0"] = float(ttm.get("freeCashFlowTTM") or (fcf_hist[-1] if fcf_hist else 0))
    if not v["fcf0"] and fcf_hist: v["fcf0"] = fcf_hist[-1]
    # historical growth rates
    def cagr(series):
        s = [x for x in series if x and x > 0]
        if len(s) >= 3: return (s[-1]/s[0])**(1/(len(s)-1)) - 1
        return None
    v["fcf_cagr"] = cagr(fcf_hist)
    revs = [float(y["revenue"]) for y in reversed(inc) if y.get("revenue")]
    v["rev_hist"] = revs
    v["rev_cagr"] = cagr(revs)
    eps  = [float(y["eps"]) for y in reversed(inc) if y.get("eps") is not None]
    v["eps_hist"] = eps
    v["eps_cagr"] = cagr([e for e in eps if e > 0]) if any(e > 0 for e in eps) else None
    v["ni_hist"]  = [float(y.get("netIncome") or 0) for y in reversed(inc)]
    v["shares_hist"] = [float(y.get("weightedAverageShsOutDil") or y.get("weightedAverageShsOut") or 0)
                        for y in reversed(inc)]
    return v

def dcf_equity_value(fcf0, g1, wacc, terminal_g, net_debt, fade_years=5, growth_years=5):
    """Two-stage DCF: growth_years at g1, then linear fade to terminal_g, plus terminal value."""
    if fcf0 <= 0 or wacc <= terminal_g: return None, []
    flows, fcf = [], fcf0
    for yr in range(1, growth_years + 1):
        fcf *= (1 + g1); flows.append(fcf)
    for i in range(1, fade_years + 1):
        g = g1 + (terminal_g - g1) * i / fade_years
        fcf *= (1 + g); flows.append(fcf)
    pv = sum(f / (1 + wacc) ** (i + 1) for i, f in enumerate(flows))
    tv = flows[-1] * (1 + terminal_g) / (wacc - terminal_g)
    pv += tv / (1 + wacc) ** len(flows)
    return pv - net_debt, flows

def reverse_dcf(price, shares, fcf0, wacc, terminal_g, net_debt):
    """Bisection: what growth rate is priced in at the current market price?"""
    if fcf0 <= 0 or not shares or not price: return None
    target = price * shares
    lo, hi = -0.10, 0.60
    for _ in range(60):
        mid = (lo + hi) / 2
        ev, _ = dcf_equity_value(fcf0, mid, wacc, terminal_g, net_debt)
        if ev is None: return None
        if ev < target: lo = mid
        else: hi = mid
    return (lo + hi) / 2

def buffett_test(d, v):
    """10-point Buffett quality checklist on real data. Returns (checks, score, max)."""
    checks = []
    met  = d.get("metrics6", []) or []
    rat  = d.get("ratios", []) or []
    inc  = d.get("income6", []) or []
    def add(name, ok, detail):
        checks.append({"check": name, "ok": ok, "detail": detail})
    # 1-2 ROIC level and consistency
    roics = []
    for y in met:
        r = y.get("returnOnInvestedCapital") or y.get("roic")
        if r is not None: roics.append(float(r) * 100)
    add("ROIC ≥ 15% (latest)", bool(roics) and roics[0] >= 15,
        f"{roics[0]:.1f}%" if roics else "n/a")
    add("ROIC ≥ 12% every year (consistency)", bool(roics) and len(roics) >= 3 and min(roics[:5]) >= 12,
        f"min {min(roics[:5]):.1f}% over {min(len(roics),5)} yrs" if roics else "n/a")
    # 3 Gross margin
    gm = None
    for y in rat[:1]:
        g = y.get("grossProfitMargin") or y.get("grossMargin")
        if g is not None: gm = float(g) * 100
    if gm is None and inc:
        rev, gp = inc[0].get("revenue"), inc[0].get("grossProfit")
        if rev and gp: gm = gp / rev * 100
    add("Gross margin ≥ 40% (pricing power)", gm is not None and gm >= 40,
        f"{gm:.1f}%" if gm is not None else "n/a")
    # 4 Net margin
    nm = None
    if inc and inc[0].get("revenue"):
        nm = float(inc[0].get("netIncome") or 0) / float(inc[0]["revenue"]) * 100
    add("Net margin ≥ 15%", nm is not None and nm >= 15, f"{nm:.1f}%" if nm is not None else "n/a")
    # 5 FCF margin
    fm = None
    if v["fcf_hist"] and v["rev_hist"]:
        fm = v["fcf_hist"][-1] / v["rev_hist"][-1] * 100
    add("FCF margin ≥ 12%", fm is not None and fm >= 12, f"{fm:.1f}%" if fm is not None else "n/a")
    # 6 Debt
    de = d.get("metrics", [])
    dv = None
    for y in (de[:2] if isinstance(de, list) else []):
        x = y.get("debtToEbitda") or y.get("netDebtToEBITDA")
        if x is not None: dv = float(x); break
    add("Debt/EBITDA ≤ 2.5x or net cash", dv is not None and dv <= 2.5,
        f"{dv:.2f}x" if dv is not None else "n/a")
    # 7 Revenue growth
    add("Revenue CAGR ≥ 8%", v["rev_cagr"] is not None and v["rev_cagr"] >= 0.08,
        f"{v['rev_cagr']*100:.1f}%" if v["rev_cagr"] is not None else "n/a")
    # 8 EPS growth
    add("EPS growing over 5 yrs", v["eps_cagr"] is not None and v["eps_cagr"] > 0,
        f"{v['eps_cagr']*100:.1f}% CAGR" if v["eps_cagr"] is not None else "n/a")
    # 9 Share count
    sh = [s for s in v["shares_hist"] if s > 0]
    add("Share count flat or shrinking (buybacks)", len(sh) >= 3 and sh[-1] <= sh[0] * 1.02,
        f"{(sh[-1]/sh[0]-1)*100:+.1f}% over {len(sh)} yrs" if len(sh) >= 3 else "n/a")
    # 10 FCF conversion
    conv = None
    if v["fcf_hist"] and v["ni_hist"] and v["ni_hist"][-1] > 0:
        conv = v["fcf_hist"][-1] / v["ni_hist"][-1] * 100
    add("FCF / Net Income ≥ 80% (earnings are real cash)", conv is not None and conv >= 80,
        f"{conv:.0f}%" if conv is not None else "n/a")
    score = sum(1 for c in checks if c["ok"])
    return checks, score, len(checks)

def lynch_classify(d, v, pe):
    """Peter Lynch category + PEG verdict."""
    g = v["eps_cagr"] if v["eps_cagr"] is not None else v["rev_cagr"]
    g_pct = g * 100 if g is not None else None
    mktcap = v["mktcap"]
    sector = d.get("sector", "")
    cyclical_sectors = ["Energy", "Basic Materials", "Consumer Cyclical", "Industrials", "Materials"]
    eps = v["eps_hist"]
    if eps and eps[-1] < 0 and len(eps) >= 2 and max(eps) > 0:
        cat, note = "Turnaround", "Earnings currently negative after being positive — thesis depends on recovery, size positions small."
    elif g_pct is None:
        cat, note = "Unclassified", "Not enough growth history to classify."
    elif g_pct >= 20:
        cat, note = "Fast Grower", "Lynch's favourite — 20%+ growers. Watch for the growth fade; pay up only with a reasonable PEG."
    elif g_pct >= 10:
        cat = "Stalwart" if mktcap > 10e9 else "Mid-pace Grower"
        note = "Solid 10-20% grower. Lynch expects 30-50% gains then rotate — do not expect a ten-bagger."
    elif sector in cyclical_sectors:
        cat, note = "Cyclical", "Earnings follow the economic cycle — low P/E can be a TOP not a bottom. Time the cycle, not the P/E."
    else:
        cat, note = "Slow Grower", "Sub-10% growth — only interesting for dividends. Rarely a fit for MCIS Tier 1."
    peg = None
    if pe and g_pct and g_pct > 0:
        peg = pe / g_pct
    if peg is None:            peg_verdict = "PEG unavailable"
    elif peg <= 1.0:           peg_verdict = "PEG ≤ 1.0 — attractively priced for its growth (Lynch buy zone)"
    elif peg <= 1.5:           peg_verdict = "PEG 1.0-1.5 — fairly priced"
    elif peg <= 2.0:           peg_verdict = "PEG 1.5-2.0 — expensive, needs execution"
    else:                      peg_verdict = "PEG > 2.0 — priced for perfection"
    return cat, note, peg, peg_verdict, g_pct

def moat_assessment(d, v):
    """Quantitative moat evidence score 0-10 → None / Narrow / Wide."""
    ev, score = [], 0
    rat = d.get("ratios", []) or []
    gms = []
    for y in rat:
        g = y.get("grossProfitMargin") or y.get("grossMargin")
        if g is not None: gms.append(float(g) * 100)
    if gms:
        avg = sum(gms) / len(gms)
        if avg >= 50: score += 2; ev.append(f"🟢 Avg gross margin {avg:.0f}% — strong pricing power (+2)")
        elif avg >= 35: score += 1; ev.append(f"🟡 Avg gross margin {avg:.0f}% — decent (+1)")
        else: ev.append(f"🔴 Avg gross margin {avg:.0f}% — weak pricing power (+0)")
        if len(gms) >= 3 and (max(gms) - min(gms)) <= 6:
            score += 1; ev.append(f"🟢 Margin stability — range only {max(gms)-min(gms):.1f} pts (+1)")
    met = d.get("metrics6", []) or []
    roics = [float(y.get("returnOnInvestedCapital") or y.get("roic") or 0) * 100
             for y in met if (y.get("returnOnInvestedCapital") or y.get("roic")) is not None]
    if roics:
        if min(roics[:5]) >= 15 and len(roics) >= 3:
            score += 3; ev.append(f"🟢 ROIC ≥ 15% every year for {min(len(roics),5)} yrs — durable advantage (+3)")
        elif roics[0] >= 15:
            score += 2; ev.append(f"🟡 ROIC {roics[0]:.0f}% now but not consistently (+2)")
        elif roics[0] >= 10:
            score += 1; ev.append(f"🟡 ROIC {roics[0]:.0f}% — average business (+1)")
        else:
            ev.append(f"🔴 ROIC {roics[0]:.0f}% — no evidence of moat (+0)")
    if v["fcf_hist"] and v["rev_hist"]:
        fm = v["fcf_hist"][-1] / v["rev_hist"][-1] * 100
        if fm >= 20: score += 2; ev.append(f"🟢 FCF margin {fm:.0f}% — cash machine (+2)")
        elif fm >= 10: score += 1; ev.append(f"🟡 FCF margin {fm:.0f}% (+1)")
        else: ev.append(f"🔴 FCF margin {fm:.0f}% (+0)")
    if v["rev_cagr"] is not None and v["rev_cagr"] >= 0.10:
        score += 2; ev.append(f"🟢 Revenue compounding at {v['rev_cagr']*100:.0f}% — moat is widening, not just defending (+2)")
    rating = "WIDE MOAT" if score >= 8 else ("NARROW MOAT" if score >= 5 else "NO MOAT EVIDENCE")
    return rating, score, ev

# ─────────────────────────────────────────────
# PAGE: VALUATION ENGINE
# ─────────────────────────────────────────────

if page == "🏛 Valuation Engine":
    st.markdown("""
    <div class="mcis-header">
        <p class="mcis-title">🏛 Valuation Engine</p>
        <p class="mcis-subtitle">DCF | Reverse DCF | Buffett Quality Test | Lynch Classification | Moat Assessment</p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns([3, 1])
    with c1:
        # Get available tickers from scan results
        available_tickers = sorted(set([r["ticker"] for r in st.session_state.scan_results]))
        
        if available_tickers:
            val_ticker = st.selectbox(
                "Select company or type ticker",
                [""] + available_tickers,
                index=0,
                key="val_ticker_select"
            )
            if not val_ticker:
                val_ticker = st.text_input("Or enter ticker manually", placeholder="e.g. NVDA", key="val_ticker_in").upper().strip()
        else:
            val_ticker = st.text_input("Ticker symbol", placeholder="e.g. NVDA", key="val_ticker_in").upper().strip()
            st.caption("💡 Run the Scanner first to populate the dropdown")
    
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        load = st.button("📥 Load Company")

    if load and val_ticker:
        with st.spinner(f"Fetching 6 years of financials for {val_ticker}..."):
            vd = fetch_valuation_data(val_ticker)
        if not vd.get("ok"):
            st.error(f"Could not fetch data for {val_ticker}. Check the ticker.")
        else:
            st.session_state["val_data"] = vd

    vd = st.session_state.get("val_data")
    if vd and vd.get("ok"):
        v = _val_inputs(vd)
        result = run_filters(vd)
        m = result.get("metrics", {})
        pe = m.get("pe")

        st.subheader(f"{vd['ticker']} — {vd.get('name','')}")
        st.caption(f"{vd.get('sector','')} | {vd.get('industry','')} | Price ${v['price']:,.2f} | "
                   f"Mkt Cap {fmt_mktcap(v['mktcap'])} | MCIS Score {result['score']}/100 ({result['verdict']})")

        if v["fcf0"] <= 0:
            st.markdown('<div class="warning-box"><b>FCF is negative or unavailable</b> — a DCF is not meaningful. '
                        'The quality, Lynch and moat sections below still work.</div>', unsafe_allow_html=True)

        # ── DCF assumptions ──
        st.markdown('<div class="section-header">⚙️ DCF Assumptions — adjust and everything recalculates live</div>', unsafe_allow_html=True)
        hist_g = v["fcf_cagr"] if v["fcf_cagr"] is not None else v["rev_cagr"]
        default_g = int(round(min(max((hist_g or 0.10) * 100, 4), 25)))
        a1, a2, a3, a4 = st.columns(4)
        with a1: g1  = st.slider("Growth yrs 1-5 (%)", -5, 40, default_g) / 100
        with a2: wacc = st.slider("Discount rate (%)", 6.0, 15.0, 10.0, 0.5) / 100
        with a3: tg  = st.slider("Terminal growth (%)", 1.0, 4.0, 2.5, 0.25) / 100
        with a4: mos_req = st.slider("Required margin of safety (%)", 10, 50, 25, 5)
        _fcf_c = f"{v['fcf_cagr']*100:.1f}%" if v['fcf_cagr'] is not None else "n/a"
        _rev_c = f"{v['rev_cagr']*100:.1f}%" if v['rev_cagr'] is not None else "n/a"
        st.caption(f"Historical FCF CAGR: {_fcf_c} | Revenue CAGR: {_rev_c} | "
                   f"FCF base (TTM): ${v['fcf0']/1e9:.2f}B | Net debt: ${v['net_debt']/1e9:.2f}B")

        if v["fcf0"] > 0 and v["shares"]:
            scenarios = {
                "🐻 Bear":  max(g1 * 0.6, -0.05),
                "⚖️ Base":  g1,
                "🚀 Bull":  min(g1 * 1.3, 0.40),
            }
            rows, per_share = [], {}
            for name, g in scenarios.items():
                eq, _ = dcf_equity_value(v["fcf0"], g, wacc, tg, v["net_debt"])
                ps = eq / v["shares"] if eq else 0
                per_share[name] = ps
                mos = (1 - v["price"] / ps) * 100 if ps > 0 else -999
                rows.append({"Scenario": name, "FCF growth": f"{g*100:.1f}%",
                             "Intrinsic value/share": f"${ps:,.2f}",
                             "vs Price": f"{(ps/v['price']-1)*100:+.1f}%" if v['price'] else "n/a",
                             "Margin of safety": f"{mos:.1f}%" if mos > -999 else "n/a"})

            st.markdown('<div class="section-header">💰 DCF — Three Scenario Intrinsic Value</div>', unsafe_allow_html=True)
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            # Football field chart
            import plotly.graph_objects as go
            fig = go.Figure()
            colors_map = {"🐻 Bear": "#e65100", "⚖️ Base": "#1a3c5e", "🚀 Bull": "#1b5e20"}
            for name, ps in per_share.items():
                fig.add_trace(go.Bar(x=[ps], y=[name], orientation="h",
                                     marker_color=colors_map[name], text=f"${ps:,.0f}",
                                     textposition="outside", showlegend=False))
            fig.add_vline(x=v["price"], line_dash="dash", line_color="#c9a84c", line_width=3,
                          annotation_text=f"Price ${v['price']:,.0f}", annotation_position="top")
            fig.update_layout(height=260, margin=dict(l=10, r=10, t=30, b=10),
                              xaxis_title="Value per share ($)", plot_bgcolor="white")
            st.plotly_chart(fig, use_container_width=True)

            # 5-Year Price Chart
            st.markdown('<div class="section-header">📈 5-Year Price History</div>', unsafe_allow_html=True)
            prices = fetch_historical_prices_yahoo(val_ticker)
            if prices and len(prices) > 10:
                fig_price = plot_5year_price_chart_yahoo(prices, val_ticker, v["price"])
                if fig_price:
                    st.plotly_chart(fig_price, use_container_width=True)
                else:
                    st.info("Chart unavailable")
            else:
                st.info(f"⚠️ Price history not available for {val_ticker}. Current price: ${v['price']:,.2f}")

            base_ps = per_share["⚖️ Base"]
            base_mos = (1 - v["price"] / base_ps) * 100 if base_ps > 0 else -999
            if base_mos >= mos_req:
                st.success(f"✅ BUY ZONE — base case margin of safety {base_mos:.0f}% meets your {mos_req}% requirement. "
                           f"Buy-below price: ${base_ps*(1-mos_req/100):,.2f}")
            elif base_mos > 0:
                st.warning(f"⚠️ UNDERVALUED BUT THIN — {base_mos:.0f}% margin of safety is below your {mos_req}% requirement. "
                           f"Target entry: ${base_ps*(1-mos_req/100):,.2f}")
            else:
                st.error(f"❌ ABOVE INTRINSIC VALUE — price exceeds base case by {-base_mos:.0f}%. "
                         f"Target entry: ${base_ps*(1-mos_req/100):,.2f}")

            # Reverse DCF
            st.markdown('<div class="section-header">🔄 Reverse DCF — what the market is pricing in</div>', unsafe_allow_html=True)
            implied = reverse_dcf(v["price"], v["shares"], v["fcf0"], wacc, tg, v["net_debt"])
            if implied is not None:
                r1, r2, r3 = st.columns(3)
                r1.metric("Implied FCF growth (yrs 1-5)", f"{implied*100:.1f}%")
                r2.metric("Historical FCF CAGR", f"{v['fcf_cagr']*100:.1f}%" if v['fcf_cagr'] is not None else "n/a")
                r3.metric("Your base assumption", f"{g1*100:.1f}%")
                if v["fcf_cagr"] is not None:
                    if implied > v["fcf_cagr"] * 1.2:
                        st.error(f"Market demands {implied*100:.1f}% growth — MORE than the company has historically delivered "
                                 f"({v['fcf_cagr']*100:.1f}%). The stock is priced for acceleration.")
                    elif implied < v["fcf_cagr"] * 0.7:
                        st.success(f"Market only demands {implied*100:.1f}% — LESS than historical {v['fcf_cagr']*100:.1f}%. "
                                   "Expectations are beatable — this is where mispricing lives.")
                    else:
                        st.info(f"Market expects {implied*100:.1f}% — roughly in line with history. Fairly priced on growth.")
            else:
                st.info("Reverse DCF unavailable (needs positive FCF and share count).")

        # ── Buffett Quality Test ──
        st.markdown('<div class="section-header">🎩 Buffett Quality Test — 10 checks</div>', unsafe_allow_html=True)
        checks, score, mx = buffett_test(vd, v)
        b1, b2 = st.columns([1, 3])
        with b1:
            st.metric("Quality Score", f"{score}/{mx}")
            if score >= 8:   st.success("WONDERFUL COMPANY")
            elif score >= 6: st.info("GOOD COMPANY")
            elif score >= 4: st.warning("AVERAGE")
            else:            st.error("AVOID — quality too low")
        with b2:
            for c in checks:
                (st.success if c["ok"] else st.error)(f"{'✓' if c['ok'] else '✗'} {c['check']} — {c['detail']}")

        # ── Lynch Classification ──
        st.markdown('<div class="section-header">📈 Peter Lynch Classification</div>', unsafe_allow_html=True)
        cat, note, peg, peg_verdict, g_pct = lynch_classify(vd, v, pe)
        l1, l2, l3 = st.columns(3)
        l1.metric("Category", cat)
        l2.metric("Growth rate", f"{g_pct:.1f}%" if g_pct is not None else "n/a")
        l3.metric("PEG ratio", f"{peg:.2f}" if peg is not None else "n/a")
        st.info(f"**{cat}** — {note}")
        if peg is not None:
            (st.success if peg <= 1.5 else st.warning if peg <= 2 else st.error)(peg_verdict)

        # ── Moat Assessment ──
        st.markdown('<div class="section-header">🏰 Moat Assessment</div>', unsafe_allow_html=True)
        rating, mscore, evidence = moat_assessment(vd, v)
        mo1, mo2 = st.columns([1, 3])
        with mo1:
            st.metric("Moat Evidence Score", f"{mscore}/10")
            if rating == "WIDE MOAT":    st.success(f"🏰 {rating}")
            elif rating == "NARROW MOAT": st.info(f"🛡️ {rating}")
            else:                         st.error(f"⚠️ {rating}")
        with mo2:
            for e in evidence: st.write(e)
        with st.expander("📝 Qualitative moat checklist — your judgement, not the data's"):
            st.caption("Numbers show a moat EXISTS. These questions identify WHAT it is. Tick what genuinely applies:")
            for q in ["Network effects — does each new customer make the product better for others?",
                      "Switching costs — is it painful/expensive for customers to leave?",
                      "Intangibles — brand, patents or licences competitors cannot copy?",
                      "Cost advantage — can it produce cheaper than anyone else at scale?",
                      "Efficient scale — is the market only big enough for a few players?"]:
                st.checkbox(q, key=f"moat_{vd['ticker']}_{q[:20]}")

        st.caption("MCIS Valuation Engine | Blueprint v1.1 | Models, not predictions — not investment advice")
    else:
        st.markdown('<div class="info-box">Enter a ticker and click <b>Load Company</b>. '
                    'The engine fetches 6 years of financials once, then every slider recalculates the DCF instantly.</div>',
                    unsafe_allow_html=True)

# ─────────────────────────────────────────────
# PAGE: QUALITATIVE ALERTS
# ─────────────────────────────────────────────

if page == "🚨 Qualitative Alerts":
    st.markdown("""
    <div class="mcis-header">
        <p class="mcis-title">🚨 Qualitative Alert System</p>
        <p class="mcis-subtitle">News | Insider Trading | SEC Filings — monitoring Tier 1 holdings for thesis breakers</p>
    </div>
    """, unsafe_allow_html=True)

    # Build the default monitoring list: Tier 1 from last scan + watchlist
    tier1 = sorted({r["ticker"] for r in st.session_state.scan_results if r.get("layer") == "LONG_TERM"})
    wl    = sorted({r["ticker"] for r in st.session_state.watchlist})
    universe = sorted(set(tier1) | set(wl))

    st.markdown(f'<div class="info-box"><b>Monitoring universe:</b> {len(tier1)} Tier 1 companies from your last scan '
                f'+ {len(wl)} watchlist companies. Each ticker uses ~3 API calls — keep runs under ~40 tickers '
                f'to stay inside FMP free-tier limits.</div>', unsafe_allow_html=True)

    c1, c2 = st.columns([3, 1])
    with c1:
        default_sel = universe[:15] if universe else []
        selected = st.multiselect("Tickers to monitor", options=universe, default=default_sel)
        manual = st.text_input("Add extra tickers (comma separated)", placeholder="e.g. NVDA, ASML, LLY")
    with c2:
        news_days   = st.selectbox("News lookback", [7, 14, 30, 60], index=2)
        filing_days = st.selectbox("SEC filings lookback", [30, 60, 90], index=1)

    scan_list = list(dict.fromkeys(selected + [t.strip().upper() for t in manual.split(",") if t.strip()]))

    if st.button("🚨 Run Alert Scan") and scan_list:
        prog = st.progress(0, text="Starting alert scan...")
        results = {}
        for i, tk in enumerate(scan_list):
            prog.progress((i + 1) / len(scan_list), text=f"Scanning {tk} ({i+1}/{len(scan_list)})...")
            results.update(run_alert_scan([tk], news_days=news_days, filing_days=filing_days))
        prog.empty()
        st.session_state["alert_results"] = results
        st.session_state["alert_time"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    results = st.session_state.get("alert_results", {})
    if results:
        st.caption(f"Last alert scan: {st.session_state.get('alert_time','')}")
        n_crit = sum(1 for r in results.values() for a in r["all"] if a["sev"] == "CRITICAL")
        n_warn = sum(1 for r in results.values() for a in r["all"] if a["sev"] == "WARNING")
        n_pos  = sum(1 for r in results.values() for a in r["all"] if a["sev"] == "POSITIVE")
        n_info = sum(1 for r in results.values() for a in r["all"] if a["sev"] == "INFO")

        k1, k2, k3, k4 = st.columns(4)
        k1.markdown(f'<div class="metric-card" style="border-left-color:#b71c1c"><div class="metric-value" style="color:#b71c1c">{n_crit}</div><div class="metric-label">🔴 Critical — act today</div></div>', unsafe_allow_html=True)
        k2.markdown(f'<div class="metric-card tier3-card"><div class="metric-value" style="color:#e65100">{n_warn}</div><div class="metric-label">🟠 Warnings — investigate</div></div>', unsafe_allow_html=True)
        k3.markdown(f'<div class="metric-card tier1-card"><div class="metric-value" style="color:#1b5e20">{n_pos}</div><div class="metric-label">🟢 Positive signals</div></div>', unsafe_allow_html=True)
        k4.markdown(f'<div class="metric-card"><div class="metric-value">{n_info}</div><div class="metric-label">🔵 Informational</div></div>', unsafe_allow_html=True)

        # Critical feed first — across all tickers
        crit_feed = [(tk, a) for tk, r in results.items() for a in r["all"] if a["sev"] == "CRITICAL"]
        if crit_feed:
            st.markdown('<div class="section-header">🔴 CRITICAL ALERTS — Investment Committee review required</div>', unsafe_allow_html=True)
            for tk, a in crit_feed:
                link = f" — [source]({a['link']})" if a["link"] else ""
                st.error(f"**{tk}** | {a['src']} | {a['date']} — {a['text']}{link}")

        st.markdown('<div class="section-header">📡 Company-by-company feed</div>', unsafe_allow_html=True)
        order = sorted(results.keys(),
                       key=lambda t: (-sum(1 for a in results[t]["all"] if a["sev"] == "CRITICAL"),
                                      -sum(1 for a in results[t]["all"] if a["sev"] == "WARNING")))
        for tk in order:
            r = results[tk]
            nc = sum(1 for a in r["all"] if a["sev"] == "CRITICAL")
            nw = sum(1 for a in r["all"] if a["sev"] == "WARNING")
            badge = "🔴" if nc else ("🟠" if nw else "🟢")
            ins = r["insider"]
            with st.expander(f"{badge} {tk} — {nc} critical, {nw} warnings | insiders: "
                             f"{ins.get('n_buys',0)} buys / {ins.get('n_sells',0)} sells"):
                if ins.get("n_sells") or ins.get("n_buys"):
                    st.caption(f"Insider 90-day flow: bought ${ins.get('buy_val',0)/1e6:.1f}M | "
                               f"sold ${ins.get('sell_val',0)/1e6:.1f}M")
                if not r["all"]:
                    st.success("✓ Quiet — no qualitative alerts in the lookback window. Thesis undisturbed.")
                for a in sorted(r["all"], key=lambda x: {"CRITICAL":0,"WARNING":1,"POSITIVE":2,"INFO":3}[x["sev"]]):
                    link = f" — [source]({a['link']})" if a["link"] else ""
                    line = f"**{a['src']}** {a['date']} — {a['text']}" + (f" _({a['why']})_" if a["why"] else "") + link
                    if a["sev"] == "CRITICAL":  st.error(line)
                    elif a["sev"] == "WARNING": st.warning(line)
                    elif a["sev"] == "POSITIVE":st.success(line)
                    else:                       st.info(line)

        st.markdown("""
        <div class="warning-box"><b>MCIS Rule — Section 16 triggers:</b> any 🔴 CRITICAL alert on a held position
        requires an Investment Committee thesis review within 48 hours. A cluster of insider selling alone is not a
        thesis breaker — but combined with a guidance cut or accounting alert, it is.</div>
        """, unsafe_allow_html=True)
    elif not universe:
        st.markdown('<div class="info-box">No Tier 1 or watchlist companies found yet — run the Scanner first, '
                    'or add tickers manually above.</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# PAGE: DATA AUDIT
# ─────────────────────────────────────────────

if page == "🔬 Data Audit":
    st.markdown("""
    <div class="mcis-header">
        <p class="mcis-title">🔬 Data Audit</p>
        <p class="mcis-subtitle">Spot-check FMP data against Yahoo Finance & SEC filings — ensure data quality</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="info-box">
    <b>Why data audit matters:</b> FMP is fast and convenient, but occasionally returns stale or incorrect data.
    This page compares FMP against Yahoo Finance (daily) and SEC filings (official source) for a sample of companies.
    Any major discrepancy (<5% variance flags caution, >10% requires review).
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-header">🔍 Sample Companies to Validate</div>', unsafe_allow_html=True)
    st.caption("These 5 companies represent different sectors and market caps. A clean audit on these suggests data quality is solid.")

    sample_tickers = ["NVDA", "MSFT", "ASML", "SNOW", "AMD"]
    audit_results = {}

    if st.button("🚀 Run Data Audit on Sample"):
        prog = st.progress(0, text="Starting audit...")
        for i, ticker in enumerate(sample_tickers):
            prog.progress((i + 1) / len(sample_tickers), text=f"Auditing {ticker}...")
            audit_results[ticker] = audit_fmp_vs_yahoo(ticker)
        prog.empty()
        st.session_state["audit_results"] = audit_results
        st.session_state["audit_time"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    results = st.session_state.get("audit_results", {})
    if results:
        st.caption(f"Last audit: {st.session_state.get('audit_time','')}")

        # Summary cards
        passed = sum(1 for r in results.values() if r.get("status") == "✅ MATCH")
        flagged = sum(1 for r in results.values() if r.get("status") == "⚠️ REVIEW")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f'<div class="metric-card tier1-card"><div class="metric-value" style="color:#1b5e20">{passed}</div><div class="metric-label">✅ Data Matches Yahoo</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="metric-card tier3-card"><div class="metric-value" style="color:#e65100">{flagged}</div><div class="metric-label">⚠️ Minor Discrepancies</div></div>', unsafe_allow_html=True)

        st.markdown('<div class="section-header">📋 Detailed Audit Results</div>', unsafe_allow_html=True)
        
        for ticker in sample_tickers:
            audit = results.get(ticker, {})
            status = audit.get("status", "⚠️ REVIEW")
            
            with st.expander(f"{status} — {ticker}"):
                if "error" in audit:
                    st.error(f"Error: {audit['error']}")
                else:
                    # Matches
                    if audit.get("matches"):
                        st.success("✓ Data Matches:")
                        for metric, comparison in audit["matches"].items():
                            st.write(f"  • {metric.upper()}: {comparison}")
                    
                    # Discrepancies
                    if audit.get("discrepancies"):
                        st.warning("⚠️ Discrepancies Found:")
                        for disc in audit["discrepancies"]:
                            st.write(f"  • {disc}")
                        st.caption("**Action:** Verify the higher variance in SEC filings or contact FMP support")
                    else:
                        st.success("No material discrepancies detected")

        st.markdown("""
        <div class="warning-box">
        <b>Data Quality Guidelines:</b>
        🟢 <5% variance = Confidence in FMP data
        🟡 5-10% variance = Note the variance, use with caution
        🔴 >10% variance = Verify against SEC filings before using in analysis
        </div>
        """, unsafe_allow_html=True)

        # Export audit results
        audit_df_rows = []
        for ticker in sample_tickers:
            audit = results.get(ticker, {})
            audit_df_rows.append({
                "Ticker": ticker,
                "Status": audit.get("status", "N/A"),
                "Matches": len(audit.get("matches", {})),
                "Discrepancies": len(audit.get("discrepancies", [])),
            })
        audit_df = pd.DataFrame(audit_df_rows)
        st.dataframe(audit_df, use_container_width=True, hide_index=True)

        st.markdown('<div class="section-header">📊 Add Custom Ticker to Audit</div>', unsafe_allow_html=True)
        custom_ticker = st.text_input("Enter ticker to audit", placeholder="e.g. AAPL").upper().strip()
        if st.button("🔍 Audit Ticker") and custom_ticker:
            with st.spinner(f"Auditing {custom_ticker}..."):
                custom_audit = audit_fmp_vs_yahoo(custom_ticker)
            status = custom_audit.get("status", "⚠️ REVIEW")
            st.subheader(f"{status} — {custom_ticker}")
            if "error" in custom_audit:
                st.error(f"Error: {custom_audit['error']}")
            else:
                if custom_audit.get("matches"):
                    st.success("✓ Data Matches:")
                    for metric, comparison in custom_audit["matches"].items():
                        st.write(f"  • {metric.upper()}: {comparison}")
                if custom_audit.get("discrepancies"):
                    st.warning("⚠️ Discrepancies Found:")
                    for disc in custom_audit["discrepancies"]:
                        st.write(f"  • {disc}")
                else:
                    st.success("No material discrepancies detected")

    else:
        st.markdown('<div class="info-box">Click <b>Run Data Audit</b> to validate FMP data against Yahoo Finance for a sample of companies.</div>', unsafe_allow_html=True)
