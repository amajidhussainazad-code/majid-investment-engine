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
API_KEY = "EBgvBcpXZ972yqnngUEMujYeBuk2cPZy"
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

        d["ok"] = True
    except Exception as e:
        d["err"] = str(e)
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
         "📋 Watchlist", "⚡ Swing Trades", "📅 Quarterly Review"],
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

def results_to_df(results):
    rows = []
    for r in results:
        m = r.get("metrics",{})
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
            "EV/EBITDA": m.get("ev_ebitda","N/A"),
            "Halal":     r.get("halal","?"),
            "Price":     f"${r['price']:,.2f}" if r.get('price') else "N/A",
            "Mkt Cap":   fmt_mktcap(r.get("mktcap",0)),
        })
    return pd.DataFrame(rows)

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
        # Top Tier 1 table
        st.markdown('<div class="section-header">🏆 Top Tier 1 Companies — Buy Candidates</div>', unsafe_allow_html=True)
        if t1:
            df = results_to_df(sorted(t1, key=lambda x: x["score"], reverse=True)[:10])
            st.dataframe(df[["Ticker","Company","Score","ROIC%","GM%","RevCAGR%","Halal","Price","Mkt Cap"]],
                        use_container_width=True, hide_index=True)
        else:
            st.info("No Tier 1 results yet. Run the scanner first.")

        # Capital allocation
        st.markdown('<div class="section-header">💰 Capital Allocation — $5,000 Starting Capital</div>', unsafe_allow_html=True)
        alloc_data = {
            "Layer": ["Halal ETF Core","Tier 1 Compounders","Tier 2 Growth","Swing/Tactical","Opportunity Cash"],
            "Allocation": ["30%","25%","20%","5%","20%"],
            "Amount": ["$1,500","$1,250","$1,000","$250","$1,000"],
            "What to Buy": ["SPUS + SPTE + SPWO","Top 3-4 Tier 1 companies","Top 2-3 Tier 2 companies","Options/special situations","Money market — deploy on crash"],
        }
        st.dataframe(pd.DataFrame(alloc_data), use_container_width=True, hide_index=True)

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

                if   result["layer"]=="LONG_TERM": t1.append(result)
                elif result["layer"]=="MID_TERM":  t2.append(result)
                elif result["layer"]=="SWING":     t3.append(result)
                else:                               rejected += 1

                results_text.markdown(
                    f"**Live results:** 🟢 T1: {len(t1)} | 🔵 T2: {len(t2)} | 🟠 T3: {len(t3)} | ❌ Rejected: {rejected}")

            except Exception as e:
                errors += 1

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

    ticker_input = st.text_input("Enter ticker symbol", placeholder="e.g. NVDA").upper().strip()

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
        <p class="mcis-subtitle">Your saved companies across all tiers</p>
    </div>
    """, unsafe_allow_html=True)

    watchlist = st.session_state.watchlist

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
        st.markdown('<div class="info-box">Your watchlist is empty. Add companies from the Scanner, Rankings or Company Lookup pages.</div>', unsafe_allow_html=True)
    else:
        st.caption(f"{len(watchlist)} companies on watchlist")
        df = results_to_df(watchlist)
        st.dataframe(df[["Ticker","Company","Sector","Score","Tier","ROIC%","GM%","RevCAGR%","Halal","Price","Mkt Cap"]],
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

# This line intentionally left blank
