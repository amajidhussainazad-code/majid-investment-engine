"""
MCIS Dashboard v1.1.3 — Majid Capital Investment System
Streamlit dynamic dashboard
Deploy: streamlit run app.py

v1.1:   Currency-conversion fix — foreign-currency statements (DKK, TWD, RMB...)
        are converted to USD before every DCF / fair-value calculation,
        and per-share scaling is ADR-immune (market-cap based).
v1.1.2: Dossier fixes — Net Margin / FCF Margin were never computed; tables
        dropped the most recent fiscal year and invented their year headers;
        foreign currencies printed with a "$"; balance sheet only fetched 2 yrs;
        shares outstanding read a field FMP omits; net debt shown in the oldest
        column; revenue growth showed a CAGR instead of YoY; /tmp/ path broke
        the PDF button on Windows.
v1.1.3: Dossier gains Total Overheads, Overheads % of Revenue,
        Non-Operating & Tax net, and Net Profit / (Loss) with accounting
        parentheses. Statement figures convert to USD at the spot rate
        prevailing at EACH fiscal year end. FX failure is now loud in the app
        instead of silently printing foreign currency as dollars.
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
# API key — Streamlit Cloud Secrets first, then an environment variable,
# then the historical literal.
# ⚠️ SECURITY: if this repo is public, the literal below is public too.
#    Rotate the key in FMP and keep the new one in Secrets only.
try:
    API_KEY = st.secrets["FMP_API_KEY"]
except Exception:
    API_KEY = os.environ.get("FMP_API_KEY", "bjdd20Euw6xoPRfudtkjuMzxnyPdLMHJ")

BASE = "https://financialmodelingprep.com/stable"

NO_FLY = ["alcohol", "tobacco", "gambling", "casino", "conventional bank",
          "pork", "adult entertainment", "weapons of mass"]
HALAL_FAIL_SECTORS  = ["Financial Services", "Banks", "Banking", "Insurance"]
HALAL_CLEAN_SECTORS = ["Technology", "Healthcare", "Industrials"]

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
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════
# ★ MCIS v1.1 CURRENCY FIX — live FX helpers (used by the DCF engines)
# FMP returns statements in each company's REPORTING currency
# (DKK for NVO, TWD for TSM, RMB for PDD...). These helpers convert
# every statement figure to USD BEFORE any DCF / fair value math.
# ═══════════════════════════════════════════════════════════════
@st.cache_data(ttl=3600)
def get_fx_to_usd(currency):
    """1 unit of `currency` in USD, at today's spot. Returns 1.0 for USD/unknown."""
    if not currency or currency == "USD":
        return 1.0
    try:
        q = fmp_get("quote", {"symbol": f"{currency}USD"})
        if isinstance(q, list) and q and q[0].get("price"):
            return float(q[0]["price"])
        q = fmp_get("quote", {"symbol": f"USD{currency}"})
        if isinstance(q, list) and q and q[0].get("price"):
            return 1.0 / float(q[0]["price"])
    except Exception:
        pass
    return 1.0


def stmt_fx(statements):
    """FX multiplier for a list of FMP statements (reads reportedCurrency of latest)."""
    try:
        if statements and isinstance(statements, list) and isinstance(statements[0], dict):
            return get_fx_to_usd(statements[0].get("reportedCurrency", "USD"))
    except Exception:
        pass
    return 1.0


# ═══════════════════════════════════════════════════════════════
# ★ MCIS v1.1.3 — HISTORICAL FX
# The dossier converts each statement at the spot rate prevailing at
# THAT statement's own period end, not one rate smeared across all years.
# get_fx_on_date() returns None on failure — never a silent 1.0, which is
# what printed CNY figures as though they were dollars.
# ═══════════════════════════════════════════════════════════════
@st.cache_data(ttl=86400)
def _fx_series(currency):
    """Daily history of 1 unit of `currency` in USD. {'YYYY-MM-DD': rate} or {}."""
    if not currency or currency.upper() == "USD":
        return {"__identity__": 1.0}
    c = currency.upper()

    def _parse(rows, invert=False):
        out = {}
        if not isinstance(rows, list):
            return out
        for row in rows:
            if not isinstance(row, dict):
                continue
            dt = row.get("date")
            px = row.get("price")
            if px is None:
                px = row.get("close")
            if not dt or px is None:
                continue
            try:
                p = float(px)
            except Exception:
                continue
            if p <= 0:
                continue
            out[str(dt)[:10]] = (1.0 / p) if invert else p
        return out

    for endpoint, sym, inv in [
        ("historical-price-eod/light", f"{c}USD", False),
        ("historical-price-eod/full",  f"{c}USD", False),
        ("historical-price-eod/light", f"USD{c}", True),
        ("historical-price-eod/full",  f"USD{c}", True),
    ]:
        series = _parse(fmp_get(endpoint, {"symbol": sym}), invert=inv)
        if series:
            return series
    return {}


def get_fx_on_date(currency, date_str):
    """Spot rate for 1 unit of `currency` in USD, on or just before date_str.

    Returns (rate, asof_date, stale_flag). rate is None when the lookup FAILED.
    """
    if not currency or currency.upper() == "USD":
        return 1.0, "—", False

    series = _fx_series(currency)
    if "__identity__" in series:
        return 1.0, "—", False
    if not series:
        return None, None, False

    target = (date_str or "")[:10]
    if not target:
        return None, None, False

    on_or_before = [dt for dt in series if dt <= target]
    if on_or_before:
        best = max(on_or_before)
        return series[best], best, False

    earliest = min(series)
    return series[earliest], earliest, True


def fx_health_check(vd):
    """Pre-flight FX check for a loaded company — drives the in-app warning."""
    info = {"ccy": "USD", "needs_fx": False, "ok": True,
            "rates": [], "missing": [], "stale": []}
    try:
        src = (vd.get("income6") or vd.get("income") or [])
        if src and isinstance(src[0], dict):
            info["ccy"] = (src[0].get("reportedCurrency") or "USD").upper()
    except Exception:
        return info

    if info["ccy"] == "USD":
        return info
    info["needs_fx"] = True

    dates = set()
    for key in ("income6", "income", "cashflow6", "cashflow", "balance"):
        for row in (vd.get(key) or []):
            if isinstance(row, dict):
                dt = (row.get("date") or "")[:10]
                if dt:
                    dates.add(dt)

    for dt in sorted(dates):
        rate, asof, stale = get_fx_on_date(info["ccy"], dt)
        if rate is None:
            info["missing"].append(dt)
            info["ok"] = False
        else:
            info["rates"].append((dt[:4], rate, asof, stale))
            if stale:
                info["stale"].append(dt)
    return info


def fetch_company(ticker):
    d = {"ticker": ticker, "ok": False}
    try:
        raw = fmp_get("profile", {"symbol": ticker})
        if not isinstance(raw, list) or not raw:
            return d
        p = raw[0]
        d.update({
            "name":     p.get("companyName") or ticker,
            "sector":   p.get("sector", "Unknown"),
            "industry": p.get("industry", "Unknown"),
            "price":    p.get("price", 0),
            "mktcap":   p.get("marketCap", 0),
            "desc":     p.get("description", ""),
            "profile":  p,
        })
        d["metrics"]  = fmp_get("key-metrics",         {"symbol": ticker, "period": "annual", "limit": 4})
        d["ttm"]      = fmp_get("key-metrics-ttm",     {"symbol": ticker})
        d["income"]   = fmp_get("income-statement",    {"symbol": ticker, "period": "annual", "limit": 4})
        d["cashflow"] = fmp_get("cash-flow-statement", {"symbol": ticker, "period": "annual", "limit": 4})
        d["ratios"]   = fmp_get("ratios",              {"symbol": ticker, "period": "annual", "limit": 4})

        if isinstance(d["ttm"], list) and d["ttm"]:
            d["ttm"] = d["ttm"][0]
        elif not isinstance(d["ttm"], dict):
            d["ttm"] = {}

        # FCF
        try:
            cf = d.get("cashflow", [])
            if cf and isinstance(cf, list) and len(cf) > 0 and isinstance(cf[0], dict):
                ocf = cf[0].get("operatingCashFlow") or cf[0].get("operatingCashflows")
                capex = cf[0].get("capitalExpenditure") or cf[0].get("capitalExpenditures")
                if ocf is not None and capex is not None:
                    fcf_val = float(ocf) - abs(float(capex))
                    if fcf_val > 0:
                        d["fcf"] = fcf_val * stmt_fx(cf)
        except Exception:
            pass

        # Shares outstanding
        try:
            shares = None
            ttm_data = d.get("ttm", {})
            if isinstance(ttm_data, dict):
                shares = (ttm_data.get("weightedAverageShsOut")
                          or ttm_data.get("weightedAverageShsOutDil")
                          or ttm_data.get("numberOfShares")
                          or ttm_data.get("sharesOutstanding"))
            if not shares:
                met = d.get("metrics", [])
                if met and isinstance(met, list) and len(met) > 0 and isinstance(met[0], dict):
                    shares = (met[0].get("weightedAverageShsOut")
                              or met[0].get("weightedAverageShsOutDil")
                              or met[0].get("numberOfShares")
                              or met[0].get("sharesOutstanding"))
            if not shares and d.get("profile"):
                shares = (d["profile"].get("shFloat")
                          or d["profile"].get("sharesOutstanding")
                          or d["profile"].get("sharesFloat"))
            # ★ v1.1 ADR-immune: prefer shares implied by USD mktcap/price.
            try:
                _px = float(d.get("price") or 0)
                _mc = float(d.get("mktcap") or 0)
                if _px > 0 and _mc > 0:
                    shares = _mc / _px
            except Exception:
                pass
            if shares and shares > 0:
                d["shares"] = float(shares)
        except Exception:
            pass

        # Net debt
        try:
            ttm = d.get("ttm", {})
            if isinstance(ttm, dict):
                total_debt = ttm.get("totalDebt") or ttm.get("longTermDebt") or ttm.get("totalLiabilities", 0)
                cash = ttm.get("cashAndCashEquivalents") or ttm.get("cash") or ttm.get("shortTermInvestments", 0)
                _fx_nd = stmt_fx(d.get("cashflow", []))
                if total_debt and cash is not None:
                    d["net_debt"] = (float(total_debt) - float(cash)) * _fx_nd
                elif total_debt:
                    d["net_debt"] = float(total_debt) * _fx_nd
        except Exception:
            pass

        d["ok"] = True
    except Exception as e:
        d["err"] = str(e)
    return d


def fetch_valuation_data(ticker):
    """Fetch 6 years of financials for valuation and dossier."""
    d = fetch_company(ticker)
    if not d.get("ok"):
        return d
    d["income6"]   = fmp_get("income-statement",        {"symbol": ticker, "period": "annual", "limit": 6})
    d["cashflow6"] = fmp_get("cash-flow-statement",     {"symbol": ticker, "period": "annual", "limit": 6})
    # ★ v1.1.2 FIX: was limit 2, so 3 of the 5 dossier columns were always blank
    d["balance"]   = fmp_get("balance-sheet-statement", {"symbol": ticker, "period": "annual", "limit": 6})
    q = fmp_get("quote", {"symbol": ticker})
    d["quote"] = q[0] if isinstance(q, list) and q else {}
    d["metrics6"]  = fmp_get("key-metrics", {"symbol": ticker, "period": "annual", "limit": 6})
    return d


# ─────────────────────────────────────────────
# HALAL CHECK
# ─────────────────────────────────────────────
def check_halal(d):
    desc     = d.get("desc", "").lower()
    sector   = d.get("sector", "")
    industry = d.get("industry", "").lower()
    if any(k in desc for k in NO_FLY):
        return "FAIL", "Prohibited activity"
    if any(s in sector for s in HALAL_FAIL_SECTORS):
        return "FAIL", "Conventional finance"
    if any(k in industry for k in ["bank", "insur", "alcohol", "tobacco", "casino", "gambling"]):
        return "FAIL", f"Prohibited: {industry}"
    if sector in HALAL_CLEAN_SECTORS:
        return "PASS", "Clean sector"
    return "CONDITIONAL", "Verify via Zoya"


# ─────────────────────────────────────────────
# EXTRACT METRICS
# ─────────────────────────────────────────────
def extract_metrics(d):
    m   = {}
    met = d.get("metrics", [])
    ttm = d.get("ttm", {})
    rat = d.get("ratios", [])
    inc = d.get("income", [])
    cf  = d.get("cashflow", [])

    # ROIC
    for yr in met[:2]:
        v = yr.get("returnOnInvestedCapital") or yr.get("roic")
        if v is not None:
            m["roic"] = round(float(v) * 100, 1)
            break
    if "roic" not in m:
        v = ttm.get("returnOnInvestedCapitalTTM") or ttm.get("roicTTM")
        if v is not None:
            m["roic"] = round(float(v) * 100, 1)

    # FCF
    fcf_list = []
    for yr in cf[:4]:
        v = yr.get("freeCashFlow")
        if v is not None:
            fcf_list.append(float(v))
    m["fcf_list"] = fcf_list

    # Gross Margin
    for yr in rat[:2]:
        v = yr.get("grossProfitMargin") or yr.get("grossMargin")
        if v is not None:
            m["gm"] = round(float(v) * 100, 1)
            break
    if "gm" not in m:
        for yr in inc[:1]:
            rev, gp = yr.get("revenue", 0), yr.get("grossProfit", 0)
            if rev and gp:
                m["gm"] = round((gp / rev) * 100, 1)

    # Revenue CAGR
    revs = [float(yr["revenue"]) for yr in inc[:4] if yr.get("revenue")]
    if len(revs) >= 3:
        m["rev_cagr"] = round(((revs[0] / revs[-1]) ** (1 / (len(revs) - 1)) - 1) * 100, 1)

    # Debt/EBITDA
    for yr in met[:2]:
        v = yr.get("debtToEbitda") or yr.get("netDebtToEBITDA")
        if v is not None:
            m["debt_ebitda"] = round(float(v), 2)
            break
    if "debt_ebitda" not in m:
        v = ttm.get("debtToEbitdaTTM") or ttm.get("netDebtToEBITDATTM")
        if v is not None:
            m["debt_ebitda"] = round(float(v), 2)

    # PE
    for yr in met[:1]:
        v = yr.get("peRatio") or yr.get("priceToEarningsRatio")
        if v:
            m["pe"] = round(float(v), 1)
    if "pe" not in m:
        v = ttm.get("peRatioTTM")
        if v:
            m["pe"] = round(float(v), 1)
    if "pe" not in m and d.get("price") and d.get("income"):
        try:
            price = float(d.get("price", 0))
            eps = float(d.get("income", [{}])[0].get("eps", 0))
            if price > 0 and eps > 0:
                m["pe"] = round(price / eps, 1)
        except Exception:
            pass

    # ★ v1.1.1: recompute P/E in USD terms.
    try:
        _px = float(d.get("price", 0) or 0)
        _inc0 = (d.get("income") or [{}])[0]
        _eps_rep = float(_inc0.get("eps") or 0)
        if _px > 0 and _eps_rep > 0:
            _fx_eps = stmt_fx(d.get("income", []))
            _pe_usd = _px / (_eps_rep * _fx_eps)
            if 0 < _pe_usd < 500:
                m["pe"] = round(_pe_usd, 1)
    except Exception:
        pass

    # EV/EBITDA
    v = ttm.get("evToEbitdaTTM") or ttm.get("enterpriseValueOverEBITDATTM")
    if v:
        m["ev_ebitda"] = round(float(v), 1)

    # FCF Yield
    v = ttm.get("freeCashFlowYieldTTM")
    if v:
        m["fcf_yield"] = round(float(v) * 100, 1)

    # ═══════════════════════════════════════════════════════════════
    # ★ v1.1.2 FIX — the dossier's KEY FINANCIAL RATIOS block asks for
    # m['nm'] and m['fcf_margin'], but nothing ever wrote them. That is why
    # Net Margin printed "—" and FCF Margin printed "N/A%".
    # ═══════════════════════════════════════════════════════════════
    for yr in rat[:1]:
        val = yr.get("netProfitMargin") or yr.get("netIncomeMargin")
        if val is not None:
            m["nm"] = round(float(val) * 100, 1)
            break
    if "nm" not in m and inc:
        try:
            rev = float(inc[0].get("revenue") or 0)
            ni = inc[0].get("netIncome")
            if rev > 0 and ni is not None:
                m["nm"] = round(float(ni) / rev * 100, 1)
        except Exception:
            pass

    if "fcf_margin" not in m and cf and inc:
        try:
            fcf_v = cf[0].get("freeCashFlow")
            rev_v = float(inc[0].get("revenue") or 0)
            if fcf_v is not None and rev_v > 0:
                m["fcf_margin"] = round(float(fcf_v) / rev_v * 100, 1)
        except Exception:
            pass

    # EV/EBITDA fallback — FMP omits the TTM field on many foreign filers.
    if "ev_ebitda" not in m and inc:
        try:
            _fx = stmt_fx(inc)
            ebitda_usd = float(inc[0].get("ebitda") or 0) * _fx
            mc = float(d.get("mktcap") or 0)
            nd = float(d.get("net_debt") or 0)
            if ebitda_usd > 0 and mc > 0:
                m["ev_ebitda"] = round((mc + nd) / ebitda_usd, 1)
        except Exception:
            pass

    return m


# ─────────────────────────────────────────────
# RUN MCIS FILTERS
# ─────────────────────────────────────────────
def run_filters(d):
    r = {
        "ticker":   d["ticker"],
        "name":     d.get("name", d["ticker"]),
        "sector":   d.get("sector", "Unknown"),
        "price":    d.get("price", 0),
        "mktcap":   d.get("mktcap", 0),
        "fcf":      d.get("fcf", 0),
        "shares":   d.get("shares", 0),
        "net_debt": d.get("net_debt", 0),
        "passed":   [], "failed": [], "warnings": [],
        "score":    0,  "metrics": {},
        "verdict":  "", "layer": "",
        "halal":    "", "halal_reason": "",
    }
    desc = d.get("desc", "").lower()
    if any(k in desc for k in NO_FLY):
        r["verdict"] = "REJECTED — No Fly Zone"
        return r

    h_status, h_reason = check_halal(d)
    r["halal"] = h_status
    r["halal_reason"] = h_reason
    if h_status == "FAIL":
        r["verdict"] = "REJECTED — Halal Fail"
        return r

    m = extract_metrics(d)
    r["metrics"] = m

    # Filter 1 — ROIC
    if "roic" in m:
        if m["roic"] >= 15:
            r["passed"].append(f"ROIC {m['roic']}%"); r["score"] += 25
        elif m["roic"] >= 10:
            r["warnings"].append(f"ROIC {m['roic']}%"); r["score"] += 10
        else:
            r["failed"].append(f"ROIC {m['roic']}% low")
    else:
        r["warnings"].append("ROIC unavailable")

    # Filter 2 — FCF
    fcf = m.get("fcf_list", [])
    if fcf:
        if fcf[0] > 0 and len(fcf) >= 2 and fcf[0] > fcf[-1]:
            r["passed"].append("FCF positive+growing"); r["score"] += 20
        elif fcf[0] > 0:
            r["warnings"].append("FCF positive"); r["score"] += 10
        else:
            r["failed"].append("FCF negative")
    else:
        r["warnings"].append("FCF unavailable")

    # Filter 3 — Gross Margin
    if "gm" in m:
        if m["gm"] >= 35:
            r["passed"].append(f"GM {m['gm']}%"); r["score"] += 20
        elif m["gm"] >= 20:
            r["warnings"].append(f"GM {m['gm']}%"); r["score"] += 8
        else:
            r["failed"].append(f"GM {m['gm']}% low")
    else:
        r["warnings"].append("GM unavailable")

    # Filter 4 — Revenue Growth
    if "rev_cagr" in m:
        if m["rev_cagr"] >= 8:
            r["passed"].append(f"RevCAGR {m['rev_cagr']}%"); r["score"] += 20
        elif m["rev_cagr"] >= 3:
            r["warnings"].append(f"RevCAGR {m['rev_cagr']}%"); r["score"] += 8
        else:
            r["failed"].append(f"RevCAGR {m['rev_cagr']}% low")
    else:
        r["warnings"].append("RevCAGR unavailable")

    # Filter 5 — Debt/EBITDA
    if "debt_ebitda" in m:
        if m["debt_ebitda"] < 0:
            r["passed"].append("Net cash"); r["score"] += 15
        elif m["debt_ebitda"] <= 3:
            r["passed"].append(f"D/E {m['debt_ebitda']}x"); r["score"] += 15
        elif m["debt_ebitda"] <= 5:
            r["warnings"].append(f"D/E {m['debt_ebitda']}x elevated"); r["score"] += 5
        else:
            r["failed"].append(f"D/E {m['debt_ebitda']}x high")
    else:
        r["warnings"].append("Debt/EBITDA unavailable")

    fails = len(r["failed"])
    s = r["score"]
    if fails == 0 and s >= 75:
        r["verdict"] = "TIER 1"; r["layer"] = "LONG_TERM"
    elif fails <= 1 and s >= 55:
        r["verdict"] = "TIER 2"; r["layer"] = "MID_TERM"
    elif fails <= 2 and s >= 35:
        r["verdict"] = "TIER 3"; r["layer"] = "SWING"
    else:
        r["verdict"] = "REJECTED"; r["layer"] = "REJECTED"
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
         "📈 ETF Monitor",
         "📋 Watchlist", "⚡ Swing Trades", "📅 Quarterly Review", "🔬 Data Audit"],
        label_visibility="collapsed"
    )
    st.markdown("---")
    with st.expander("📖 Signal Legend"):
        st.markdown("""
**STOCKS:**
- 🟢 **BUY** — Price ≤ 75% of fair value (25% margin of safety). Strong buy.
- 🟡 **HOLD** — Fair value zone. Monitor, wait for dip.
- 🔴 **AVOID** — Overvalued. Skip, wait for correction.
- ⚠️ **DATA INSUFF** — <2 years history. Come back later.

**ETF TRACK 1 (Ready to Buy, 2+ yrs):**
- 🔴 **RED (80-100)** — Strongly recommend
- 🟡 **YELLOW (70-79)** — Worth reviewing
- 🟠 **ORANGE (60-69)** — You decide (trade-offs shown)
- 🟢 **GREEN (40-59)** — Monitor only
- ⚪ **SUPPRESSED (<40)** — Skip

**ETF TRACK 2 (Watch List, <2 yrs):**
- 🚀 **EARLY BIRD** — Strong start, consider 1-3% exploratory
- 🔵 **EMERGING** — 3-12 months, monitor
- 🟣 **DEVELOPING** — 1-2 yrs, approaching evaluation
        """)
    st.markdown("---")
    st.markdown('<p class="sidebar-text" style="font-size:0.8em">Blueprint v1.2 | Phase 3 | Not investment advice</p>',
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
    except Exception:
        pass


def load_from_disk():
    try:
        if os.path.exists(SAVE_FILE):
            with open(SAVE_FILE, "r") as f:
                return json.load(f)
    except Exception:
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
    if status == "PASS":
        return "🟢 PASS"
    elif status == "CONDITIONAL":
        return "🟡 CHECK"
    else:
        return "🔴 FAIL"


def score_color(score):
    if score >= 75:
        return "🟢"
    elif score >= 55:
        return "🟡"
    else:
        return "🔴"


def fmt_mktcap(v):
    if not v:
        return "N/A"
    if v >= 1e12:
        return f"${v/1e12:.1f}T"
    if v >= 1e9:
        return f"${v/1e9:.1f}B"
    return f"${v/1e6:.0f}M"


# ═══════════════════════════════════════════════════════════════════════════
# PHASE 3: PROFESSIONAL VALUATION ENGINE
# ═══════════════════════════════════════════════════════════════════════════
RISK_FREE_RATE = 0.045       # 10-yr US Treasury (update quarterly)
EQUITY_RISK_PREMIUM = 0.055  # Historical equity premium
TERMINAL_GROWTH = 0.025      # Terminal growth rate


def p3_fetch_history(ticker):
    """Fetch full financial history for Phase 3 valuation."""
    inc  = fmp_get("income-statement", {"symbol": ticker, "limit": 12}) or []
    cf   = fmp_get("cash-flow-statement", {"symbol": ticker, "limit": 12}) or []
    bs   = fmp_get("balance-sheet-statement", {"symbol": ticker, "limit": 12}) or []
    prof = fmp_get("profile", {"symbol": ticker}) or []
    km   = fmp_get("key-metrics", {"symbol": ticker, "limit": 12}) or []
    if isinstance(inc, list): inc = sorted(inc, key=lambda x: x.get('date', ''))
    if isinstance(cf, list):  cf  = sorted(cf,  key=lambda x: x.get('date', ''))
    if isinstance(bs, list):  bs  = sorted(bs,  key=lambda x: x.get('date', ''))
    return inc, cf, bs, prof, km


def p3_data_confidence(years):
    """Data confidence based on years of history."""
    if years >= 10: return "HIGH", 10
    if years >= 5:  return "MEDIUM", 5
    if years >= 2:  return "LOW", 3
    return "UNRATED", 0


def p3_quality_score(inc, cf, bs, km, years):
    """5-factor quality scoring, 1-25 scale. Adaptive by data availability."""
    factors = {}
    roic = 0
    try:
        if km and isinstance(km, list):
            latest_km = sorted(km, key=lambda x: x.get('date', ''))[-1]
            roic = (latest_km.get('roic') or latest_km.get('returnOnInvestedCapital') or 0) * 100
    except Exception:
        pass
    if roic > 30: factors['ROIC'] = 5
    elif roic > 20: factors['ROIC'] = 4
    elif roic > 15: factors['ROIC'] = 3
    elif roic > 10: factors['ROIC'] = 2
    else: factors['ROIC'] = 1

    fcf_growth = 0
    try:
        if len(cf) >= 2:
            f1 = cf[-2].get('freeCashFlow', 0)
            f2 = cf[-1].get('freeCashFlow', 0)
            if f1 and f1 > 0:
                fcf_growth = (f2 - f1) / f1 * 100
    except Exception:
        pass
    if fcf_growth > 20: factors['FCF Growth'] = 5
    elif fcf_growth > 10: factors['FCF Growth'] = 4
    elif fcf_growth > 5: factors['FCF Growth'] = 3
    elif fcf_growth > 0: factors['FCF Growth'] = 2
    else: factors['FCF Growth'] = 1

    rev_cagr = 0
    try:
        n = min(4, len(inc))
        if n >= 2:
            r0 = inc[-n].get('revenue', 0)
            r1 = inc[-1].get('revenue', 0)
            if r0 and r0 > 0:
                rev_cagr = ((r1 / r0) ** (1 / (n - 1)) - 1) * 100
    except Exception:
        pass
    if rev_cagr > 20: factors['Revenue Growth'] = 5
    elif rev_cagr > 10: factors['Revenue Growth'] = 4
    elif rev_cagr > 5: factors['Revenue Growth'] = 3
    elif rev_cagr > 0: factors['Revenue Growth'] = 2
    else: factors['Revenue Growth'] = 1

    if years >= 5:
        try:
            latest_bs = bs[-1] if bs else {}
            latest_inc = inc[-1] if inc else {}
            cash = latest_bs.get('cashAndCashEquivalents', 0) or 0
            debt = latest_bs.get('totalDebt', 0) or 0
            ebitda = latest_inc.get('ebitda', 0) or latest_inc.get('operatingIncome', 0) or 0
            net_debt = debt - cash
            if net_debt <= 0:
                factors['Balance Sheet'] = 5
            elif ebitda > 0:
                nd_ebitda = net_debt / ebitda
                if nd_ebitda < 0.5: factors['Balance Sheet'] = 5
                elif nd_ebitda < 1.0: factors['Balance Sheet'] = 4
                elif nd_ebitda < 2.0: factors['Balance Sheet'] = 3
                elif nd_ebitda < 3.0: factors['Balance Sheet'] = 2
                else: factors['Balance Sheet'] = 1
            else:
                factors['Balance Sheet'] = 1
        except Exception:
            factors['Balance Sheet'] = 3

    if years >= 10:
        try:
            margins = []
            for s in inc[-5:]:
                rev = s.get('revenue', 0)
                gp = s.get('grossProfit', 0)
                if rev > 0:
                    margins.append(gp / rev * 100)
            if len(margins) >= 3:
                trend = (margins[-1] - margins[0]) / max(len(margins) - 1, 1)
                if trend > 3: factors['Margin Stability'] = 5
                elif trend > 1: factors['Margin Stability'] = 4
                elif trend > -2: factors['Margin Stability'] = 3
                elif trend > -5: factors['Margin Stability'] = 2
                else: factors['Margin Stability'] = 1
            else:
                factors['Margin Stability'] = 3
        except Exception:
            factors['Margin Stability'] = 3

    n_factors = len(factors)
    raw = sum(factors.values())
    score_25 = round(raw / (n_factors * 5) * 25) if n_factors else 0
    return score_25, factors, {'roic': roic, 'fcf_growth': fcf_growth, 'rev_cagr': rev_cagr}


def p3_premium(score_25, confidence):
    """Quality-linked premium, capped by data confidence."""
    if score_25 >= 23: prem = 1.20
    elif score_25 >= 20: prem = 1.17
    elif score_25 >= 17: prem = 1.13
    elif score_25 >= 14: prem = 1.10
    elif score_25 >= 10: prem = 1.07
    else: prem = 1.00
    if confidence == "MEDIUM": prem = min(prem, 1.15)
    elif confidence == "LOW": prem = min(prem, 1.10)
    elif confidence == "UNRATED": prem = 1.00
    return prem


def p3_discount_rate(score_25, confidence):
    """Dynamic discount rate: risk-free + equity premium + company risk."""
    if confidence == "UNRATED":
        company_risk = 0.05
    elif score_25 >= 23: company_risk = 0.0025
    elif score_25 >= 20: company_risk = 0.01
    elif score_25 >= 17: company_risk = 0.015
    elif score_25 >= 14: company_risk = 0.025
    elif score_25 >= 10: company_risk = 0.035
    else: company_risk = 0.045
    if confidence == "LOW": company_risk += 0.01
    total = RISK_FREE_RATE + EQUITY_RISK_PREMIUM + company_risk
    return total, company_risk


def p3_hold_years(score_25):
    """Quality-linked fade: how long we believe growth holds before fading."""
    if score_25 >= 23: return 5
    if score_25 >= 20: return 4
    if score_25 >= 17: return 3
    if score_25 >= 14: return 2
    return 1


def p3_analyst_growth(ticker, fallback):
    """Analyst-anchored growth: consensus revenue estimates from FMP."""
    try:
        est = fmp_get("analyst-estimates", {"symbol": ticker, "limit": 4})
        if est and isinstance(est, list) and len(est) >= 2:
            est_sorted = sorted(est, key=lambda x: x.get('date', ''))
            revs = [e.get('estimatedRevenueAvg', 0) or e.get('revenueAvg', 0) for e in est_sorted]
            revs = [r for r in revs if r and r > 0]
            if len(revs) >= 2:
                g = (revs[-1] / revs[0]) ** (1 / (len(revs) - 1)) - 1
                if -0.2 < g < 1.0:
                    return max(0.02, min(g, 0.50)), "analyst"
    except Exception:
        pass
    return max(0.04, min(fallback, 0.50)), "historical"


def p3_tam_brake(growth, ticker, prof, inc):
    """TAM reality brake: sustainable growth = industry growth + share-gain room."""
    industry_growth = 0.08
    mkt_share = 0.10
    try:
        sector = (prof[0].get('sector', '') or '').lower() if prof else ''
        industry = (prof[0].get('industry', '') or '').lower() if prof else ''
        if 'semiconductor' in industry or 'technology' in sector and 'hardware' in industry:
            industry_growth = 0.25
        elif 'software' in industry or 'internet' in industry or 'technology' in sector:
            industry_growth = 0.14
        elif 'health' in sector or 'biotech' in industry or 'medical' in industry:
            industry_growth = 0.10
        elif 'consumer' in sector and 'cyclical' in sector:
            industry_growth = 0.06
        elif 'consumer' in sector:
            industry_growth = 0.04
        elif 'industrial' in sector:
            industry_growth = 0.05
        elif 'energy' in sector or 'utilities' in sector:
            industry_growth = 0.03
        elif 'communication' in sector:
            industry_growth = 0.10
        rev = inc[-1].get('revenue', 0) if inc else 0
        if rev > 150e9:  mkt_share = 0.35
        elif rev > 50e9: mkt_share = 0.20
        elif rev > 10e9: mkt_share = 0.10
        else:            mkt_share = 0.04
    except Exception:
        pass
    if mkt_share < 0.05:   room = 0.15
    elif mkt_share < 0.15: room = 0.08
    elif mkt_share < 0.30: room = 0.04
    else:                  room = 0.01
    ceiling = industry_growth + room
    return min(growth, ceiling, 0.50), industry_growth, mkt_share


def p3_dcf_scenario(fcf0, growth, discount, horizon, shares, hold=3):
    """DCF with quality-linked fade."""
    if fcf0 <= 0 or shares <= 0:
        return 0
    if discount <= TERMINAL_GROWTH:
        discount = TERMINAL_GROWTH + 0.03
    hold = min(hold, horizon - 1)
    pv = 0
    fcf = fcf0
    for yr in range(1, horizon + 1):
        if yr <= hold:
            g = growth
        else:
            g = growth - (growth - TERMINAL_GROWTH) * ((yr - hold) / (horizon - hold))
        fcf = fcf * (1 + g)
        pv += fcf / ((1 + discount) ** yr)
    tv = fcf * (1 + TERMINAL_GROWTH) / (discount - TERMINAL_GROWTH)
    pv += tv / ((1 + discount) ** horizon)
    return pv / shares


def p3_full_valuation(ticker):
    """Complete Phase 3 valuation: analyst anchor + TAM brake + quality-linked fade."""
    inc, cf, bs, prof, km = p3_fetch_history(ticker)
    years = len(inc)
    confidence, horizon = p3_data_confidence(years)
    result = {'ticker': ticker, 'years': years, 'confidence': confidence, 'horizon': horizon}

    if confidence == "UNRATED":
        result['signal'] = "⚠️ DATA INSUFF"
        result['note'] = f"Only {years} year(s) of history. Reassess after 2+ years."
        return result

    score_25, factors, metrics = p3_quality_score(inc, cf, bs, km, years)
    result['quality_score'] = score_25
    result['factors'] = factors
    result['metrics'] = metrics

    premium = p3_premium(score_25, confidence)
    disc, company_risk = p3_discount_rate(score_25, confidence)
    result['premium'] = premium
    result['discount_rate'] = disc
    result['company_risk'] = company_risk

    price = 0; shares = 0; company_name = ticker
    try:
        if prof and isinstance(prof, list):
            price = prof[0].get('price', 0) or 0
            mktcap = prof[0].get('mktCap', 0) or prof[0].get('marketCap', 0) or 0
            company_name = prof[0].get('companyName', ticker)
            if price > 0:
                shares = mktcap / price
    except Exception:
        pass
    if shares <= 0:
        try:
            shares = inc[-1].get('weightedAverageShsOut', 0) or 0
        except Exception:
            pass
    result['price'] = price
    result['company'] = company_name

    fcf0 = 0
    try:
        recent_fcf = [c.get('freeCashFlow', 0) for c in cf[-3:]]
        fcf0 = recent_fcf[-1] if recent_fcf else 0
        if fcf0 <= 0 and len(recent_fcf) >= 2:
            fcf0 = sum(recent_fcf) / len(recent_fcf)
    except Exception:
        pass
    fcf0 = fcf0 * stmt_fx(cf)

    if fcf0 <= 0 or shares <= 0 or price <= 0:
        result['signal'] = "⚠️ DATA INSUFF"
        result['note'] = "Missing FCF, shares, or price data."
        return result

    analyst_g, g_source = p3_analyst_growth(ticker, metrics['rev_cagr'] / 100)
    braked_g, ind_growth, mkt_share = p3_tam_brake(analyst_g, ticker, prof, inc)
    hold = p3_hold_years(score_25)
    result['analyst_growth'] = analyst_g
    result['growth_source'] = g_source
    result['braked_growth'] = braked_g
    result['industry_growth'] = ind_growth
    result['mkt_share_proxy'] = mkt_share
    result['hold_years'] = hold

    if confidence == "HIGH":     w = (0.25, 0.50, 0.25)
    elif confidence == "MEDIUM": w = (0.30, 0.50, 0.20)
    else:                        w = (0.40, 0.40, 0.20)

    bear = p3_dcf_scenario(fcf0 * 0.85, braked_g * 0.7, disc + 0.01, horizon, shares, hold)
    base = p3_dcf_scenario(fcf0, braked_g, disc, horizon, shares, hold)
    bull = p3_dcf_scenario(fcf0 * 1.10, min(braked_g * 1.2, 0.50), disc - 0.005, horizon, shares, hold)
    intrinsic = bear * w[0] + base * w[1] + bull * w[2]
    fair_value = intrinsic * premium
    result['bear'] = bear
    result['base'] = base
    result['bull'] = bull
    result['weights'] = w
    result['intrinsic'] = intrinsic
    result['fair_value'] = fair_value

    result['review_flag'] = bool(price > 0 and (fair_value > 3 * price or fair_value < 0.2 * price))

    buy_below = fair_value * 0.75
    result['buy_below'] = buy_below
    expected_return = (fair_value - price) / price * 100 if price > 0 else 0
    result['expected_return'] = expected_return

    if result['review_flag']:
        result['signal'] = "⚠️ DATA CHECK"
        result['action'] = (f"Fair value ${fair_value:,.0f} vs price ${price:,.2f} — "
                            "gap too large to trust. Verify currency/shares/FCF before acting.")
    elif price <= buy_below:
        result['signal'] = "🟢 BUY"
        result['action'] = f"Strong buy — {expected_return:.0f}% upside to fair value"
    elif price <= fair_value:
        result['signal'] = "🟡 HOLD"
        result['action'] = f"Fair value zone — wait for ${buy_below:.0f} entry"
    else:
        result['signal'] = "🔴 AVOID"
        result['action'] = f"Overvalued by {-expected_return:.0f}% — target entry ${buy_below:.0f}"

    if result['signal'] == "🟢 BUY":
        if score_25 >= 20: result['allocation'] = "4-5% of portfolio"
        elif score_25 >= 14: result['allocation'] = "2-3% of portfolio"
        else: result['allocation'] = "1-2% of portfolio"
    else:
        result['allocation'] = "0% — wait for entry price"
    return result


# ═══════════════════════════════════════════════════════════════════════════
# PHASE 3: ETF OPPORTUNITY MONITOR
# ═══════════════════════════════════════════════════════════════════════════
ETF_UNIVERSE = ["SPUS", "HLAL", "SPTE", "SPWO", "UMMA", "SPSK", "ETHS", "HIWO", "ISWD", "ISDW", "WSHR"]
CURRENT_HOLDINGS = ["SPUS", "ETHS"]

FOREIGN_ETF_MAP = {
    "ETHS": {"fmp_alts": ["ETHS.TO"], "yahoo": "ETHS.TO", "name": "iShares Global Halal (TSX)"},
    "HIWO": {"fmp_alts": ["HIWO.L", "HIWO.MI"], "yahoo": "HIWO.L", "name": "HSBC MSCI World Islamic ESG (LSE)"},
    "ISWD": {"fmp_alts": ["ISWD.L"], "yahoo": "ISWD.L", "name": "iShares MSCI World Islamic (LSE)"},
    "ISDW": {"fmp_alts": ["ISDW.L"], "yahoo": "ISDW.L", "name": "iShares MSCI World Islamic Dist (LSE)"},
    "WSHR": {"fmp_alts": ["WSHR.NE", "WSHR.TO"], "yahoo": "WSHR.NE", "name": "Wealthsimple Shariah World (TSX)"},
}


def fetch_price_history(ticker, days=1300):
    """Universal price history fetcher — /stable API with legacy fallback.
    Returns list of {'date','close'} newest-first, or []."""
    try:
        data = fmp_get("historical-price-eod/light", {"symbol": ticker})
        if isinstance(data, list) and len(data) > 0 and data[0].get("price") is not None:
            out = [{"date": d.get("date", ""), "close": float(d.get("price", 0) or 0)} for d in data]
            out = [o for o in out if o["close"] > 0]
            out.sort(key=lambda x: x["date"], reverse=True)
            return out[:days]
    except Exception:
        pass
    try:
        data = fmp_get("historical-price-eod/full", {"symbol": ticker})
        if isinstance(data, list) and len(data) > 0 and data[0].get("close") is not None:
            out = [{"date": d.get("date", ""), "close": float(d.get("close", 0) or 0)} for d in data]
            out = [o for o in out if o["close"] > 0]
            out.sort(key=lambda x: x["date"], reverse=True)
            return out[:days]
    except Exception:
        pass
    try:
        hist = fmp_get("historical-price-full", {"symbol": ticker, "serietype": "line"})
        if isinstance(hist, dict) and "historical" in hist:
            out = [{"date": d.get("date", ""), "close": float(d.get("close", 0) or d.get("adjClose", 0) or 0)}
                   for d in hist["historical"]]
            out = [o for o in out if o["close"] > 0]
            out.sort(key=lambda x: x["date"], reverse=True)
            return out[:days]
    except Exception:
        pass
    return []


def fetch_yahoo_prices(yahoo_symbol, years=5):
    """Yahoo Finance fallback for non-US listings. Returns (prices, status_msg)."""
    try:
        import urllib.request, json as _json
        url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}"
               f"?range={years}y&interval=1d")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = _json.loads(resp.read().decode())
        result = data.get("chart", {}).get("result")
        if not result:
            err = data.get("chart", {}).get("error", {})
            return [], f"Yahoo: no data ({err.get('code','unknown')})"
        res = result[0]
        ts = res.get("timestamp", [])
        closes = res.get("indicators", {}).get("quote", [{}])[0].get("close", [])
        from datetime import datetime as _dt
        out = []
        for t, c in zip(ts, closes):
            if c:
                out.append({"date": _dt.utcfromtimestamp(t).strftime("%Y-%m-%d"), "close": float(c)})
        out.sort(key=lambda x: x["date"], reverse=True)
        if out:
            return out, f"Yahoo: OK ✅ ({yahoo_symbol})"
        return [], "Yahoo: empty response"
    except Exception as e:
        emsg = str(e)[:40]
        if "429" in emsg: return [], "Yahoo: HTTP 429 rate-limited (retry later)"
        if "404" in emsg: return [], f"Yahoo: ticker {yahoo_symbol} not found"
        return [], f"Yahoo: failed ({emsg})"


def fetch_prices_with_diagnosis(ticker):
    """Full chain: FMP → FMP suffixed → Yahoo. Returns (prices, source_trail)."""
    trail = []
    prices = fetch_price_history(ticker, days=1300)
    if prices:
        return prices, "FMP ✅"
    trail.append(f"FMP: no data ({ticker}")
    fmap = FOREIGN_ETF_MAP.get(ticker, {})
    for alt in fmap.get("fmp_alts", []):
        prices = fetch_price_history(alt, days=1300)
        if prices:
            return prices, f"FMP ✅ (as {alt})"
        trail[0] += f", {alt}"
    trail[0] += " tried)"
    yh = fmap.get("yahoo")
    if yh:
        prices, ymsg = fetch_yahoo_prices(yh)
        trail.append(ymsg)
        if prices:
            return prices, " | ".join(trail[:-1] + [ymsg])
    else:
        trail.append("Yahoo: no symbol mapped")
    return [], " | ".join(trail)


def p3_etf_scan(etf_ticker):
    """Score an ETF against MCIS criteria. Returns dict with score + tier."""
    r = {'ticker': etf_ticker, 'score': 0, 'details': {}}
    prof = fmp_get("profile", {"symbol": etf_ticker}) or []
    if not prof or not isinstance(prof, list) or len(prof) == 0:
        fmap = FOREIGN_ETF_MAP.get(etf_ticker, {})
        r['name'] = fmap.get('name', "Non-US listed halal ETF")
        prices, trail = fetch_prices_with_diagnosis(etf_ticker)
        if prices:
            closes = [p['close'] for p in prices]
            r['price'] = closes[0]
            r['p5_high'] = max(closes)
            r['p5_low'] = min(closes)
            r['p5_target'] = min(closes) * 0.95
            if len(prices) >= 200:
                r['perf_1y'] = (closes[0] / closes[min(251, len(closes) - 1)] - 1) * 100
            r['tier'] = "🌍 PRICE-ONLY"
            r['note'] = f"{trail} | No FMP fundamentals — price data only, score N/A"
        else:
            r['tier'] = "⚪ NOT COVERED"
            r['note'] = f"{trail} | → track manually on IBKR"
        r['track'] = 3
        return r

    p = prof[0]
    r['name'] = p.get('companyName', etf_ticker)
    r['price'] = p.get('price', 0)
    ipo = p.get('ipoDate', '') or ''
    r['ipo'] = ipo

    age_years = 0
    try:
        from datetime import datetime as dt
        ipo_dt = dt.strptime(ipo[:10], "%Y-%m-%d")
        age_years = (dt.now() - ipo_dt).days / 365.25
    except Exception:
        pass
    r['age_years'] = age_years

    if age_years < 2:
        perf_1y = 0
        try:
            prices = fetch_price_history(etf_ticker, days=600)
            if len(prices) >= 200:
                perf_1y = (prices[0]['close'] / prices[min(251, len(prices) - 1)]['close'] - 1) * 100
            if prices:
                closes = [p['close'] for p in prices]
                r['p5_high'] = max(closes)
                r['p5_low'] = min(closes)
                r['p5_target'] = min(closes) * 0.95
                r['price'] = prices[0]['close'] or r.get('price', 0)
        except Exception:
            pass
        r['perf_1y'] = perf_1y
        if age_years < 0.25:
            r['tier'] = "🔵 EMERGING"
            r['note'] = f"Launched {age_years*12:.0f} months ago — too new, monitor"
        elif age_years < 1:
            if perf_1y > 15:
                r['tier'] = "🚀 EARLY BIRD"
                r['note'] = f"Strong start (+{perf_1y:.0f}%) — consider 1-3% exploratory position"
            else:
                r['tier'] = "🔵 EMERGING"
                r['note'] = f"{age_years*12:.0f} months old — monitoring performance"
        else:
            r['tier'] = "🟣 DEVELOPING"
            months_to_eval = max(0, (2 - age_years) * 12)
            r['note'] = f"Approaching maturity — formal evaluation in ~{months_to_eval:.0f} months"
        r['track'] = 2
        return r

    score = 0
    details = {}
    details['Halal'] = 10
    score += 10

    name_lower = r['name'].lower()
    if any(k in name_lower for k in ['world', 'global', 'international']):
        details['Diversification'] = 15
    elif any(k in name_lower for k in ['emerging', 'asia', 'europe']):
        details['Diversification'] = 12
    else:
        details['Diversification'] = 8
    score += details['Diversification']

    if age_years >= 10: details['Track Record'] = 20
    elif age_years >= 5: details['Track Record'] = 16
    elif age_years >= 3: details['Track Record'] = 12
    else: details['Track Record'] = 8
    score += details['Track Record']

    details['Access'] = 10 if r['price'] > 0 else 0
    score += details['Access']

    details['Expense'] = 12
    score += 12

    perf_1y = 0
    try:
        prices = fetch_price_history(etf_ticker, days=1300)
        if len(prices) >= 200:
            perf_1y = (prices[0]['close'] / prices[min(251, len(prices) - 1)]['close'] - 1) * 100
        if prices:
            closes = [p['close'] for p in prices]
            r['p5_high'] = max(closes)
            r['p5_low'] = min(closes)
            r['p5_target'] = min(closes) * 0.95
            r['price'] = prices[0]['close'] or r.get('price', 0)
    except Exception:
        pass
    r['perf_1y'] = perf_1y
    if perf_1y > 20: details['Performance'] = 20
    elif perf_1y > 12: details['Performance'] = 16
    elif perf_1y > 6: details['Performance'] = 12
    elif perf_1y > 0: details['Performance'] = 8
    else: details['Performance'] = 4
    score += details['Performance']

    if etf_ticker in CURRENT_HOLDINGS:
        details['Overlap'] = 5
    elif etf_ticker in ["HLAL"]:
        details['Overlap'] = 3
    elif etf_ticker in ["HIWO", "ISWD", "ISDW"]:
        details['Overlap'] = 4
    else:
        details['Overlap'] = 8
    score += details['Overlap']

    r['score'] = score
    r['details'] = details
    r['track'] = 1

    if score >= 80:
        r['tier'] = "🔴 RED ALERT"
        r['note'] = "Strongly recommend — serious consideration for allocation"
    elif score >= 70:
        r['tier'] = "🟡 YELLOW ALERT"
        r['note'] = "Worth reviewing — good candidate"
    elif score >= 60:
        r['tier'] = "🟠 ORANGE ALERT"
        r['note'] = "You decide — meets 60-70% of criteria, trade-offs below"
    elif score >= 40:
        r['tier'] = "🟢 GREEN INFO"
        r['note'] = "Monitor only — not ready"
    else:
        r['tier'] = "⚪ SUPPRESSED"
        r['note'] = "Does not meet criteria — skip"

    if etf_ticker in CURRENT_HOLDINGS:
        r['note'] = "✅ CURRENT HOLDING — " + r['note']
    return r


def analyze_etf_prices(etf_ticker):
    """Fetch and analyze 5-year ETF price history."""
    prices = fetch_price_history(etf_ticker, days=1300)
    if prices:
        current = prices[0]["close"]
        closes = [p["close"] for p in prices]
        if closes and current > 0:
            high_5y = max(closes)
            low_5y = min(closes)
            buy_target = low_5y * 0.95
            return {"current": current, "high": high_5y, "low": low_5y,
                    "target": buy_target, "status": "✅ Data"}
    try:
        quote = fmp_get("quote", {"symbol": etf_ticker})
        if quote and isinstance(quote, list) and len(quote) > 0:
            current = float(quote[0].get("price", 0)) or 0
            if current > 0:
                return {"current": current, "high": current * 1.15, "low": current * 0.75,
                        "target": current * 0.80, "status": "⏳ Estimated"}
    except Exception:
        pass
    return None


def calculate_blended_fair_value(r):
    """Fair Value from 6 weighted methods.

    ⚠️ NOTE: the reverse_dcf term below is `price * 1.05` at a 20% weight, which
    makes the largest single input to Target Entry the current price itself.
    That is partly circular and worth replacing with a real reverse DCF.
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
    gm = float(metrics.get("gm", 0) or 0)

    try:
        valuations["reverse_dcf"] = price * 1.05
    except Exception:
        pass
    try:
        if pe > 1 and pe < 100 and rev_cagr > 1:
            fair_pe = max((rev_cagr / 100) * 1.5 * 100, 10)
            valuations["historical_multiples"] = price * (fair_pe / pe)
    except Exception:
        pass
    try:
        if pe > 1 and rev_cagr > 1:
            valuations["lynch"] = price * (rev_cagr / pe)
    except Exception:
        pass
    try:
        if roic > 15:
            premium = 1.2 + ((roic - 15) / 100) * 0.1
            valuations["buffett"] = price * min(premium, 2.0)
    except Exception:
        pass
    try:
        if gm > 35:
            valuations["fcf_yield"] = price * 1.25
    except Exception:
        pass
    try:
        if gm > 20:
            quality_factor = (gm / 50) ** 0.5
            valuations["graham"] = price * max(quality_factor, 0.8)
    except Exception:
        pass

    if valuations:
        total_weight = sum(weights.get(k, 0) for k in valuations)
        if total_weight > 0:
            blended = sum(valuations[k] * weights.get(k, 0) for k in valuations) / total_weight
            return blended if blended > price * 0.5 else price * 1.1
    return None


def results_to_df(results):
    rows = []
    for r in results:
        m = r.get("metrics", {})
        target_entry = "N/A"
        try:
            price = float(r.get("price", 0) or 0)
            if price > 0:
                fair_value = calculate_blended_fair_value(r)
                if fair_value and fair_value > 1:
                    target_bear = fair_value * 0.50
                    target_base = fair_value * 0.70
                    target_entry = f"${target_bear:,.0f} - ${target_base:,.0f}"
                else:
                    target_bear = price * 0.60
                    target_base = price * 0.80
                    target_entry = f"${target_bear:,.0f} - ${target_base:,.0f}"
        except Exception:
            pass

        r["target_entry"] = target_entry

        try:
            price = float(r.get("price", 0) or 0)
            if target_entry != "N/A" and "-" in target_entry and price > 0:
                range_str = target_entry.replace("$", "").replace(",", "")
                low, high = [float(x.strip()) for x in range_str.split("-")]
                if high > price * 3 or high < price * 0.25:
                    r["signal"] = "⚠️ DATA CHECK"
                elif price <= high:
                    r["signal"] = "🟢 BUY"
                elif price <= high * 1.3:
                    r["signal"] = "🟡 WAIT"
                else:
                    r["signal"] = "🔴 AVOID"
            else:
                r["signal"] = "⚠️ ANALYZE"
        except Exception:
            r["signal"] = "⚠️ ANALYZE"

        rows.append({
            "Ticker":       r["ticker"],
            "Company":      r["name"],
            "Sector":       r["sector"],
            "Score":        r["score"],
            "Tier":         r["verdict"],
            "ROIC%":        m.get("roic", "N/A"),
            "GM%":          m.get("gm", "N/A"),
            "RevCAGR%":     m.get("rev_cagr", "N/A"),
            "Debt/EB":      m.get("debt_ebitda", "N/A"),
            "P/E":          m.get("pe", "N/A"),
            "Price":        f"${r['price']:,.2f}" if r.get('price') else "N/A",
            "Target Entry": target_entry,
            "Mkt Cap":      fmt_mktcap(r.get("mktcap", 0)),
            "Halal":        r.get("halal", "?"),
        })
    return pd.DataFrame(rows)


# ═════════════════════════════════════════════
# PRICE CHART & DATA VALIDATION
# ═════════════════════════════════════════════
@st.cache_data(ttl=3600)
def fetch_historical_prices_yahoo(ticker, days=1825):
    """5 years of historical daily close prices (stable API with legacy fallback)."""
    try:
        prices = fetch_price_history(ticker, days=days)
        if prices:
            return sorted(prices, key=lambda x: x["date"])
        return []
    except Exception:
        return []


def plot_5year_price_chart_yahoo(prices, ticker, current_price=None):
    """Interactive 5-year price chart using Plotly."""
    import plotly.graph_objects as go
    if not prices or len(prices) < 2:
        return None

    if isinstance(prices, dict):
        fig = go.Figure()
        fig.add_annotation(
            text=f"<b>{ticker} Price Summary</b><br>"
                 f"Current: ${prices.get('current_price', 0):,.2f}<br>"
                 f"52W High: ${prices.get('52w_high', 0):,.2f}<br>"
                 f"52W Low: ${prices.get('52w_low', 0):,.2f}",
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
            font=dict(size=14), align="center")
        fig.update_layout(height=300, template="plotly_white", margin=dict(l=50, r=50, t=50, b=50))
        return fig

    dates = [p["date"] for p in prices]
    closes = [float(p["close"]) for p in prices]
    closes_52w = closes[-252:] if len(closes) > 252 else closes
    high_52w = max(closes_52w) if closes_52w else max(closes)
    low_52w = min(closes_52w) if closes_52w else min(closes)
    high_5y = max(closes)
    low_5y = min(closes)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=closes, mode="lines", name="Close Price",
        line=dict(color="#1a3c5e", width=2),
        hovertemplate="<b>%{x}</b><br>Close: $%{y:,.2f}<extra></extra>"))
    fig.add_hline(y=high_52w, line_dash="dash", line_color="#e65100", line_width=1,
                  annotation_text=f"52W High: ${high_52w:,.0f}", annotation_position="right")
    fig.add_hline(y=low_52w, line_dash="dash", line_color="#e65100", line_width=1,
                  annotation_text=f"52W Low: ${low_52w:,.0f}", annotation_position="right")
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
        fmp_data = fetch_company(ticker)
        if not fmp_data.get("ok"):
            return audit
        yf_url = (f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}"
                  "?modules=financialData,incomeStatementHistory")
        yf_resp = requests.get(yf_url, timeout=15)
        yf_data = yf_resp.json()
        if "quoteSummary" not in yf_data or not yf_data["quoteSummary"].get("result"):
            return audit
        yf = yf_data["quoteSummary"]["result"][0]

        fmp_rev = fmp_data.get("income", [])
        yf_rev = yf.get("incomeStatementHistory", {}).get("incomeStatementHistory", [])
        if fmp_rev and yf_rev:
            fmp_val = float(fmp_rev[0].get("revenue") or 0)
            yf_val = float(yf_rev[0].get("totalRevenue", {}).get("raw") or 0)
            if fmp_val and yf_val:
                pct_diff = abs((fmp_val - yf_val) / yf_val) * 100
                audit["matches"]["revenue"] = (f"FMP ${fmp_val/1e9:.1f}B vs Yahoo ${yf_val/1e9:.1f}B "
                                               f"(diff: {pct_diff:.1f}%)")
                if pct_diff > 5:
                    audit["discrepancies"].append(f"Revenue mismatch {pct_diff:.1f}%")

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
# VALUATION ENGINE FUNCTIONS
# ═════════════════════════════════════════════
def _val_inputs(d):
    """Extract the raw numbers the valuation engine needs.
    ★ v1.1: all statement figures converted to USD; shares are ADR-immune."""
    v = {}
    q   = d.get("quote", {})
    bal = d.get("balance", []) or []
    cf  = d.get("cashflow6", []) or []
    inc = d.get("income6", []) or []

    fx = stmt_fx(cf) if cf else stmt_fx(inc)

    v["price"]  = float(q.get("price") or d.get("price") or 0)
    v["mktcap"] = float(q.get("marketCap") or d.get("mktcap") or 0)

    v["shares"] = 0
    if v["price"] and v["mktcap"]:
        v["shares"] = v["mktcap"] / v["price"]
    if not v["shares"]:
        v["shares"] = float(q.get("sharesOutstanding") or 0)

    b0 = bal[0] if bal else {}
    cash = float(b0.get("cashAndShortTermInvestments") or b0.get("cashAndCashEquivalents") or 0)
    debt = float(b0.get("totalDebt") or 0)
    v["net_debt"] = (debt - cash) * fx

    fcf_hist = [float(y["freeCashFlow"]) * fx for y in reversed(cf) if y.get("freeCashFlow") is not None]
    v["fcf_hist"] = fcf_hist

    ttm = d.get("ttm", {}) or {}
    _fcf_ttm = ttm.get("freeCashFlowTTM")
    if _fcf_ttm:
        v["fcf0"] = float(_fcf_ttm) * fx
    else:
        v["fcf0"] = fcf_hist[-1] if fcf_hist else 0
    if not v["fcf0"] and fcf_hist:
        v["fcf0"] = fcf_hist[-1]

    def cagr(series):
        s = [x for x in series if x and x > 0]
        if len(s) >= 3:
            return (s[-1] / s[0]) ** (1 / (len(s) - 1)) - 1
        return None

    v["fcf_cagr"] = cagr(fcf_hist)

    revs = [float(y["revenue"]) * fx for y in reversed(inc) if y.get("revenue")]
    v["rev_hist"] = revs
    v["rev_cagr"] = cagr(revs)

    eps = [float(y["eps"]) for y in reversed(inc) if y.get("eps") is not None]
    v["eps_hist"] = eps
    v["eps_cagr"] = cagr([e for e in eps if e > 0]) if any(e > 0 for e in eps) else None

    v["ni_hist"] = [float(y.get("netIncome") or 0) * fx for y in reversed(inc)]
    v["shares_hist"] = [float(y.get("weightedAverageShsOutDil") or y.get("weightedAverageShsOut") or 0)
                        for y in reversed(inc)]
    return v


def dcf_equity_value(fcf0, g1, wacc, terminal_g, net_debt, fade_years=5, growth_years=5):
    """Two-stage DCF: growth_years at g1, then linear fade to terminal_g, plus TV."""
    if fcf0 <= 0 or wacc <= terminal_g:
        return None, []
    flows, fcf = [], fcf0
    for yr in range(1, growth_years + 1):
        fcf *= (1 + g1)
        flows.append(fcf)
    for i in range(1, fade_years + 1):
        g = g1 + (terminal_g - g1) * i / fade_years
        fcf *= (1 + g)
        flows.append(fcf)
    pv = sum(f / (1 + wacc) ** (i + 1) for i, f in enumerate(flows))
    tv = flows[-1] * (1 + terminal_g) / (wacc - terminal_g)
    pv += tv / (1 + wacc) ** len(flows)
    return pv - net_debt, flows


def reverse_dcf(price, shares, fcf0, wacc, terminal_g, net_debt):
    """Bisection: what growth rate is priced in at the current market price?"""
    if fcf0 <= 0 or not shares or not price:
        return None
    target = price * shares
    lo, hi = -0.10, 0.60
    for _ in range(60):
        mid = (lo + hi) / 2
        ev, _ = dcf_equity_value(fcf0, mid, wacc, terminal_g, net_debt)
        if ev is None:
            return None
        if ev < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def buffett_test(d, v):
    """10-point Buffett quality checklist on real data. Returns (checks, score, max)."""
    checks = []
    met = d.get("metrics6", []) or []
    rat = d.get("ratios", []) or []
    inc = d.get("income6", []) or []

    def add(name, ok, detail):
        checks.append({"check": name, "ok": ok, "detail": detail})

    roics = []
    for y in met:
        r = y.get("returnOnInvestedCapital") or y.get("roic")
        if r is not None:
            roics.append(float(r) * 100)
    add("ROIC ≥ 15% (latest)", bool(roics) and roics[0] >= 15,
        f"{roics[0]:.1f}%" if roics else "n/a")
    add("ROIC ≥ 12% every year (consistency)",
        bool(roics) and len(roics) >= 3 and min(roics[:5]) >= 12,
        f"min {min(roics[:5]):.1f}% over {min(len(roics),5)} yrs" if roics else "n/a")

    gm = None
    for y in rat[:1]:
        g = y.get("grossProfitMargin") or y.get("grossMargin")
        if g is not None:
            gm = float(g) * 100
    if gm is None and inc:
        rev, gp = inc[0].get("revenue"), inc[0].get("grossProfit")
        if rev and gp:
            gm = gp / rev * 100
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
        if x is not None:
            dv = float(x)
            break
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
        cat, note = "Turnaround", ("Earnings currently negative after being positive — thesis depends "
                                   "on recovery, size positions small.")
    elif g_pct is None:
        cat, note = "Unclassified", "Not enough growth history to classify."
    elif g_pct >= 20:
        cat, note = "Fast Grower", ("Lynch's favourite — 20%+ growers. Watch for the growth fade; "
                                    "pay up only with a reasonable PEG.")
    elif g_pct >= 10:
        cat = "Stalwart" if mktcap > 10e9 else "Mid-pace Grower"
        note = ("Solid 10-20% grower. Lynch expects 30-50% gains then rotate — "
                "do not expect a ten-bagger.")
    elif sector in cyclical_sectors:
        cat, note = "Cyclical", ("Earnings follow the economic cycle — low P/E can be a TOP not a "
                                 "bottom. Time the cycle, not the P/E.")
    else:
        cat, note = "Slow Grower", ("Sub-10% growth — only interesting for dividends. Rarely a fit "
                                    "for MCIS Tier 1.")

    peg = None
    if pe and g_pct and g_pct > 0:
        peg = pe / g_pct
    if peg is None:  peg_verdict = "PEG unavailable"
    elif peg <= 1.0: peg_verdict = "PEG ≤ 1.0 — attractively priced for its growth (Lynch buy zone)"
    elif peg <= 1.5: peg_verdict = "PEG 1.0-1.5 — fairly priced"
    elif peg <= 2.0: peg_verdict = "PEG 1.5-2.0 — expensive, needs execution"
    else:            peg_verdict = "PEG > 2.0 — priced for perfection"
    return cat, note, peg, peg_verdict, g_pct


def moat_assessment(d, v):
    """Quantitative moat evidence score 0-10."""
    ev, score = [], 0
    rat = d.get("ratios", []) or []
    gms = []
    for y in rat:
        g = y.get("grossProfitMargin") or y.get("grossMargin")
        if g is not None:
            gms.append(float(g) * 100)
    if gms:
        avg = sum(gms) / len(gms)
        if avg >= 50:
            score += 2; ev.append(f"🟢 Avg gross margin {avg:.0f}% — strong pricing power (+2)")
        elif avg >= 35:
            score += 1; ev.append(f"🟡 Avg gross margin {avg:.0f}% — decent (+1)")
        else:
            ev.append(f"🔴 Avg gross margin {avg:.0f}% — weak pricing power (+0)")
        if len(gms) >= 3 and (max(gms) - min(gms)) <= 6:
            score += 1; ev.append(f"🟢 Margin stability — range only {max(gms)-min(gms):.1f} pts (+1)")

    met = d.get("metrics6", []) or []
    roics = [float(y.get("returnOnInvestedCapital") or y.get("roic") or 0) * 100
             for y in met if (y.get("returnOnInvestedCapital") or y.get("roic")) is not None]
    if roics:
        if min(roics[:5]) >= 15 and len(roics) >= 3:
            score += 3
            ev.append(f"🟢 ROIC ≥ 15% every year for {min(len(roics),5)} yrs — durable advantage (+3)")
        elif roics[0] >= 15:
            score += 2; ev.append(f"🟡 ROIC {roics[0]:.0f}% now but not consistently (+2)")
        elif roics[0] >= 10:
            score += 1; ev.append(f"🟡 ROIC {roics[0]:.0f}% — average business (+1)")
        else:
            ev.append(f"🔴 ROIC {roics[0]:.0f}% — no evidence of moat (+0)")

    if v["fcf_hist"] and v["rev_hist"]:
        fm = v["fcf_hist"][-1] / v["rev_hist"][-1] * 100
        if fm >= 20:
            score += 2; ev.append(f"🟢 FCF margin {fm:.0f}% — cash machine (+2)")
        elif fm >= 10:
            score += 1; ev.append(f"🟡 FCF margin {fm:.0f}% (+1)")
        else:
            ev.append(f"🔴 FCF margin {fm:.0f}% (+0)")

    if v["rev_cagr"] is not None and v["rev_cagr"] >= 0.10:
        score += 2
        ev.append(f"🟢 Revenue compounding at {v['rev_cagr']*100:.0f}% — moat is widening (+2)")

    rating = "WIDE MOAT" if score >= 8 else ("NARROW MOAT" if score >= 5 else "NO MOAT EVIDENCE")
    return rating, score, ev


# ═════════════════════════════════════════════
# COMPANY DOSSIER PDF GENERATOR
# Professional 2-page institutional dossier
# ═════════════════════════════════════════════
def _format_number(v, sym="$"):
    """Format large numbers. `sym` is the reporting-currency prefix, not always '$'."""
    if v is None or v == 0:
        return "—"
    try:
        v = float(v)
    except Exception:
        return "—"
    if abs(v) >= 1e9:
        return f"{sym}{v/1e9:.1f}B"
    if abs(v) >= 1e6:
        return f"{sym}{v/1e6:.1f}M"
    if abs(v) >= 1e3:
        return f"{sym}{v/1e3:.1f}K"
    return f"{sym}{v:,.0f}"


def _pct(v):
    if v is None or v == "N/A":
        return "—"
    return f"{float(v)*100:.1f}%" if isinstance(v, (int, float)) else "—"


def _tbl_rows(d, keys, years=5):
    """Return (rows, year_labels) for the most recent `years` statements, oldest-first.

    ★ MCIS v1.1.2 FIXES:
      - was `list(reversed(h))[:years]` = the OLDEST n, dropping the latest year
      - only ever looked at keys[0]; the fallback key was dead code
      - year labels are now read from each statement's own `date` field instead
        of being generated from datetime.now()
    """
    h = []
    for k in keys:
        cand = d.get(k) or []
        if isinstance(cand, dict):
            cand = [cand]
        if isinstance(cand, list) and len(cand) > len(h):
            h = cand

    # Sort explicitly by date so ordering never depends on FMP's response order
    h = sorted([x for x in h if isinstance(x, dict)], key=lambda x: x.get("date", "") or "")
    h = h[-years:]                                   # ★ most RECENT n
    labels = [((x.get("date", "") or "")[:4] or "—") for x in h]

    while len(h) < years:                            # pad on the LEFT (older side)
        h.insert(0, {})
        labels.insert(0, "—")
    return h, labels

def generate_dossier_pdf(ticker, d, v, result, buffett_checks, buffett_score, lynch_cat,
                         lynch_note, lynch_peg, moat_rating, moat_score,
                         cio_recommendation, investment_edge, risks_text):
    """Generate a professional 2-page MCIS Company Dossier PDF."""
    import os
    import tempfile
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from datetime import datetime

    output_path = os.path.join(tempfile.gettempdir(), f"{ticker}_dossier.pdf")
    doc = SimpleDocTemplate(output_path, pagesize=letter, topMargin=0.4*inch, bottomMargin=0.35*inch,
                            leftMargin=0.55*inch, rightMargin=0.55*inch)
    story = []
    styles = getSampleStyleSheet()

    t_header = ParagraphStyle('CustomHeader', parent=styles['Heading1'], fontSize=16,
                              textColor=colors.HexColor('#1a3c5e'), spaceAfter=2,
                              fontName='Helvetica-Bold')
    t_subhdr = ParagraphStyle('CustomSubHeader', parent=styles['Heading2'], fontSize=10,
                              textColor=colors.HexColor('#1a3c5e'), spaceAfter=3, spaceBefore=3,
                              fontName='Helvetica-Bold')
    t_normal = ParagraphStyle('CustomNormal', parent=styles['Normal'], fontSize=9,
                              alignment=TA_LEFT, spaceAfter=3)
    t_small  = ParagraphStyle('CustomSmall', parent=styles['Normal'], fontSize=8,
                              textColor=colors.HexColor('#666666'), spaceAfter=2)
    t_warn   = ParagraphStyle('CustomWarn', parent=styles['Normal'], fontSize=8,
                              textColor=colors.HexColor('#b45309'), spaceAfter=4)
    t_fxnote = ParagraphStyle('FxNote', parent=styles['Normal'], fontSize=6.5,
                              textColor=colors.HexColor('#777777'), spaceAfter=3)

    def _tbl_style(body_size=8):
        return TableStyle([
            ('BACKGROUND',     (0, 0), (-1, 0), colors.HexColor('#1a3c5e')),
            ('TEXTCOLOR',      (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN',          (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN',          (0, 0), (0, -1), 'LEFT'),
            ('FONTNAME',       (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE',       (0, 0), (-1, 0), body_size),
            ('FONTSIZE',       (0, 1), (-1, -1), body_size),
            ('BOTTOMPADDING',  (0, 0), (-1, -1), 1.6),
            ('TOPPADDING',     (0, 0), (-1, -1), 1.6),
            ('GRID',           (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
        ])

    # ── Pull the statement blocks (v1.1.2 _tbl_rows: most-recent-n, real labels)
    inc, years_header = _tbl_rows(d, ['income6', 'income'], years=5)
    cf,  cf_years     = _tbl_rows(d, ['cashflow6', 'cashflow'], years=5)
    bal, bal_years    = _tbl_rows(d, ['balance'], years=5)

    # ── Reporting currency
    rep_ccy = "USD"
    try:
        _src = (d.get('income6') or d.get('income') or [])
        if _src and isinstance(_src[0], dict):
            rep_ccy = (_src[0].get('reportedCurrency') or "USD").upper()
    except Exception:
        pass

    # ═══════════════════════════════════════════════════════════════════
    # ★NEW — HISTORICAL FX
    # One rate per statement, taken at that statement's own period end.
    # If ANY year fails to resolve we convert NOTHING and label the whole
    # document in reporting currency. Half-converted tables are worse than
    # unconverted ones because nothing on the page tells you which is which.
    # ═══════════════════════════════════════════════════════════════════
    CONVERT = (rep_ccy != "USD")
    fx_map = {}          # 'YYYY-MM-DD' -> rate
    fx_note_bits = []    # for the footnote under the income table
    fx_missing = []
    fx_stale = False

    if CONVERT:
        all_dates = set()
        for coll in (inc, cf, bal):
            for r_ in coll:
                dt = (r_.get("date") or "")[:10]
                if dt:
                    all_dates.add(dt)
        for dt in sorted(all_dates):
            rate, asof, stale = get_fx_on_date(rep_ccy, dt)
            if rate is None:
                fx_missing.append(dt)
            else:
                fx_map[dt] = rate
                fx_stale = fx_stale or stale
                fx_note_bits.append(f"{dt[:4]}: 1 {rep_ccy} = ${rate:.5f}"
                                    + (f" (as of {asof}{'*' if stale else ''})" if asof != "—" else ""))
        if fx_missing:
            CONVERT = False

    DISPLAY_CCY = "USD" if (rep_ccy == "USD" or CONVERT) else rep_ccy
    SYM = "$" if DISPLAY_CCY == "USD" else f"{rep_ccy} "

    def conv(val, stmt):
        """Reported figure -> display currency, at that statement's own year-end rate."""
        if val is None:
            return None
        try:
            val = float(val)
        except Exception:
            return None
        if not CONVERT:
            return val
        r = fx_map.get((stmt.get("date") or "")[:10])
        return val * r if r else None

    def money(x, paren=False):
        """Format with the display-currency symbol. paren=True -> losses as (1.2B)."""
        if x is None or x == 0:
            return "—"
        try:
            x = float(x)
        except Exception:
            return "—"
        neg = x < 0
        a = abs(x)
        if a >= 1e9:   body = f"{SYM}{a/1e9:.1f}B"
        elif a >= 1e6: body = f"{SYM}{a/1e6:.1f}M"
        elif a >= 1e3: body = f"{SYM}{a/1e3:.1f}K"
        else:          body = f"{SYM}{a:,.0f}"
        if not neg:
            return body
        return f"({body})" if paren else f"-{body}"

    def cell_money(yr, key, paren=False):
        return money(conv(yr.get(key), yr), paren=paren)

    def pct_of_rev(yr, key):
        """Margin from ORIGINAL reported figures — FX-neutral, so unaffected by
        which rate we use (numerator and denominator share the same year)."""
        try:
            rev = float(yr.get("revenue") or 0)
            num = yr.get(key)
            if rev > 0 and num is not None:
                return f"{float(num)/rev*100:.1f}%"
        except Exception:
            pass
        return "—"

    # ── ★NEW: Total Overheads ────────────────────────────────────────
    def overheads(yr):
        """Total operating expenses EXCLUDING cost of revenue.

        Preference order:
          1. FMP's own `operatingExpenses` field
          2. The accounting identity: Gross Profit − Operating Income
          3. Sum of the individual opex components FMP exposes
        D&A is deliberately excluded from (3) — FMP usually already folds it
        into SG&A, and adding it back double-counts.
        """
        ox = yr.get("operatingExpenses")
        if ox is not None:
            try:
                return float(ox)
            except Exception:
                pass
        try:
            gp, oi = yr.get("grossProfit"), yr.get("operatingIncome")
            if gp is not None and oi is not None:
                return float(gp) - float(oi)
        except Exception:
            pass
        total, got = 0.0, False
        for k in ("researchAndDevelopmentExpenses",
                  "sellingGeneralAndAdministrativeExpenses",
                  "sellingAndMarketingExpenses",
                  "generalAndAdministrativeExpenses",
                  "otherExpenses"):
            vv = yr.get(k)
            if vv:
                try:
                    total += float(vv)
                    got = True
                except Exception:
                    pass
        return total if got else None

    def overheads_pct(yr):
        try:
            rev = float(yr.get("revenue") or 0)
            ox = overheads(yr)
            if rev > 0 and ox is not None:
                return f"{ox/rev*100:.1f}%"
        except Exception:
            pass
        return "—"

    # ── ★NEW: the operating -> net bridge in one line ────────────────
    def nonop_and_tax(yr):
        """Net Profit − Operating Income. Everything below the operating line:
        interest and investment income, other income, equity-method results,
        MINUS tax. Positive means the below-the-line items net out in the
        company's favour, which is how net profit can exceed operating income."""
        try:
            ni, oi = yr.get("netIncome"), yr.get("operatingIncome")
            if ni is not None and oi is not None:
                return float(ni) - float(oi)
        except Exception:
            pass
        return None

    # ═══════════════════════════════════════════
    # PAGE 1 — FINANCIAL SNAPSHOT
    # ═══════════════════════════════════════════
    story.append(Paragraph(f"<b>{ticker} — {d.get('name','')}</b>", t_header))
    story.append(Paragraph(f"{d.get('sector','')} | {d.get('industry','')} | "
                           f"Price ${v['price']:,.2f} USD | Market Cap {fmt_mktcap(v['mktcap'])} USD",
                           t_small))

    if rep_ccy != "USD" and CONVERT:
        story.append(Paragraph(
            f"Statements reported in <b>{rep_ccy}</b>, converted to <b>USD</b> at the spot rate "
            f"prevailing at each fiscal year end. Growth percentages are computed on the "
            f"original {rep_ccy} figures so they show business growth, not currency movement.",
            t_small))
    elif rep_ccy != "USD" and not CONVERT:
        story.append(Paragraph(
            # Note: Helvetica has no ⚠ glyph — reportlab renders it as a black box.
            # Bold caps carry the warning instead.
            f"<b>USD CONVERSION UNAVAILABLE.</b> The {rep_ccy}/USD rate could not be retrieved for "
            f"{', '.join(fx_missing[:4])}{'…' if len(fx_missing) > 4 else ''}. "
            f"Every figure below is <b>as reported in {rep_ccy}</b> and is NOT comparable to the USD "
            f"price and market cap above. Do not read these tables as dollars.", t_warn))
    story.append(Spacer(1, 0.06*inch))

    # ── 1. Income Statement ──────────────────────────────────────────
    story.append(Paragraph(f"INCOME STATEMENT (5 YEARS, {DISPLAY_CCY})", t_subhdr))

    growth_label = ("Revenue Growth % (local ccy)" if (rep_ccy != "USD" and CONVERT)
                    else "Revenue Growth %")

    inc_specs = [
        ("Revenue",                  lambda i, yr: cell_money(yr, "revenue")),
        (growth_label,               "__growth__"),
        ("Gross Profit",             lambda i, yr: cell_money(yr, "grossProfit")),
        ("Gross Margin %",           lambda i, yr: pct_of_rev(yr, "grossProfit")),
        ("Total Overheads",          lambda i, yr: money(conv(overheads(yr), yr))),          # ★NEW
        ("Overheads % of Revenue",   lambda i, yr: overheads_pct(yr)),                        # ★NEW
        ("Operating Income",         lambda i, yr: cell_money(yr, "operatingIncome", True)),
        ("Operating Margin %",       lambda i, yr: pct_of_rev(yr, "operatingIncome")),
        ("Non-Operating & Tax, net", lambda i, yr: money(conv(nonop_and_tax(yr), yr), True)), # ★NEW
        ("Net Profit / (Loss)",      lambda i, yr: cell_money(yr, "netIncome", True)),        # ★NEW label
        ("Net Margin %",             lambda i, yr: pct_of_rev(yr, "netIncome")),
        ("EPS",                      "__eps__"),
    ]

    inc_rows = [["Metric"] + years_header]
    for label, fn in inc_specs:
        row = [label]
        for i, yr in enumerate(inc):
            if fn == "__growth__":
                # Computed on ORIGINAL reported figures — no FX contamination.
                try:
                    prev = float(inc[i-1].get("revenue") or 0) if i > 0 else 0
                    cur = float(yr.get("revenue") or 0)
                    row.append(f"{(cur/prev - 1)*100:.1f}%" if prev > 0 and cur else "—")
                except Exception:
                    row.append("—")
            elif fn == "__eps__":
                val = conv(yr.get("eps"), yr)
                if val is None:
                    row.append("—")
                else:
                    row.append(f"({SYM}{abs(val):.2f})" if val < 0 else f"{SYM}{val:.2f}")
            else:
                row.append(fn(i, yr))
        inc_rows.append(row)

    inc_tbl = Table(inc_rows, colWidths=[1.55*inch] + [0.92*inch]*5)
    inc_tbl.setStyle(_tbl_style(7.5))
    story.append(inc_tbl)

    story.append(Paragraph(
        "Total Overheads = operating expenses excl. cost of revenue. Non-Operating &amp; Tax, net = "
        "Net Profit − Operating Income (interest/investment/other income, less tax) — a positive "
        "figure is why net profit can exceed operating income.", t_fxnote))
    if CONVERT and fx_note_bits:
        story.append(Paragraph("FX applied — " + " | ".join(fx_note_bits)
                               + ("   *earliest rate on record; statement predates available history."
                                  if fx_stale else ""), t_fxnote))
    story.append(Spacer(1, 0.04*inch))

    # ── 2. Cash Flow Statement ───────────────────────────────────────
    rev_by_year = {}
    for _r in inc:
        _y = (_r.get("date", "") or "")[:4]
        try:
            if _y and _r.get("revenue"):
                rev_by_year[_y] = float(_r["revenue"])
        except Exception:
            pass

    story.append(Paragraph(f"CASH FLOW STATEMENT (5 YEARS, {DISPLAY_CCY})", t_subhdr))
    cf_rows = [["Metric"] + cf_years]
    for label, key in [
        ("Operating Cash Flow", "operatingCashFlow"),
        ("Capital Expenditure", "capitalExpenditure"),
        ("Free Cash Flow",      "freeCashFlow"),
        ("FCF Margin %",        "__fcf_margin__"),
    ]:
        row = [label]
        for i, yr in enumerate(cf):
            if key == "__fcf_margin__":
                try:
                    rev = rev_by_year.get(cf_years[i], 0)
                    fcf_v = yr.get("freeCashFlow")
                    row.append(f"{float(fcf_v)/rev*100:.1f}%" if rev > 0 and fcf_v is not None else "—")
                except Exception:
                    row.append("—")
            else:
                row.append(cell_money(yr, key, paren=True))
        cf_rows.append(row)
    cf_tbl = Table(cf_rows, colWidths=[1.55*inch] + [0.92*inch]*5)
    cf_tbl.setStyle(_tbl_style(7.5))
    story.append(cf_tbl)
    story.append(Spacer(1, 0.04*inch))

    # ── 3. Balance Sheet ─────────────────────────────────────────────
    shares_by_year = {}
    for _r in inc:
        _y = (_r.get("date", "") or "")[:4]
        _s = _r.get("weightedAverageShsOutDil") or _r.get("weightedAverageShsOut")
        try:
            if _y and _s:
                shares_by_year[_y] = float(_s)
        except Exception:
            pass

    story.append(Paragraph(f"BALANCE SHEET & CAPITAL STRUCTURE (5 YEARS, {DISPLAY_CCY})", t_subhdr))
    bal_rows = [["Metric"] + bal_years]
    for label, key in [
        ("Cash & Equivalents",     "cashAndShortTermInvestments"),
        ("Total Debt",             "totalDebt"),
        ("Net Debt",               "__net_debt__"),
        ("Shareholders' Equity",   "totalStockholdersEquity"),
        ("Shares Outstanding (M)", "__shares__"),
    ]:
        row = [label]
        for i, yr in enumerate(bal):
            if key == "__net_debt__":
                try:
                    cash = float(yr.get("cashAndShortTermInvestments")
                                 or yr.get("cashAndCashEquivalents") or 0)
                    debt = float(yr.get("totalDebt") or 0)
                    row.append(money(conv(debt - cash, yr), paren=True) if (cash or debt) else "—")
                except Exception:
                    row.append("—")
            elif key == "__shares__":
                s = shares_by_year.get(bal_years[i])
                row.append(f"{s/1e6:,.0f}M" if s else "—")   # share COUNT — never FX-converted
            else:
                row.append(cell_money(yr, key))
        bal_rows.append(row)
    bal_tbl = Table(bal_rows, colWidths=[1.75*inch] + [0.86*inch]*5)
    bal_tbl.setStyle(_tbl_style(7.5))
    story.append(bal_tbl)
    story.append(Spacer(1, 0.04*inch))

    # ── 4. Key Ratios ────────────────────────────────────────────────
    m = result.get("metrics", {})

    nm_val = m.get("nm")
    if nm_val is None:
        try:
            _last = inc[-1] if inc else {}
            _rev = float(_last.get("revenue") or 0)
            _ni = _last.get("netIncome")
            if _rev > 0 and _ni is not None:
                nm_val = round(float(_ni) / _rev * 100, 1)
        except Exception:
            pass

    fcfm_val = m.get("fcf_margin")
    if fcfm_val is None:
        try:
            _lastcf = cf[-1] if cf else {}
            _rev = rev_by_year.get(cf_years[-1], 0)
            _fcf = _lastcf.get("freeCashFlow")
            if _rev > 0 and _fcf is not None:
                fcfm_val = round(float(_fcf) / _rev * 100, 1)
        except Exception:
            pass

    # ★NEW: overheads ratio in the summary block too
    ovh_val = None
    try:
        _last = inc[-1] if inc else {}
        _rev = float(_last.get("revenue") or 0)
        _ox = overheads(_last)
        if _rev > 0 and _ox is not None:
            ovh_val = round(_ox / _rev * 100, 1)
    except Exception:
        pass

    def _r(val, suffix=""):
        return f"{val}{suffix}" if val is not None else "—"

    ratio_rows = [
        ["ROIC",                  _r(m.get('roic'), "%")],
        ["Gross Margin",          _r(m.get('gm'), "%")],
        ["Overheads % of Revenue", _r(ovh_val, "%")],      # ★NEW
        ["Net Margin",            _r(nm_val, "%")],
        ["FCF Margin",            _r(fcfm_val, "%")],
        ["Debt/EBITDA",           _r(m.get('debt_ebitda'), "x")],
        ["P/E Ratio",             _r(m.get('pe'), "x")],
        ["EV/EBITDA",             _r(m.get('ev_ebitda'), "x")],
    ]
    ratio_tbl = Table(ratio_rows, colWidths=[1.9*inch, 1.6*inch])
    ratio_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME',      (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, -1), 8),
        ('GRID',          (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1.6),
        ('TOPPADDING',    (0, 0), (-1, -1), 1.6),
    ]))
    # ── 5. Price & Valuation (always USD — v uses stmt_fx internally) ─
    # ★ v1.1.3: ratios and price sit SIDE BY SIDE so page 1 still fits on one
    # page after the three new income-statement lines were added.
    fv_per_share, margin_of_safety, dcf_flag = "N/A", "N/A", ""
    try:
        if v.get("fcf0", 0) > 0 and v.get("shares", 0) > 0:
            fcf0, shares, price = v["fcf0"], v["shares"], v["price"]
            wacc, tg = 0.08, 0.025
            g1 = min(max(v.get("rev_cagr") or 0.10, 0.04), 0.25)
            pv_stage1 = sum(fcf0 * ((1 + g1) ** yr) / ((1 + wacc) ** yr) for yr in range(1, 6))
            fcf_year5 = fcf0 * ((1 + g1) ** 5)
            tv = (fcf_year5 * (1 + tg) / (wacc - tg)) / ((1 + wacc) ** 5)
            fv_ps = ((pv_stage1 + tv) - v.get("net_debt", 0)) / shares if shares > 0 else 0
            if fv_ps > 0:
                fv_per_share = f"${fv_ps:,.2f}"
                mos = ((fv_ps - price) / price) * 100 if price > 0 else 0
                margin_of_safety = f"{mos:+.1f}%"
                if price > 0 and (fv_ps > 3 * price or fv_ps < 0.2 * price):
                    dcf_flag = "DATA CHECK — fair value detached from price; verify currency/shares/FCF."
    except Exception:
        pass

    price_info = [
        ["Current Price",    f"${v['price']:,.2f}"],
        ["Fair Value (DCF)", fv_per_share],
        ["Margin of Safety", margin_of_safety],
        ["Market Cap",       fmt_mktcap(v['mktcap'])],
        ["MCIS Score",       f"{result['score']}/100"],
        ["MCIS Verdict",     result['verdict']],
        ["Halal Status",     result.get('halal', '?')],
    ]
    price_tbl = Table(price_info, colWidths=[1.9*inch, 1.6*inch])
    price_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME',      (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, -1), 8),
        ('GRID',          (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1.6),
        ('TOPPADDING',    (0, 0), (-1, -1), 1.6),
    ]))
    _hdr_row = Table([[Paragraph("KEY FINANCIAL RATIOS", t_subhdr),
                       Paragraph("PRICE & VALUATION METRICS (USD)", t_subhdr)]],
                     colWidths=[3.6*inch, 3.6*inch])
    _hdr_row.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    _side_by_side = Table([[ratio_tbl, price_tbl]], colWidths=[3.6*inch, 3.6*inch])
    _side_by_side.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (0, -1), 0),
        ('RIGHTPADDING', (1, 0), (1, -1), 0),
    ]))
    from reportlab.platypus import KeepTogether
    story.append(KeepTogether([_hdr_row, _side_by_side]))
    if dcf_flag:
        story.append(Paragraph(f"<b>{dcf_flag}</b>", t_warn))

    story.append(PageBreak())

    # ═══════════════════════════════════════════
    # PAGE 2 — INVESTMENT ANALYSIS
    # ═══════════════════════════════════════════
    story.append(Paragraph(f"<b>INVESTMENT ANALYSIS — {ticker}</b>", t_header))
    story.append(Spacer(1, 0.1*inch))

    story.append(Paragraph("VALUATION FRAMEWORK", t_subhdr))
    val_data = [
        ["DCF (Base Case)",      "See Valuation Engine for full model"],
        ["Reverse DCF",          "Market growth expectations embedded in price"],
        ["Historical P/E",       _r(m.get('pe'), "x")],
        ["Historical EV/EBITDA", _r(m.get('ev_ebitda'), "x")],
        ["PEG Ratio",            f"{lynch_peg:.2f}" if lynch_peg else "N/A"],
        ["Margin of Safety",     margin_of_safety],
    ]
    val_tbl = Table(val_data, colWidths=[2*inch, 2.5*inch])
    val_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('ALIGN',         (0, 0), (-1, -1), 'LEFT'),
        ('FONTSIZE',      (0, 0), (-1, -1), 8),
        ('GRID',          (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING',    (0, 0), (-1, -1), 3),
    ]))
    story.append(val_tbl)
    story.append(Spacer(1, 0.1*inch))

    story.append(Paragraph("BUFFETT QUALITY TEST (10 CHECKS)", t_subhdr))
    story.append(Paragraph(f"<b>Score: {buffett_score}/10</b> | " +
                           ("WONDERFUL COMPANY" if buffett_score >= 8 else
                            "GOOD COMPANY" if buffett_score >= 6 else
                            "AVERAGE" if buffett_score >= 4 else "AVOID"), t_normal))
    for c in buffett_checks:
        story.append(Paragraph(f"<b>{'✓' if c['ok'] else '✗'} {c['check']}</b> — {c['detail']}", t_small))
    story.append(Spacer(1, 0.08*inch))

    story.append(Paragraph("PETER LYNCH CLASSIFICATION", t_subhdr))
    story.append(Paragraph(f"<b>{lynch_cat}</b>", t_normal))
    story.append(Paragraph(lynch_note, t_small))
    story.append(Spacer(1, 0.08*inch))

    story.append(Paragraph("COMPETITIVE MOAT", t_subhdr))
    story.append(Paragraph(f"<b>{moat_rating} ({moat_score}/10)</b>", t_normal))
    story.append(Spacer(1, 0.08*inch))

    story.append(Paragraph("MATERIAL RISKS", t_subhdr))
    if risks_text:
        for line in risks_text.split("\n")[:5]:
            if line.strip():
                story.append(Paragraph(f"• {line.strip()}", t_small))
    else:
        story.append(Paragraph("• No risks documented", t_small))
    story.append(Spacer(1, 0.08*inch))

    story.append(Paragraph("INVESTMENT EDGE", t_subhdr))
    story.append(Paragraph(investment_edge if investment_edge
                           else "[Investment edge not yet documented]", t_small))
    story.append(Spacer(1, 0.08*inch))

    story.append(Paragraph("CIO RECOMMENDATION", t_subhdr))
    _hex = ('1b5e20' if cio_recommendation == 'BUY' else
            '006064' if cio_recommendation == 'HOLD' else
            'e65100' if cio_recommendation == 'WATCH' else 'b71c1c')
    story.append(Paragraph(f"<font color='#{_hex}'><b>{cio_recommendation}</b></font>", t_normal))
    story.append(Spacer(1, 0.08*inch))

    story.append(Paragraph("PORTFOLIO ALLOCATION", t_subhdr))
    story.append(Paragraph("[To be determined by CIO based on position sizing framework]", t_small))
    story.append(Spacer(1, 0.12*inch))

    _ccy_footer = (f"Statements in {rep_ccy} converted to USD at each fiscal year-end spot rate"
                   if (rep_ccy != "USD" and CONVERT)
                   else f"Statements as reported in {rep_ccy} — USD conversion unavailable"
                   if rep_ccy != "USD" else "All figures USD")
    story.append(Paragraph(f"MCIS Company Dossier | Generated {datetime.now().strftime('%B %d, %Y')} | "
                           f"Blueprint v1.2 | {_ccy_footer} | Not investment advice",
                           ParagraphStyle('Footer', parent=styles['Normal'], fontSize=7,
                                          textColor=colors.HexColor('#999999'), alignment=TA_CENTER)))
    doc.build(story)
    return output_path


# ═════════════════════════════════════════════
# QUALITATIVE ALERT SYSTEM — engine
# FMP stable: news, insider trading + SEC EDGAR fallback
# ═════════════════════════════════════════════
CRITICAL_KW = ["sec investigation", "doj", "fraud", "subpoena", "restatement", "restate",
               "bankruptcy", "chapter 11", "delisting", "going concern", "resigns", "resignation",
               "steps down", "stepping down", "abrupt departure", "cuts guidance", "lowers guidance",
               "slashes guidance", "withdraws guidance", "accounting irregular", "short seller report",
               "material weakness", "default", "criminal"]
WARNING_KW = ["lawsuit", "class action", "layoffs", "job cuts", "downgrade", "downgrades",
              "misses estimates", "earnings miss", "revenue miss", "data breach", "cyberattack",
              "recall", "probe", "investigation", "fine", "penalty", "antitrust", "strike",
              "dilution", "secondary offering", "insider selling", "warns", "profit warning",
              "loses contract", "delay", "halted"]
POSITIVE_KW = ["beats estimates", "raises guidance", "upgrade", "upgrades", "buyback",
               "share repurchase", "new contract", "partnership", "fda approval", "record revenue",
               "dividend increase", "insider buying", "acquisition of", "expands"]

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
    if not isinstance(raw, list):
        return []
    cutoff = (datetime.now() - pd.Timedelta(days=days)).strftime("%Y-%m-%d")
    out = []
    for t in raw:
        d = t.get("transactionDate") or t.get("filingDate") or ""
        if d and d >= cutoff:
            out.append(t)
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
    to = datetime.now().strftime("%Y-%m-%d")
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
    if not filings:
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
        ad = (t.get("acquisitionOrDisposition") or "").upper()
        qty = float(t.get("securitiesTransacted") or 0)
        px = float(t.get("price") or 0)
        val = qty * px
        if typ.startswith("S") or ad == "D":
            sells.append(t); sell_val += val
        elif typ.startswith("P") or ad == "A":
            buys.append(t); buy_val += val

    exec_sells = [t for t in sells if any(k in (t.get("typeOfOwner") or "").lower()
                  for k in ["chief executive", "ceo", "chief financial", "cfo", "president"])]
    if len(sells) >= 4:
        alerts.append(("WARNING", f"Cluster selling — {len(sells)} insider sales in 90 days (${sell_val/1e6:.1f}M)"))
    if any(float(t.get("securitiesTransacted") or 0) * float(t.get("price") or 0) > 5_000_000 for t in exec_sells):
        alerts.append(("WARNING", "CEO/CFO sale above $5M in the last 90 days"))
    if buy_val > 1_000_000 and buy_val > sell_val:
        alerts.append(("POSITIVE", f"Net insider BUYING — ${buy_val/1e6:.1f}M bought vs ${sell_val/1e6:.1f}M sold"))

    return {"n_sells": len(sells), "n_buys": len(buys),
            "sell_val": sell_val, "buy_val": buy_val, "alerts": alerts}


def run_alert_scan(tickers, news_days=30, insider_days=90, filing_days=60):
    out = {}
    for tk in tickers:
        entry = {"news_alerts": [], "insider": {}, "filing_alerts": [], "all": []}
        for n in fetch_news(tk, news_days):
            title = n.get("title") or ""
            sev, kw = classify_headline(title)
            if sev:
                a = {"sev": sev, "src": "NEWS", "date": (n.get("publishedDate") or "")[:10],
                     "text": title, "why": f"keyword: {kw}", "link": n.get("url") or ""}
                entry["news_alerts"].append(a); entry["all"].append(a)

        ins = analyze_insiders(fetch_insiders(tk, insider_days))
        entry["insider"] = ins
        for sev, msg in ins["alerts"]:
            a = {"sev": sev, "src": "INSIDER", "date": "", "text": msg, "why": "", "link": ""}
            entry["all"].append(a)

        for f in fetch_filings(tk, filing_days):
            for prefix, (sev, why) in FILING_SEVERITY.items():
                if f["form"].upper().startswith(prefix):
                    a = {"sev": sev, "src": "SEC", "date": f["date"],
                         "text": f"{f['form']} filed", "why": why, "link": f["link"]}
                    entry["filing_alerts"].append(a); entry["all"].append(a)
                    break
        out[tk] = entry
    return out


# ─────────────────────────────────────────────
# PAGE: DASHBOARD
# ─────────────────────────────────────────────
if page == "🏠 Dashboard":
    st.markdown("""
    <div class="mcis-header">
        <p class="mcis-title">📊 MCIS Dashboard</p>
        <p class="mcis-subtitle">Majid Capital Investment System — Blueprint v1.2</p>
    </div>
    """, unsafe_allow_html=True)

    results = st.session_state.scan_results
    t1 = [r for r in results if r.get("layer") == "LONG_TERM"]
    t2 = [r for r in results if r.get("layer") == "MID_TERM"]
    t3 = [r for r in results if r.get("layer") == "SWING"]

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{len(results)}</div>'
                    f'<div class="metric-label">Companies Scanned</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-card tier1-card"><div class="metric-value" style="color:#1b5e20">{len(t1)}</div>'
                    f'<div class="metric-label">Tier 1 — Buy</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="metric-card tier2-card"><div class="metric-value" style="color:#006064">{len(t2)}</div>'
                    f'<div class="metric-label">Tier 2 — Watch</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="metric-card tier3-card"><div class="metric-value" style="color:#e65100">{len(t3)}</div>'
                    f'<div class="metric-label">Tier 3 — Monitor</div></div>', unsafe_allow_html=True)
    with c5:
        st.markdown(f'<div class="metric-card cash-card"><div class="metric-value" style="color:#c9a84c">'
                    f'{len(st.session_state.watchlist)}</div>'
                    f'<div class="metric-label">Watchlist</div></div>', unsafe_allow_html=True)

    if st.session_state.last_scan:
        st.caption(f"Last scan: {st.session_state.last_scan}")

    if not results:
        st.markdown("""
        <div class="info-box">
        👆 Go to <b>🔍 Scanner</b> in the sidebar to run your first MCIS market scan.
        The scanner will analyse 300+ companies against MCIS Blueprint v1.2 criteria
        and populate this dashboard with real results.
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background-color: #E3F2FD; border-left: 4px solid #1976D2; padding: 15px;
                    margin-bottom: 20px; border-radius: 4px;">
        <b>📌 Important Distinction:</b><br>
        <b>Tier 1 = QUALITY COMPANIES</b> (excellent fundamentals)<br>
        <b>BUT NOT NECESSARILY BUY PRICES</b> (may be overvalued)<br><br>
        ✅ Use this list to find <b>wonderful companies</b><br>
        💰 Use <b>Valuation Engine</b> to find <b>good entry prices</b><br><br>
        Example: MSFT is Tier 1 (quality) but 🔴 AVOID at $390 (overpriced). Target entry: $147
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="section-header">🟢 READY TO BUY NOW — Action Items</div>',
                    unsafe_allow_html=True)

        # Populate target_entry + signal for ALL results before any filtering
        _ = results_to_df(results)

        buy_now = [r for r in t1 if r.get("signal") == "🟢 BUY"]
        if buy_now:
            st.markdown(f"**🎯 {len(buy_now)} companies ready to buy** — within Target Entry range.")
            df_buy = results_to_df(sorted(buy_now, key=lambda x: x["score"], reverse=True))
            st.dataframe(df_buy[["Ticker", "Company", "Score", "ROIC%", "GM%", "Price", "Target Entry", "Halal"]],
                         use_container_width=True, hide_index=True)
            st.caption("✅ These are your immediate buy candidates. Add to portfolio when capital available.")
        else:
            st.info("⏳ No Tier 1 companies at buy prices right now. Check back after market corrections!")

        st.markdown("---")
        st.markdown('<div class="section-header">💰 Capital Allocation — $5,000 Starting Capital</div>',
                    unsafe_allow_html=True)
        alloc_data = {
            "Layer": ["Halal ETF Core", "Tier 1 Compounders", "Tier 2 Growth", "Swing/Tactical", "Opportunity Cash"],
            "Allocation": ["30%", "25%", "20%", "5%", "20%"],
            "Amount": ["$1,500", "$1,250", "$1,000", "$250", "$1,000"],
            "What to Buy": ["SPUS + SPTE + SPWO", "Top 3-4 Tier 1 companies", "Top 2-3 Tier 2 companies",
                            "Options/special situations", "Money market — deploy on crash"],
        }
        st.dataframe(pd.DataFrame(alloc_data), use_container_width=True, hide_index=True)

        st.markdown('<div class="section-header">💎 Halal ETF Core — 5-Year Price Analysis</div>',
                    unsafe_allow_html=True)
        etf_list = ["SPUS", "SPTE", "SPWO"]
        etf_data = []
        for ticker in etf_list:
            etf_info = analyze_etf_prices(ticker)
            if etf_info:
                current, high, low = etf_info["current"], etf_info["high"], etf_info["low"]
                target = etf_info["target"]
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
        st.markdown('<div class="section-header">🏆 All Tier 1 Companies — With Signals</div>',
                    unsafe_allow_html=True)
        if t1:
            if 'selected_signal_tier1' not in st.session_state:
                st.session_state.selected_signal_tier1 = 'All'

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

            sorted_t1 = sorted(t1, key=lambda x: x["score"], reverse=True)[:15]
            if st.session_state.selected_signal_tier1 == 'All':
                filtered_t1 = sorted_t1
                st.info(f"📊 Showing: {len(filtered_t1)} Tier 1 companies")
            else:
                filtered_t1 = [r for r in sorted_t1 if r.get("signal") == st.session_state.selected_signal_tier1]
                st.info(f"📊 Showing: {len(filtered_t1)} companies with signal "
                        f"'{st.session_state.selected_signal_tier1}'")

            if filtered_t1:
                df_t1 = results_to_df(filtered_t1)
                df_t1["Signal"] = [r.get("signal", "⚠️ ANALYZE") for r in filtered_t1]
                st.dataframe(df_t1[["Ticker", "Company", "Score", "ROIC%", "GM%", "RevCAGR%",
                                    "Price", "Target Entry", "Signal", "Halal"]],
                             use_container_width=True, hide_index=True)
                st.caption("📊 Load in Valuation Engine for detailed analysis.")
            else:
                st.warning(f"No Tier 1 companies found with signal "
                           f"'{st.session_state.selected_signal_tier1}'")
        else:
            st.info("No Tier 1 results yet. Run the scanner first.")

        st.markdown('<div class="section-header">🥈 Tier 2 — Watch (Good Quality, 1 Filter Miss)</div>',
                    unsafe_allow_html=True)
        if t2:
            with st.expander(f"Show {len(t2)} Tier 2 companies", expanded=False):
                t2_sorted = sorted(t2, key=lambda x: x["score"], reverse=True)
                df_t2 = results_to_df(t2_sorted)
                df_t2["Signal"] = [r.get("signal", "⚠️ ANALYZE") for r in t2_sorted]
                st.dataframe(df_t2[["Ticker", "Company", "Score", "ROIC%", "GM%", "RevCAGR%",
                                    "Price", "Target Entry", "Signal", "Halal"]],
                             use_container_width=True, hide_index=True)
                st.caption("💡 Tier 2 = strong fundamentals, one criterion missed. Smaller position size (2-3%).")
        else:
            st.info("No Tier 2 companies in latest scan.")

        st.markdown('<div class="section-header">🥉 Tier 3 — Monitor (Swing / Tactical Candidates)</div>',
                    unsafe_allow_html=True)
        if t3:
            with st.expander(f"Show {len(t3)} Tier 3 companies", expanded=False):
                t3_sorted = sorted(t3, key=lambda x: x["score"], reverse=True)
                df_t3 = results_to_df(t3_sorted)
                df_t3["Signal"] = [r.get("signal", "⚠️ ANALYZE") for r in t3_sorted]
                st.dataframe(df_t3[["Ticker", "Company", "Score", "ROIC%", "GM%", "RevCAGR%",
                                    "Price", "Target Entry", "Signal", "Halal"]],
                             use_container_width=True, hide_index=True)
                st.caption("💡 Tier 3 = swing/tactical only, max 5% of portfolio combined.")
        else:
            st.info("No Tier 3 companies in latest scan.")

        st.markdown('<div class="section-header">💎 Fair Value Opportunities — Quick Glance</div>',
                    unsafe_allow_html=True)
        fv_opps = []
        for r in sorted(t1 + t2, key=lambda x: x["score"], reverse=True)[:15]:
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
                    pv_s1 = sum(fcf * ((1 + g1) ** yr) / ((1 + wacc) ** yr) for yr in range(1, 6))
                    fcf_yr5 = fcf * ((1 + g1) ** 5)
                    tv = (fcf_yr5 * (1 + tg) / (wacc - tg)) / ((1 + wacc) ** 5)
                    fv_ps = ((pv_s1 + tv) - net_debt) / shares
                    if fv_ps > 1:
                        discount = ((fv_ps - price) / price) * 100
                        flag = "⚠️ DATA CHECK" if (fv_ps > 3 * price or fv_ps < 0.2 * price) else ""
                        fv_opps.append({
                            "Ticker": r["ticker"],
                            "Current Price": f"${price:,.2f}",
                            "Fair Value": f"${fv_ps:,.2f}",
                            "Discount": f"{discount:+.0f}%",
                            "Tier": r.get("verdict", ""),
                            "Flag": flag,
                        })
            except Exception:
                pass
        if fv_opps:
            fv_df = pd.DataFrame(fv_opps).sort_values("Discount", ascending=False)
            st.dataframe(fv_df, use_container_width=True, hide_index=True)
            st.caption("💡 Positive discount = undervalued. ⚠️ DATA CHECK = too detached from price — verify.")
        else:
            st.info("Fair Value data appears after full company analysis. See 📄 Company Dossier.")


# ─────────────────────────────────────────────
# PAGE: SCANNER
# ─────────────────────────────────────────────
elif page == "🔍 Scanner":
    st.markdown("""
    <div class="mcis-header">
        <p class="mcis-title">🔍 MCIS Scanner</p>
        <p class="mcis-subtitle">Real-time market scanning against Blueprint v1.2 criteria</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="info-box">
    <b>Scanner uses live FMP data.</b> Applies 5 MCIS filters: ROIC>15%, FCF positive+growing,
    Gross Margin>35%, Revenue CAGR>8%, Debt/EBITDA<3x. Also runs Halal check and No Fly Zone screen.
    Takes approximately 15-25 minutes for full universe.
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])
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
                    except Exception:
                        pass
                universe = list(set([t for t in universe if t and len(t) <= 6]))
            except Exception:
                pass

        t1, t2, t3, rejected, errors = [], [], [], 0, 0
        progress_bar = st.progress(0)
        status_text = st.empty()
        results_text = st.empty()

        for i, ticker in enumerate(universe):
            progress_bar.progress((i + 1) / len(universe))
            status_text.text(f"Scanning {ticker}... ({i+1}/{len(universe)})")
            try:
                data = fetch_company(ticker)
                if not data["ok"]:
                    errors += 1
                    continue
                result = run_filters(data)
                if data.get("fcf"):      result["fcf"] = data["fcf"]
                if data.get("shares"):   result["shares"] = data["shares"]
                if data.get("net_debt"): result["net_debt"] = data["net_debt"]

                if result["layer"] == "LONG_TERM":  t1.append(result)
                elif result["layer"] == "MID_TERM": t2.append(result)
                elif result["layer"] == "SWING":    t3.append(result)
                else:                                rejected += 1

                results_text.markdown(f"**Live results:** 🟢 T1: {len(t1)} | 🔵 T2: {len(t2)} | "
                                      f"🟠 T3: {len(t3)} | ❌ Rejected: {rejected}")
            except Exception as e:
                errors += 1
                if i < 3:
                    status_text.text(f"⚠️ Error fetching {ticker}: {str(e)[:50]}")

        t1.sort(key=lambda x: x["score"], reverse=True)
        t2.sort(key=lambda x: x["score"], reverse=True)
        t3.sort(key=lambda x: x["score"], reverse=True)
        all_results = t1 + t2 + t3
        st.session_state.scan_results = all_results
        st.session_state.last_scan = datetime.now().strftime("%B %d, %Y at %H:%M")
        save_to_disk()

        status_text.text("✅ Scan complete!")
        progress_bar.progress(1.0)
        st.success(f"Scan complete: {len(universe)} companies scanned | "
                   f"Tier 1: {len(t1)} | Tier 2: {len(t2)} | Tier 3: {len(t3)} | "
                   f"Rejected: {rejected} | Errors: {errors}")

        if t1:
            st.markdown('<div class="section-header">🏆 Tier 1 Results — Buy Candidates</div>',
                        unsafe_allow_html=True)
            st.dataframe(results_to_df(t1)[["Ticker", "Company", "Sector", "Score",
                                            "ROIC%", "GM%", "RevCAGR%", "Halal", "Price"]],
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
        col1, col2, col3 = st.columns(3)
        with col1:
            tier_filter = st.multiselect("Filter by Tier", ["TIER 1", "TIER 2", "TIER 3"],
                                         default=["TIER 1", "TIER 2", "TIER 3"])
        with col2:
            halal_filter = st.multiselect("Filter by Halal", ["PASS", "CONDITIONAL", "FAIL"],
                                          default=["PASS", "CONDITIONAL"])
        with col3:
            sector_filter = st.multiselect("Filter by Sector",
                                           list(set(r["sector"] for r in results if r["sector"] != "Unknown")))

        filtered = [r for r in results
                    if r.get("verdict", "") in tier_filter
                    and r.get("halal", "") in halal_filter
                    and (not sector_filter or r.get("sector", "") in sector_filter)]
        filtered.sort(key=lambda x: x["score"], reverse=True)
        st.caption(f"Showing {len(filtered)} of {len(results)} companies")

        if filtered:
            df = results_to_df(filtered)
            st.dataframe(df, use_container_width=True, hide_index=True,
                         column_config={"Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100)})

            st.markdown("---")
            ticker_to_add = st.text_input("Add company to watchlist (enter ticker)")
            if st.button("➕ Add to Watchlist") and ticker_to_add:
                match = next((r for r in filtered if r["ticker"] == ticker_to_add.upper()), None)
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

    available_tickers = sorted(set(r["ticker"] for r in st.session_state.scan_results))
    col1, col2 = st.columns([2, 1])
    with col1:
        if available_tickers:
            ticker_input = st.selectbox("Select company or type ticker", [""] + available_tickers,
                                        index=0, key="lookup_ticker_select")
            if not ticker_input:
                ticker_input = st.text_input("Or enter ticker manually",
                                             placeholder="e.g. NVDA").upper().strip()
        else:
            ticker_input = st.text_input("Enter ticker symbol", placeholder="e.g. NVDA").upper().strip()
            st.caption("💡 Run the Scanner first to populate the dropdown")
    with col2:
        st.empty()

    if st.button("🔍 Analyse Company") and ticker_input:
        with st.spinner(f"Fetching live data for {ticker_input}..."):
            data = fetch_company(ticker_input)

        if not data["ok"]:
            st.error(f"Could not fetch data for {ticker_input}. Check the ticker symbol.")
        else:
            result = run_filters(data)
            m = result.get("metrics", {})

            col1, col2 = st.columns([3, 1])
            with col1:
                st.subheader(f"{result['ticker']} — {result['name']}")
                st.caption(f"{result['sector']} | {data.get('industry','')}")
            with col2:
                verdict = result["verdict"]
                if "TIER 1" in verdict:   st.success(f"✅ {verdict}")
                elif "TIER 2" in verdict: st.info(f"🔵 {verdict}")
                elif "TIER 3" in verdict: st.warning(f"🟠 {verdict}")
                else:                     st.error(f"❌ {verdict}")

            st.markdown('<div class="section-header">Key Metrics</div>', unsafe_allow_html=True)
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            c1.metric("MCIS Score",   f"{result['score']}/100")
            c2.metric("ROIC",         f"{m.get('roic','N/A')}%")
            c3.metric("Gross Margin", f"{m.get('gm','N/A')}%")
            c4.metric("Rev CAGR",     f"{m.get('rev_cagr','N/A')}%")
            c5.metric("Debt/EBITDA",  f"{m.get('debt_ebitda','N/A')}x")
            c6.metric("P/E Ratio",    f"{m.get('pe','N/A')}")

            c1, c2, c3 = st.columns(3)
            c1.metric("Price",      f"${result['price']:,.2f}")
            c2.metric("Market Cap", fmt_mktcap(result.get("mktcap", 0)))
            c3.metric("EV/EBITDA",  f"{m.get('ev_ebitda','N/A')}")

            st.markdown('<div class="section-header">Halal Status</div>', unsafe_allow_html=True)
            h = result.get("halal", "?")
            if h == "PASS":
                st.success(f"✅ HALAL PASS — {result['halal_reason']}")
            elif h == "CONDITIONAL":
                st.warning(f"⚠️ CONDITIONAL — {result['halal_reason']} — Verify on Zoya (zoya.finance)")
            else:
                st.error(f"❌ HALAL FAIL — {result['halal_reason']}")

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
                    st.warning(f"⚠️ FMP price history endpoint not returning data for {ticker_input}")
                    st.caption("Possible reasons: endpoint not on your FMP plan, key still activating, "
                               "or the ticker does not exist. Test historical-price-eod/light in the "
                               "FMP dashboard.")
                st.info(f"Current price from FMP: ${data.get('price', 'N/A')}")

            st.markdown('<div class="section-header">🔍 Data Quality Check</div>', unsafe_allow_html=True)
            validation = validate_financial_data(data, result)
            st.caption(f"FMP Data Quality: {validation['quality_badge']}")
            if validation['flags']:
                for flag in validation['flags']:
                    st.warning(flag)
            else:
                st.success("✓ No data quality issues detected")

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

    auto_buy_candidates = []
    try:
        scan_results = st.session_state.get("scan_results", [])
        for r in scan_results:
            if r.get("verdict") == "TIER 1":
                price = float(r.get("price", 0) or 0)
                target_entry = r.get("target_entry", "N/A")
                if target_entry != "N/A" and "-" in target_entry:
                    try:
                        range_str = target_entry.replace("$", "").replace(",", "")
                        low, high = [float(x.strip()) for x in range_str.split("-")]
                        if high > price * 3 or high < price * 0.25:
                            continue
                        if price <= high:
                            r["buy_signal"] = f"🟢 BUY at ${price:,.2f}"
                            auto_buy_candidates.append(r)
                    except Exception:
                        pass
    except Exception:
        pass

    if auto_buy_candidates:
        st.markdown('<div class="section-header">🟢 Auto-Buy Candidates — Tier 1 at Target Entry</div>',
                    unsafe_allow_html=True)
        st.markdown(f"**{len(auto_buy_candidates)} companies ready to buy** (within Target Entry range)")
        df_auto = results_to_df(auto_buy_candidates)
        st.dataframe(df_auto[["Ticker", "Company", "Score", "Tier", "ROIC%", "GM%",
                              "Price", "Target Entry", "Halal"]],
                     use_container_width=True, hide_index=True)
        st.caption("💡 These Tier 1 companies are at or below your Target Entry price.")

    st.markdown('<div class="section-header">➕ Manual Watchlist</div>', unsafe_allow_html=True)
    col1, col2 = st.columns([3, 1])
    with col1:
        new_ticker = st.text_input("Add ticker to watchlist", placeholder="e.g. ASML").upper().strip()
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Add") and new_ticker:
            with st.spinner(f"Fetching {new_ticker}..."):
                data = fetch_company(new_ticker)
                result = run_filters(data) if data["ok"] else {
                    "ticker": new_ticker, "name": new_ticker, "score": 0, "verdict": "Unknown",
                    "layer": "UNKNOWN", "halal": "?", "halal_reason": "", "passed": [], "failed": [],
                    "warnings": [], "metrics": {}, "price": 0, "mktcap": 0, "sector": "Unknown"}
                if result not in watchlist:
                    st.session_state.watchlist.append(result)
                    st.success(f"{new_ticker} added")

    if not watchlist:
        st.markdown('<div class="info-box">Your manual watchlist is empty. '
                    'Add companies from Rankings or Company Lookup.</div>', unsafe_allow_html=True)
    else:
        st.caption(f"{len(watchlist)} companies on manual watchlist")
        df = results_to_df(watchlist)
        st.dataframe(df[["Ticker", "Company", "Sector", "Score", "Tier", "ROIC%", "GM%",
                         "RevCAGR%", "Halal", "Price", "Target Entry"]],
                     use_container_width=True, hide_index=True,
                     column_config={"Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100)})

        to_remove = st.text_input("Remove ticker from watchlist").upper().strip()
        if st.button("➖ Remove") and to_remove:
            st.session_state.watchlist = [r for r in watchlist if r["ticker"] != to_remove]
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

    st.markdown('<div class="section-header">➕ Add New Swing Trade</div>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1: sw_ticker = st.text_input("Ticker").upper()
    with c2: sw_type   = st.selectbox("Type", ["Call Option", "Put Option", "Long Stock", "Short Stock"])
    with c3: sw_entry  = st.number_input("Entry Price $", min_value=0.0, step=0.01)
    with c4: sw_target = st.number_input("Target Price $", min_value=0.0, step=0.01)
    with c5: sw_stop   = st.number_input("Stop Loss $", min_value=0.0, step=0.01)
    with c6: sw_size   = st.number_input("Position Size $", min_value=0.0, step=10.0)

    sw_thesis = st.text_area("Trade Thesis (required)",
                             placeholder="Why are you entering this trade? What is the catalyst?")
    sw_expiry = st.date_input("Expiry / Exit by Date")

    if st.button("➕ Add Swing Trade"):
        if sw_ticker and sw_entry and sw_target and sw_stop and sw_thesis:
            trade = {
                "ticker": sw_ticker, "type": sw_type, "entry": sw_entry, "target": sw_target,
                "stop": sw_stop, "size": sw_size, "thesis": sw_thesis, "expiry": str(sw_expiry),
                "date": datetime.now().strftime("%Y-%m-%d"), "status": "Open",
                "rr_ratio": round((sw_target - sw_entry) / (sw_entry - sw_stop), 2) if sw_entry != sw_stop else 0,
            }
            st.session_state.swing_trades.append(trade)
            st.success(f"Swing trade added for {sw_ticker}")
        else:
            st.error("Please fill in all fields including thesis before adding")

    if st.session_state.swing_trades:
        st.markdown('<div class="section-header">📊 Open Swing Trades</div>', unsafe_allow_html=True)
        df = pd.DataFrame(st.session_state.swing_trades)
        st.dataframe(df[["ticker", "type", "entry", "target", "stop", "size",
                         "rr_ratio", "expiry", "status", "thesis"]],
                     use_container_width=True, hide_index=True)

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
        <p class="mcis-subtitle">MCIS Blueprint v1.2 — 8-Step Review Process</p>
    </div>
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
         ["SPUS still halal compliant?", "SPTE still tracking correct index?",
          "SPWO fees still competitive?", "Any ETF methodology changes?"]),
        ("Step 2 — Individual Company Fundamentals",
         "Pull latest quarterly earnings. Check revenue growth, ROIC, FCF, management commentary.",
         ["Revenue growth holding above 8%?", "ROIC still above 15%?",
          "FCF still positive and growing?", "Management commentary consistent with thesis?"]),
        ("Step 3 — Valuation Update",
         "Update DCF for each holding. Recalculate margin of safety.",
         ["DCF updated with latest numbers?", "Margin of safety still above 20%?",
          "Any positions stretched above intrinsic value?"]),
        ("Step 4 — Portfolio Weight Check",
         "Check no position exceeds limits. Trim if required.",
         ["Any single stock above 15% of portfolio?", "Any single ETF above 20% of portfolio?",
          "Any single sector above 35%?"]),
        ("Step 5 — Watchlist Ranking Update",
         "Update Tier rankings. Promote or demote based on latest data.",
         ["Tier 1 list updated with latest scan?", "Any Tier 2 companies ready for promotion?",
          "Any Tier 1 companies showing deterioration?"]),
        ("Step 6 — Opportunity Cash Review",
         "Has market created any dislocation worth deploying cash into?",
         ["Market down 15%+ since last review?", "Any specific Tier 1 company down 20%+ with thesis intact?",
          "Opportunity cash still at 10-20% minimum?"]),
        ("Step 7 — Swing Trade Review",
         "Close or roll any swing positions older than 30 days without movement.",
         ["Any open swings older than 30 days?", "Any swings near stop loss?",
          "Swing allocation still within 5% limit?"]),
        ("Step 8 — Written Summary",
         "CIO produces one-page summary. Chairman reviews and approves.",
         ["Summary written?", "Chairman reviewed?", "Next review date set?"]),
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
        for holding in ["SPUS", "SPTE", "SPWO"] + [r["ticker"] for r in st.session_state.watchlist[:5]]:
            v_sel = st.selectbox(f"{holding}", ["HOLD", "ADD", "WATCH", "TRIM", "EXIT", "REVIEW"],
                                 key=f"verdict_{holding}")
    with notes_col:
        st.markdown("**Committee Notes:**")
        notes = st.text_area("", height=200,
                             placeholder="Key observations, decisions and actions from this review...")

    if st.button("✅ Complete Quarterly Review"):
        if all_complete:
            st.success(f"✅ Quarterly Review completed — {review_date.strftime('%B %d, %Y')}")
            st.balloons()
        else:
            st.warning("Some checklist items are incomplete. Review them before finalising.")

    st.markdown("---")
    st.markdown("### 📄 Download Quarterly Report")

    def build_quarterly_report():
        lines = []
        lines.append("=" * 70)
        lines.append("MCIS QUARTERLY REVIEW REPORT")
        lines.append("Majid Capital Investment System — Blueprint v1.2")
        lines.append(f"Review Date: {review_date.strftime('%B %d, %Y')}")
        lines.append(f"Generated: {datetime.now().strftime('%B %d, %Y %H:%M')}")
        lines.append("=" * 70)

        lines.append("\n--- 8-STEP REVIEW CHECKLIST ---")
        done_ct, total_ct = 0, 0
        for step_title, step_desc, checks in steps:
            lines.append(f"\n{step_title}")
            for check in checks:
                total_ct += 1
                st_val = st.session_state.get(f"{step_title}_{check}", False)
                if st_val:
                    done_ct += 1
                lines.append(f"  [{'X' if st_val else ' '}] {check}")
        lines.append(f"\nChecklist completion: {done_ct}/{total_ct} items")

        lines.append("\n--- HOLDINGS VERDICTS ---")
        for holding in ["SPUS", "SPTE", "SPWO"] + [r["ticker"] for r in st.session_state.watchlist[:5]]:
            lines.append(f"  {holding}: {st.session_state.get(f'verdict_{holding}', 'HOLD')}")

        lines.append("\n--- COMMITTEE NOTES ---")
        lines.append(notes if notes else "(none entered)")

        results = st.session_state.get("scan_results", [])
        if results:
            t1r = [r for r in results if r.get("layer") == "LONG_TERM"]
            t2r = [r for r in results if r.get("layer") == "MID_TERM"]
            t3r = [r for r in results if r.get("layer") == "SWING"]
            lines.append("\n--- LATEST SCAN SNAPSHOT ---")
            lines.append(f"Companies in system: {len(results)} | Tier 1: {len(t1r)} | "
                         f"Tier 2: {len(t2r)} | Tier 3: {len(t3r)}")
            buys = [r for r in results if r.get("signal") == "🟢 BUY"]
            waits = [r for r in results if r.get("signal") == "🟡 WAIT"]
            checks_d = [r for r in results if r.get("signal") == "⚠️ DATA CHECK"]
            lines.append(f"Signals: BUY {len(buys)} | WAIT {len(waits)} | DATA CHECK {len(checks_d)}")
            if buys:
                lines.append("\nBUY candidates:")
                for r in sorted(buys, key=lambda x: x.get("score", 0), reverse=True)[:10]:
                    lines.append(f"  {r['ticker']:6s} {r.get('name','')[:30]:32s} "
                                 f"${r.get('price',0):>9,.2f}  Target: {r.get('target_entry','N/A')}")
            if waits:
                lines.append("\nWAIT (approaching entry):")
                for r in sorted(waits, key=lambda x: x.get("score", 0), reverse=True)[:10]:
                    lines.append(f"  {r['ticker']:6s} {r.get('name','')[:30]:32s} "
                                 f"${r.get('price',0):>9,.2f}  Target: {r.get('target_entry','N/A')}")
        else:
            lines.append("\n--- LATEST SCAN SNAPSHOT ---")
            lines.append("No scan data in session. Run Scanner before generating report.")

        lines.append("\n--- NEXT REVIEW ---")
        nxt = {"1": "April", "4": "July", "7": "October", "10": "January"}.get(str(review_date.month),
                                                                              "next quarter")
        lines.append(f"Scheduled: {nxt} (Jan/Apr/Jul/Oct cycle)")
        lines.append("\n" + "=" * 70)
        lines.append("MCIS | Models, not predictions — not investment advice")
        return "\n".join(lines)

    report_txt = build_quarterly_report()
    st.download_button(label="📥 Download Quarterly Report (.txt)", data=report_txt,
                       file_name=f"MCIS_Quarterly_Review_{review_date.strftime('%Y%m%d')}.txt",
                       mime="text/plain", key="dl_quarterly")
    with st.expander("👁 Preview report"):
        st.code(report_txt)


# ─────────────────────────────────────────────
# PAGE: COMPANY DOSSIER
# ─────────────────────────────────────────────
elif page == "📄 Company Dossier":
    st.markdown("""
    <div class="mcis-header">
        <p class="mcis-title">📄 Company Dossier</p>
        <p class="mcis-subtitle">Professional 2-page institutional investment thesis</p>
    </div>
    """, unsafe_allow_html=True)

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

        # ─── ★ MCIS v1.1.3 — FX PRE-FLIGHT (shown in the app, before generating) ───
        _fx = fx_health_check(vd)
        if _fx["needs_fx"] and not _fx["ok"]:
            st.error(
                f"🚨 **FX CONVERSION FAILED — {vd['ticker']} reports in {_fx['ccy']}, not USD.**\n\n"
                f"The {_fx['ccy']}/USD rate could not be retrieved for: "
                f"{', '.join(_fx['missing'][:6])}{'…' if len(_fx['missing']) > 6 else ''}\n\n"
                f"Every financial table below and in the generated dossier will show **{_fx['ccy']} "
                f"as reported** — NOT dollars. Do not compare them to the USD price, market cap or "
                f"fair value on this page. Re-load in a few minutes to retry the rate."
            )
        elif _fx["needs_fx"]:
            _stale_note = " ⚠️ one or more years fall outside available FX history." if _fx["stale"] else ""
            st.success(
                f"💱 **{vd['ticker']} reports in {_fx['ccy']}** — converted to USD at each fiscal "
                f"year-end spot rate.{_stale_note}"
            )
            with st.expander("Show the exact rate applied to each year"):
                st.dataframe(
                    pd.DataFrame([{
                        "Fiscal Year": y,
                        f"1 {_fx['ccy']} =": f"${r:.5f}",
                        "Rate as of": a,
                        "Note": "earliest available — statement predates FX history" if s else "year-end spot",
                    } for y, r, a, s in _fx["rates"]]),
                    use_container_width=True, hide_index=True,
                )
            st.caption(
                "💡 Money columns are USD at each year's own rate. Revenue-growth columns are computed "
                f"on the original {_fx['ccy']} figures, so growth reflects the business rather than "
                "currency movement. Both are labelled on the dossier."
            )

        # ═══════════════════════════════════════════
        # AUTOMATIC BUY/HOLD/AVOID SIGNAL
        # ═══════════════════════════════════════════
        fcf0 = v.get("fcf0", 0)
        shares = v.get("shares", 0)
        net_debt = v.get("net_debt", 0)
        price = v.get("price", 0)
        wacc, tg = 0.08, 0.025
        g1_base = min(max(v.get("rev_cagr", 0.10) or 0.10, 0.04), 0.25)
        mos_req = 50

        auto_signal = "⚠️ ANALYZE"
        signal_detail = "Insufficient data for automatic signal"
        fv_ps = 0

        if fcf0 > 0 and shares > 0 and price > 0:
            try:
                pv_s1 = sum(fcf0 * ((1 + g1_base) ** yr) / ((1 + wacc) ** yr) for yr in range(1, 6))
                fcf_yr5 = fcf0 * ((1 + g1_base) ** 5)
                tv = (fcf_yr5 * (1 + tg) / (wacc - tg)) / ((1 + wacc) ** 5)
                fv_ps = ((pv_s1 + tv) - net_debt) / shares if shares > 0 else 0
                discount = ((fv_ps - price) / price) * 100 if price > 0 else 0
                if fv_ps > 0:
                    if fv_ps > 3 * price or fv_ps < 0.2 * price:
                        auto_signal = "⚠️ DATA CHECK"
                        signal_detail = (f"FV ${fv_ps:,.0f} vs Price ${price:,.2f} — gap too large to "
                                         "trust. Verify currency/shares/FCF before acting.")
                    elif discount >= mos_req:
                        auto_signal = "🟢 BUY"
                        signal_detail = f"Undervalued by {discount:.0f}% (FV: ${fv_ps:,.0f} vs Price: ${price:,.2f})"
                    elif discount >= 0:
                        auto_signal = "🟡 HOLD"
                        signal_detail = f"Fairly valued with {discount:.0f}% upside (FV: ${fv_ps:,.0f})"
                    else:
                        auto_signal = "🔴 AVOID"
                        signal_detail = f"Overvalued by {abs(discount):.0f}% (FV: ${fv_ps:,.0f} vs Price: ${price:,.2f})"
            except Exception:
                pass

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
            st.metric("Fair Value", f"${fv_ps:,.0f}" if fv_ps > 0 else "N/A")

        st.markdown("---")

        checks, buff_score, mx = buffett_test(vd, v)
        cat, note, peg, peg_v, g_pct = lynch_classify(vd, v, pe)
        moat_rat, moat_sc, moat_ev = moat_assessment(vd, v)

        st.markdown('<div class="section-header">⚙️ Complete the investment thesis</div>',
                    unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            cio_rec = st.radio("CIO Recommendation", ["BUY", "HOLD", "WATCH", "AVOID"],
                               horizontal=True, key="cio_rec")
        with c2:
            port_weight = st.number_input("Suggested portfolio weight (%)", min_value=0.0,
                                          max_value=100.0, step=0.5, key="port_w")

        st.markdown('<div class="section-header">Investment Edge (one paragraph)</div>',
                    unsafe_allow_html=True)
        inv_edge = st.text_area("Why is this company better than the other finalists?",
                                placeholder="e.g. 'NVDA's dominant position in AI inference is protected "
                                            "by network effects in software ecosystems...'",
                                height=80, key="inv_edge")

        st.markdown('<div class="section-header">Material Risks (maximum 5, one per line)</div>',
                    unsafe_allow_html=True)
        risks = st.text_area("What could change our investment decision?",
                             placeholder="1. AI demand slowdown\n2. Competitive threat from AMD\n"
                                         "3. Geopolitical export restrictions\n4. Valuation compression\n"
                                         "5. Supply chain disruption",
                             height=100, key="risks")

        st.markdown("---")
        st.markdown('<div class="section-header">📉 5-Year Share Price History</div>',
                    unsafe_allow_html=True)
        try:
            dos_prices = fetch_historical_prices_yahoo(vd['ticker'], days=1825)
            if dos_prices and len(dos_prices) > 1:
                dos_current = float(vd.get("quote", {}).get("price", 0) or 0)
                fig_dos = plot_5year_price_chart_yahoo(dos_prices, vd['ticker'],
                                                       current_price=dos_current or None)
                if fig_dos:
                    st.plotly_chart(fig_dos, use_container_width=True)
                    closes_dos = [p.get("close", 0) for p in dos_prices if p.get("close")]
                    if closes_dos:
                        c1, c2, c3, c4 = st.columns(4)
                        with c1: st.metric("5Y High", f"${max(closes_dos):.2f}")
                        with c2: st.metric("5Y Low", f"${min(closes_dos):.2f}")
                        with c3: st.metric("Current", f"${closes_dos[-1]:.2f}")
                        with c4:
                            off_high = (closes_dos[-1] / max(closes_dos) - 1) * 100
                            st.metric("From 5Y High", f"{off_high:+.1f}%")
                else:
                    st.info("Chart could not be rendered.")
            else:
                st.info("⏳ 5-year price history not available for this ticker.")
        except Exception as e:
            st.warning(f"Price chart error: {str(e)[:80]}")

        st.markdown("---")
        st.markdown('<div class="section-header">🏛 Phase 3 Valuation — Institutional DCF Analysis</div>',
                    unsafe_allow_html=True)
        if st.button("🚀 Run Full Valuation", key="p3_run"):
            with st.spinner(f"Running institutional valuation for {vd['ticker']}..."):
                st.session_state["p3_result"] = p3_full_valuation(vd['ticker'])

        p3 = st.session_state.get("p3_result")
        if p3 and p3.get('ticker') == vd['ticker']:
            if p3.get('signal') == "⚠️ DATA INSUFF":
                st.warning(f"⚠️ **DATA INSUFFICIENT** — {p3.get('note','')}")
            else:
                sig = p3['signal']
                if "BUY" in sig:          st.success(f"## {sig} — {p3.get('action','')}")
                elif "HOLD" in sig:       st.info(f"## {sig} — {p3.get('action','')}")
                elif "DATA CHECK" in sig: st.warning(f"## {sig} — {p3.get('action','')}")
                else:                     st.error(f"## {sig} — {p3.get('action','')}")

                st.subheader(f"⭐ Quality Score: {p3['quality_score']}/25 | "
                             f"Data Confidence: {p3['confidence']} ({p3['years']} yrs)")
                fcols = st.columns(len(p3['factors']))
                for i, (fname, fscore) in enumerate(p3['factors'].items()):
                    with fcols[i]:
                        st.metric(fname, f"{fscore}/5 ⭐")

                st.markdown("---")
                st.subheader("💰 Discount Rate Breakdown")
                d1, d2, d3, d4 = st.columns(4)
                with d1: st.metric("Risk-Free Rate", f"{RISK_FREE_RATE*100:.1f}%", "10-yr Treasury")
                with d2: st.metric("Equity Premium", f"{EQUITY_RISK_PREMIUM*100:.1f}%", "Market standard")
                with d3: st.metric("Company Risk", f"+{p3['company_risk']*100:.2f}%", "Quality-based")
                with d4: st.metric("Total Discount Rate", f"{p3['discount_rate']*100:.2f}%")

                st.markdown("---")
                st.subheader("📈 Growth Assumptions (Analyst + TAM Brake)")
                g1c, g2c, g3c, g4c = st.columns(4)
                with g1c: st.metric("Analyst Growth", f"{p3.get('analyst_growth',0)*100:.0f}%",
                                    f"Source: {p3.get('growth_source','')}")
                with g2c: st.metric("Industry Growth", f"{p3.get('industry_growth',0)*100:.0f}%",
                                    f"Share proxy: {p3.get('mkt_share_proxy',0)*100:.0f}%")
                with g3c: st.metric("Growth Used (Braked)", f"{p3.get('braked_growth',0)*100:.0f}%",
                                    "After TAM brake")
                with g4c: st.metric("Growth Hold Period", f"{p3.get('hold_years',3)} years",
                                    f"Quality-linked (Q{p3['quality_score']}/25)")
                st.caption("💡 Growth = analyst consensus, capped by industry capacity (TAM), held longer "
                           "for higher-quality companies, then fades to 2.5% terminal")

                st.markdown("---")
                st.subheader(f"📊 Three-Scenario DCF ({p3['horizon']}-Year Forecast)")
                w = p3['weights']
                s1, s2, s3 = st.columns(3)
                with s1: st.metric(f"🐻 Bear Case ({w[0]*100:.0f}%)", f"${p3['bear']:.2f}")
                with s2: st.metric(f"📊 Base Case ({w[1]*100:.0f}%)", f"${p3['base']:.2f}")
                with s3: st.metric(f"🚀 Bull Case ({w[2]*100:.0f}%)", f"${p3['bull']:.2f}")

                st.markdown("---")
                st.subheader("🎯 Fair Value & Investment Decision")
                v1, v2, v3, v4 = st.columns(4)
                with v1: st.metric("Intrinsic Value", f"${p3['intrinsic']:.2f}", "Probability-weighted")
                with v2: st.metric("Quality Premium", f"{p3['premium']:.2f}x", f"Score {p3['quality_score']}/25")
                with v3: st.metric("Fair Value", f"${p3['fair_value']:.2f}", "Intrinsic × Premium")
                with v4: st.metric("Current Price", f"${p3['price']:.2f}",
                                   f"{p3['expected_return']:+.0f}% to fair value")
                b1, b2 = st.columns(2)
                with b1: st.metric("🎯 Target Entry (25% MoS)", f"${p3['buy_below']:.2f}")
                with b2: st.metric("💼 Suggested Allocation", p3['allocation'])
                st.caption("💡 BUY when price ≤ target entry | Legend in sidebar 📖")

        st.markdown("---")
        st.markdown('<div class="section-header">📊 Financial Statements — 5-Year History</div>',
                    unsafe_allow_html=True)
        try:
            income_stmt = vd.get("income6") or []
            cashflow_stmt = vd.get("cashflow6") or []
            balance_sheet = vd.get("balance") or []

            if income_stmt and isinstance(income_stmt, list) and len(income_stmt) > 0:
                st.subheader("📈 Income Statement (5 Years)")
                _rep_ccy = income_stmt[0].get("reportedCurrency", "USD") if isinstance(income_stmt[0], dict) else "USD"
                if _rep_ccy != "USD":
                    st.caption(f"⚠️ Reported in **{_rep_ccy}** — figures below are as reported. "
                               "The dossier PDF converts them to USD at each year-end rate.")

                income_data = []
                sorted_stmts = sorted(income_stmt, key=lambda x: x.get('date', ''))[-5:]
                for idx, stmt in enumerate(sorted_stmts):
                    year = stmt.get('date', '').split('-')[0]
                    revenue = stmt.get('revenue', 0) or 0
                    if idx == 0:
                        revenue_growth = "—"
                    else:
                        prev_revenue = sorted_stmts[idx - 1].get('revenue', 0) or 0
                        revenue_growth = (f"{((revenue - prev_revenue) / prev_revenue) * 100:.1f}%"
                                          if prev_revenue > 0 else "—")
                    gross_profit = stmt.get('grossProfit', 0) or 0
                    gross_margin = (gross_profit / revenue * 100) if revenue > 0 else 0
                    # ★ v1.1.3: overheads + net profit shown in the app table too
                    opex = stmt.get('operatingExpenses')
                    if opex is None and gross_profit and stmt.get('operatingIncome') is not None:
                        opex = float(gross_profit) - float(stmt.get('operatingIncome') or 0)
                    opex = float(opex or 0)
                    opex_pct = (opex / revenue * 100) if revenue > 0 else 0
                    operating_income = stmt.get('operatingIncome', 0) or 0
                    operating_margin = (operating_income / revenue * 100) if revenue > 0 else 0
                    net_income = stmt.get('netIncome', 0) or 0
                    net_margin = (net_income / revenue * 100) if revenue > 0 else 0
                    nonop = float(net_income) - float(operating_income)
                    eps = stmt.get('eps', 0) or 0

                    income_data.append({
                        'Year': year,
                        'Revenue': f"{revenue/1e9:.1f}B" if revenue else "—",
                        'Rev Growth %': revenue_growth,
                        'Gross Profit': f"{gross_profit/1e9:.1f}B" if gross_profit else "—",
                        'Gross Margin %': f"{gross_margin:.1f}%" if gross_margin else "—",
                        'Total Overheads': f"{opex/1e9:.1f}B" if opex else "—",
                        'Overheads %': f"{opex_pct:.1f}%" if opex_pct else "—",
                        'Operating Income': f"{operating_income/1e9:.1f}B" if operating_income else "—",
                        'Op Margin %': f"{operating_margin:.1f}%" if operating_margin else "—",
                        'Non-Op & Tax': f"{nonop/1e9:+.1f}B" if nonop else "—",
                        'Net Profit/(Loss)': (f"({abs(net_income)/1e9:.1f}B)" if net_income < 0
                                              else f"{net_income/1e9:.1f}B" if net_income else "—"),
                        'Net Margin %': f"{net_margin:.1f}%" if net_margin else "—",
                        'EPS': f"{eps:.2f}" if eps else "—",
                    })
                st.dataframe(pd.DataFrame(income_data), use_container_width=True, hide_index=True)
                st.caption(f"💡 Figures in {_rep_ccy}. Non-Op & Tax = Net Profit − Operating Income "
                           "(interest, investment and other income, less tax). A positive figure is why "
                           "net profit can exceed operating income.")
            else:
                st.warning("Income statement data not available")

            st.markdown("---")
            if cashflow_stmt and isinstance(cashflow_stmt, list) and len(cashflow_stmt) > 0:
                st.subheader("💰 Cash Flow Statement (5 Years)")
                cashflow_data = []
                for stmt in sorted(cashflow_stmt, key=lambda x: x.get('date', ''))[-5:]:
                    year = stmt.get('date', '').split('-')[0]
                    operating_cf = stmt.get('operatingCashFlow', 0) or 0
                    capex = stmt.get('capitalExpenditure', 0) or 0
                    free_cf = stmt.get('freeCashFlow', 0) or 0
                    fcf_margin = (free_cf / operating_cf * 100) if operating_cf > 0 else 0
                    cashflow_data.append({
                        'Year': year,
                        'Operating Cash Flow': f"{operating_cf/1e9:.1f}B" if operating_cf else "—",
                        'Capital Expenditure': f"{abs(capex)/1e9:.1f}B" if capex else "—",
                        'Free Cash Flow': f"{free_cf/1e9:.1f}B" if free_cf else "—",
                        'FCF / OCF %': f"{fcf_margin:.1f}%" if fcf_margin else "—",
                    })
                st.dataframe(pd.DataFrame(cashflow_data), use_container_width=True, hide_index=True)
            else:
                st.warning("Cash flow statement data not available")

            st.markdown("---")
            if balance_sheet and isinstance(balance_sheet, list) and len(balance_sheet) > 0:
                st.subheader("⚖️ Balance Sheet & Capital Structure (5 Years)")
                balance_data = []
                for stmt in sorted(balance_sheet, key=lambda x: x.get('date', ''))[-5:]:
                    year = stmt.get('date', '').split('-')[0]
                    cash = stmt.get('cashAndCashEquivalents', 0) or 0
                    total_debt = stmt.get('totalDebt', 0) or 0
                    net_debt_y = total_debt - cash
                    equity = stmt.get('totalStockholdersEquity', 0) or 0
                    debt_equity = (total_debt / equity) if equity > 0 else 0
                    balance_data.append({
                        'Year': year,
                        'Cash': f"{cash/1e9:.1f}B" if cash else "—",
                        'Total Debt': f"{total_debt/1e9:.1f}B" if total_debt else "—",
                        'Net Debt': f"{net_debt_y/1e9:.1f}B" if net_debt_y else "—",
                        'Shareholders Equity': f"{equity/1e9:.1f}B" if equity else "—",
                        'Debt/Equity': f"{debt_equity:.2f}" if debt_equity >= 0 else "—",
                    })
                st.dataframe(pd.DataFrame(balance_data), use_container_width=True, hide_index=True)
            else:
                st.warning("Balance sheet data not available")
        except Exception as e:
            st.warning(f"Could not render financial statements: {str(e)[:100]}")

        st.markdown("---")
        if st.button("📄 Generate Dossier PDF", key="gen_dos"):
            with st.spinner("Generating professional dossier..."):
                pdf_path = generate_dossier_pdf(vd['ticker'], vd, v, result, checks, buff_score,
                                                cat, note, peg, moat_rat, moat_sc,
                                                cio_rec, inv_edge, risks)
            with open(pdf_path, "rb") as f:
                st.download_button(
                    label="📥 Download Dossier PDF", data=f.read(),
                    file_name=f"{vd['ticker']}_MCIS_Dossier_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf", key="download_dos")
            st.success(f"✅ Dossier generated — {vd['ticker']}_MCIS_Dossier.pdf")
            st.info("📋 Page 1: financials & ratios. Page 2: valuation & competitive analysis "
                    "with your CIO thesis.")
    else:
        st.markdown('<div class="info-box">Enter a ticker and click <b>Load</b> to start building '
                    'a professional investment dossier.</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
# PAGE: ETF MONITOR
# ─────────────────────────────────────────────
elif page == "📈 ETF Monitor":
    st.markdown("""
    <div class="mcis-header">
        <p class="mcis-title">📈 ETF Opportunity Monitor</p>
        <p class="mcis-subtitle">Track 1: Ready to Buy (2+ yrs) | Track 2: Early Bird Watch List (&lt;2 yrs)</p>
    </div>
    """, unsafe_allow_html=True)

    st.info(f"📌 **Current Holdings:** {', '.join(CURRENT_HOLDINGS)} | "
            f"**Universe scanned:** {len(ETF_UNIVERSE)} halal ETFs | Legend in sidebar 📖")

    col_a, col_b = st.columns([1, 3])
    with col_a:
        run_etf = st.button("🔍 Run ETF Scan Now", key="etf_scan_btn", use_container_width=True)
    with col_b:
        custom_etf = st.text_input("Or scan a specific ETF ticker", placeholder="e.g. SPRE",
                                   key="custom_etf").upper().strip()

    if run_etf:
        etf_out = []
        prog = st.progress(0)
        for i, t in enumerate(ETF_UNIVERSE):
            etf_out.append(p3_etf_scan(t))
            prog.progress((i + 1) / len(ETF_UNIVERSE))
        prog.empty()
        st.session_state["etf_results"] = etf_out

    if custom_etf:
        with st.spinner(f"Scanning {custom_etf}..."):
            single = p3_etf_scan(custom_etf)
        st.subheader(f"Result: {custom_etf}")
        st.write(f"**{single.get('tier','')}** — {single.get('note','')}")
        if single.get('track') == 1:
            st.write(f"Score: **{single['score']}/100** | Age: {single.get('age_years',0):.1f} yrs | "
                     f"1-Yr Perf: {single.get('perf_1y',0):+.1f}%")
            with st.expander("Score breakdown"):
                for k, val in single.get('details', {}).items():
                    st.write(f"- {k}: {val} pts")

    etf_results = st.session_state.get("etf_results")
    if etf_results:
        track1 = [r for r in etf_results if r.get('track') == 1]
        track2 = [r for r in etf_results if r.get('track') == 2]

        st.markdown("---")
        st.subheader("📊 TRACK 1 — Ready to Buy (2+ Years History)")
        if track1:
            t1_sorted = sorted(track1, key=lambda x: x.get('score', 0), reverse=True)
            df1 = pd.DataFrame([{
                "Ticker": r['ticker'],
                "Name": r.get('name', '')[:35],
                "Age (yrs)": f"{r.get('age_years',0):.1f}",
                "Price": f"${r.get('price',0):.2f}" if r.get('price') else "—",
                "5Y High": f"${r.get('p5_high',0):.2f}" if r.get('p5_high') else "—",
                "5Y Low": f"${r.get('p5_low',0):.2f}" if r.get('p5_low') else "—",
                "Buy Target": f"${r.get('p5_target',0):.2f}" if r.get('p5_target') else "—",
                "1-Yr Perf": f"{r.get('perf_1y',0):+.1f}%",
                "Score": f"{r.get('score',0)}/100",
                "Alert": r.get('tier', ''),
                "Note": r.get('note', '')[:50],
            } for r in t1_sorted])
            st.dataframe(df1, use_container_width=True, hide_index=True)
            st.caption("💡 Buy Target = 5Y low × 0.95 (safety margin).")

            orange = [r for r in t1_sorted if "ORANGE" in r.get('tier', '')]
            if orange:
                st.markdown("#### 🟠 Orange Zone — Your Decision")
                for r in orange:
                    with st.expander(f"🟠 {r['ticker']} — {r.get('score',0)}/100 — Review trade-offs"):
                        st.write(f"**{r.get('name','')}**")
                        st.write("**Criteria breakdown:**")
                        for k, val in r.get('details', {}).items():
                            emoji = "✅" if val >= 12 else "⚠️" if val >= 8 else "❌"
                            st.write(f"{emoji} {k}: {val} pts")
                        st.write(f"**MCIS View:** {r.get('note','')}")
        else:
            st.info("No Track 1 ETFs found. Run the scan.")

        st.markdown("---")
        st.subheader("🚀 TRACK 2 — Early Bird Watch List (<2 Years)")
        if track2:
            df2 = pd.DataFrame([{
                "Ticker": r['ticker'],
                "Name": r.get('name', '')[:35],
                "Age": f"{r.get('age_years',0)*12:.0f} mo",
                "Price": f"${r.get('price',0):.2f}" if r.get('price') else "—",
                "High (inception)": f"${r.get('p5_high',0):.2f}" if r.get('p5_high') else "—",
                "Low (inception)": f"${r.get('p5_low',0):.2f}" if r.get('p5_low') else "—",
                "1-Yr Perf": f"{r.get('perf_1y',0):+.1f}%" if r.get('perf_1y') else "—",
                "Status": r.get('tier', ''),
                "Note": r.get('note', '')[:60],
            } for r in track2])
            st.dataframe(df2, use_container_width=True, hide_index=True)
            st.caption("🚀 Early birds flagged — you decide on exploratory positions (1-3%)")
        else:
            st.info("No emerging ETFs (<2 yrs) currently in the universe.")

        track3 = [r for r in etf_results if r.get('track') == 3]
        if track3:
            st.markdown("---")
            st.subheader("🌍 NON-US LISTED — Price via Fallback (FMP→Yahoo)")
            df3 = pd.DataFrame([{
                "Ticker": r['ticker'],
                "Name": r.get('name', ''),
                "Price": f"${r.get('price',0):.2f}" if r.get('price') else "—",
                "5Y High": f"${r.get('p5_high',0):.2f}" if r.get('p5_high') else "—",
                "5Y Low": f"${r.get('p5_low',0):.2f}" if r.get('p5_low') else "—",
                "Buy Target": f"${r.get('p5_target',0):.2f}" if r.get('p5_target') else "—",
                "1-Yr Perf": f"{r.get('perf_1y',0):+.1f}%" if r.get('perf_1y') else "—",
                "Status": r.get('tier', ''),
                "Diagnosis / Source": r.get('note', ''),
            } for r in track3])
            st.dataframe(df3, use_container_width=True, hide_index=True)
            st.caption("💡 🌍 PRICE-ONLY = price rescued via fallback (currency = local exchange). "
                       "⚪ NOT COVERED = all sources failed.")

        st.markdown("---")
        st.caption("⏰ Quarterly reminder: re-run in Jan / Apr / Jul / Oct — or anytime on demand.")


# ─────────────────────────────────────────────
# PAGE: VALUATION ENGINE
# ─────────────────────────────────────────────
elif page == "🏛 Valuation Engine":
    st.markdown("""
    <div class="mcis-header">
        <p class="mcis-title">🏛 Valuation Engine</p>
        <p class="mcis-subtitle">DCF | Reverse DCF | Buffett Quality Test | Lynch Classification | Moat</p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns([3, 1])
    with c1:
        available_tickers = sorted(set(r["ticker"] for r in st.session_state.scan_results))
        if available_tickers:
            val_ticker = st.selectbox("Select company or type ticker", [""] + available_tickers,
                                      index=0, key="val_ticker_select")
            if not val_ticker:
                val_ticker = st.text_input("Or enter ticker manually", placeholder="e.g. NVDA",
                                           key="val_ticker_in").upper().strip()
        else:
            val_ticker = st.text_input("Ticker symbol", placeholder="e.g. NVDA",
                                       key="val_ticker_in").upper().strip()
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

        try:
            _cf6 = vd.get("cashflow6", []) or []
            _ccy = _cf6[0].get("reportedCurrency", "USD") if _cf6 and isinstance(_cf6[0], dict) else "USD"
            if _ccy != "USD":
                st.info(f"💱 {vd['ticker']} reports in **{_ccy}** — all cash flows below are converted "
                        f"to USD (rate: 1 {_ccy} = {get_fx_to_usd(_ccy):.4f} USD) so the DCF matches "
                        "the USD share price.")
        except Exception:
            pass

        if v["fcf0"] <= 0:
            st.markdown('<div class="warning-box"><b>FCF is negative or unavailable</b> — a DCF is not '
                        'meaningful. The quality, Lynch and moat sections below still work.</div>',
                        unsafe_allow_html=True)

        st.markdown('<div class="section-header">⚙️ DCF Assumptions — adjust and everything recalculates</div>',
                    unsafe_allow_html=True)
        hist_g = v["fcf_cagr"] if v["fcf_cagr"] is not None else v["rev_cagr"]
        default_g = int(round(min(max((hist_g or 0.10) * 100, 4), 25)))
        a1, a2, a3, a4 = st.columns(4)
        with a1: g1 = st.slider("Growth yrs 1-5 (%)", -5, 40, default_g) / 100
        with a2: wacc = st.slider("Discount rate (%)", 6.0, 15.0, 10.0, 0.5) / 100
        with a3: tg = st.slider("Terminal growth (%)", 1.0, 4.0, 2.5, 0.25) / 100
        with a4: mos_req = st.slider("Required margin of safety (%)", 10, 50, 25, 5)

        _fcf_c = f"{v['fcf_cagr']*100:.1f}%" if v['fcf_cagr'] is not None else "n/a"
        _rev_c = f"{v['rev_cagr']*100:.1f}%" if v['rev_cagr'] is not None else "n/a"
        st.caption(f"Historical FCF CAGR: {_fcf_c} | Revenue CAGR: {_rev_c} | "
                   f"FCF base (TTM): ${v['fcf0']/1e9:.2f}B | Net debt: ${v['net_debt']/1e9:.2f}B")

        if v["fcf0"] > 0 and v["shares"]:
            scenarios = {"🐻 Bear": max(g1 * 0.6, -0.05), "⚖️ Base": g1, "🚀 Bull": min(g1 * 1.3, 0.40)}
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

            st.markdown('<div class="section-header">💰 DCF — Three Scenario Intrinsic Value</div>',
                        unsafe_allow_html=True)
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

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

            st.markdown('<div class="section-header">📈 5-Year Price History</div>', unsafe_allow_html=True)
            prices = fetch_historical_prices_yahoo(vd['ticker'])
            if prices and len(prices) > 10:
                fig_price = plot_5year_price_chart_yahoo(prices, vd['ticker'], v["price"])
                if fig_price:
                    st.plotly_chart(fig_price, use_container_width=True)
                else:
                    st.info("Chart unavailable")
            else:
                st.info(f"⚠️ Price history not available. Current price: ${v['price']:,.2f}")

            base_ps = per_share["⚖️ Base"]
            base_mos = (1 - v["price"] / base_ps) * 100 if base_ps > 0 else -999

            if base_ps > 0 and v["price"] > 0 and (base_ps > 3 * v["price"] or base_ps < 0.2 * v["price"]):
                st.warning(f"⚠️ DATA CHECK — base case intrinsic value ${base_ps:,.0f} is wildly detached "
                           f"from price ${v['price']:,.2f}. Usually a currency, share-count or stale-FCF "
                           "problem. Verify inputs before trusting any signal below.")

            if base_mos >= mos_req:
                st.success(f"✅ BUY ZONE — base case margin of safety {base_mos:.0f}% meets your "
                           f"{mos_req}% requirement. Buy-below price: ${base_ps*(1-mos_req/100):,.2f}")
            elif base_mos > 0:
                st.warning(f"⚠️ UNDERVALUED BUT THIN — {base_mos:.0f}% margin of safety is below your "
                           f"{mos_req}% requirement. Target entry: ${base_ps*(1-mos_req/100):,.2f}")
            else:
                st.error(f"❌ ABOVE INTRINSIC VALUE — price exceeds base case by {-base_mos:.0f}%. "
                         f"Target entry: ${base_ps*(1-mos_req/100):,.2f}")

            st.markdown('<div class="section-header">🔄 Reverse DCF — what the market is pricing in</div>',
                        unsafe_allow_html=True)
            implied = reverse_dcf(v["price"], v["shares"], v["fcf0"], wacc, tg, v["net_debt"])
            if implied is not None:
                r1, r2, r3 = st.columns(3)
                r1.metric("Implied FCF growth (yrs 1-5)", f"{implied*100:.1f}%")
                r2.metric("Historical FCF CAGR",
                          f"{v['fcf_cagr']*100:.1f}%" if v['fcf_cagr'] is not None else "n/a")
                r3.metric("Your base assumption", f"{g1*100:.1f}%")
                if v["fcf_cagr"] is not None:
                    if implied > v["fcf_cagr"] * 1.2:
                        st.error(f"Market demands {implied*100:.1f}% growth — MORE than the company has "
                                 f"historically delivered ({v['fcf_cagr']*100:.1f}%). Priced for acceleration.")
                    elif implied < v["fcf_cagr"] * 0.7:
                        st.success(f"Market only demands {implied*100:.1f}% — LESS than historical "
                                   f"{v['fcf_cagr']*100:.1f}%. Expectations are beatable.")
                    else:
                        st.info(f"Market expects {implied*100:.1f}% — roughly in line with history.")
            else:
                st.info("Reverse DCF unavailable (needs positive FCF and share count).")

        st.markdown('<div class="section-header">🎩 Buffett Quality Test — 10 checks</div>',
                    unsafe_allow_html=True)
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

        st.markdown('<div class="section-header">📈 Peter Lynch Classification</div>', unsafe_allow_html=True)
        cat, note, peg, peg_verdict, g_pct = lynch_classify(vd, v, pe)
        l1, l2, l3 = st.columns(3)
        l1.metric("Category", cat)
        l2.metric("Growth rate", f"{g_pct:.1f}%" if g_pct is not None else "n/a")
        l3.metric("PEG ratio", f"{peg:.2f}" if peg is not None else "n/a")
        st.info(f"**{cat}** — {note}")
        if peg is not None:
            (st.success if peg <= 1.5 else st.warning if peg <= 2 else st.error)(peg_verdict)

        st.markdown('<div class="section-header">🏰 Moat Assessment</div>', unsafe_allow_html=True)
        rating, mscore, evidence = moat_assessment(vd, v)
        mo1, mo2 = st.columns([1, 3])
        with mo1:
            st.metric("Moat Evidence Score", f"{mscore}/10")
            if rating == "WIDE MOAT":     st.success(f"🏰 {rating}")
            elif rating == "NARROW MOAT": st.info(f"🛡️ {rating}")
            else:                         st.error(f"⚠️ {rating}")
        with mo2:
            for e in evidence:
                st.write(e)

        with st.expander("📝 Qualitative moat checklist — your judgement, not the data's"):
            st.caption("Numbers show a moat EXISTS. These questions identify WHAT it is.")
            for q in ["Network effects — does each new customer make the product better for others?",
                      "Switching costs — is it painful/expensive for customers to leave?",
                      "Intangibles — brand, patents or licences competitors cannot copy?",
                      "Cost advantage — can it produce cheaper than anyone else at scale?",
                      "Efficient scale — is the market only big enough for a few players?"]:
                st.checkbox(q, key=f"moat_{vd['ticker']}_{q[:20]}")

        st.caption("MCIS Valuation Engine | Blueprint v1.2 | Models, not predictions — not investment advice")
    else:
        st.markdown('<div class="info-box">Enter a ticker and click <b>Load Company</b>. '
                    'The engine fetches 6 years of financials once, then every slider recalculates '
                    'the DCF instantly.</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
# PAGE: QUALITATIVE ALERTS
# ─────────────────────────────────────────────
elif page == "🚨 Qualitative Alerts":
    st.markdown("""
    <div class="mcis-header">
        <p class="mcis-title">🚨 Qualitative Alert System</p>
        <p class="mcis-subtitle">News | Insider Trading | SEC Filings — monitoring for thesis breakers</p>
    </div>
    """, unsafe_allow_html=True)

    tier1 = sorted({r["ticker"] for r in st.session_state.scan_results if r.get("layer") == "LONG_TERM"})
    wl = sorted({r["ticker"] for r in st.session_state.watchlist})
    universe = sorted(set(tier1) | set(wl))

    st.markdown(f'<div class="info-box"><b>Monitoring universe:</b> {len(tier1)} Tier 1 companies from '
                f'your last scan + {len(wl)} watchlist companies. Each ticker uses ~3 API calls — keep '
                f'runs under ~40 tickers to stay inside FMP free-tier limits.</div>', unsafe_allow_html=True)

    c1, c2 = st.columns([3, 1])
    with c1:
        default_sel = universe[:15] if universe else []
        selected = st.multiselect("Tickers to monitor", options=universe, default=default_sel)
        manual = st.text_input("Add extra tickers (comma separated)", placeholder="e.g. NVDA, ASML, LLY")
    with c2:
        news_days = st.selectbox("News lookback", [7, 14, 30, 60], index=2)
        filing_days = st.selectbox("SEC filings lookback", [30, 60, 90], index=1)

    scan_list = list(dict.fromkeys(selected + [t.strip().upper() for t in manual.split(",") if t.strip()]))

    if st.button("🚨 Run Alert Scan") and scan_list:
        prog = st.progress(0, text="Starting alert scan...")
        alert_out = {}
        for i, tk in enumerate(scan_list):
            prog.progress((i + 1) / len(scan_list), text=f"Scanning {tk} ({i+1}/{len(scan_list)})...")
            alert_out.update(run_alert_scan([tk], news_days=news_days, filing_days=filing_days))
        prog.empty()
        st.session_state["alert_results"] = alert_out
        st.session_state["alert_time"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    results = st.session_state.get("alert_results", {})
    if results:
        st.caption(f"Last alert scan: {st.session_state.get('alert_time','')}")
        n_crit = sum(1 for r in results.values() for a in r["all"] if a["sev"] == "CRITICAL")
        n_warn = sum(1 for r in results.values() for a in r["all"] if a["sev"] == "WARNING")
        n_pos = sum(1 for r in results.values() for a in r["all"] if a["sev"] == "POSITIVE")
        n_info = sum(1 for r in results.values() for a in r["all"] if a["sev"] == "INFO")

        k1, k2, k3, k4 = st.columns(4)
        k1.markdown(f'<div class="metric-card" style="border-left-color:#b71c1c">'
                    f'<div class="metric-value" style="color:#b71c1c">{n_crit}</div>'
                    f'<div class="metric-label">🔴 Critical — act today</div></div>', unsafe_allow_html=True)
        k2.markdown(f'<div class="metric-card tier3-card"><div class="metric-value" style="color:#e65100">'
                    f'{n_warn}</div><div class="metric-label">🟠 Warnings — investigate</div></div>',
                    unsafe_allow_html=True)
        k3.markdown(f'<div class="metric-card tier1-card"><div class="metric-value" style="color:#1b5e20">'
                    f'{n_pos}</div><div class="metric-label">🟢 Positive signals</div></div>',
                    unsafe_allow_html=True)
        k4.markdown(f'<div class="metric-card"><div class="metric-value">{n_info}</div>'
                    f'<div class="metric-label">🔵 Informational</div></div>', unsafe_allow_html=True)

        crit_feed = [(tk, a) for tk, r in results.items() for a in r["all"] if a["sev"] == "CRITICAL"]
        if crit_feed:
            st.markdown('<div class="section-header">🔴 CRITICAL ALERTS — Committee review required</div>',
                        unsafe_allow_html=True)
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
                    st.success("✓ Quiet — no qualitative alerts in the lookback window.")
                for a in sorted(r["all"], key=lambda x: {"CRITICAL": 0, "WARNING": 1,
                                                        "POSITIVE": 2, "INFO": 3}[x["sev"]]):
                    link = f" — [source]({a['link']})" if a["link"] else ""
                    line = (f"**{a['src']}** {a['date']} — {a['text']}"
                            + (f" _({a['why']})_" if a["why"] else "") + link)
                    if a["sev"] == "CRITICAL":   st.error(line)
                    elif a["sev"] == "WARNING":  st.warning(line)
                    elif a["sev"] == "POSITIVE": st.success(line)
                    else:                        st.info(line)

        st.markdown("""
        <div class="warning-box"><b>MCIS Rule — Section 16 triggers:</b> any 🔴 CRITICAL alert on a held
        position requires an Investment Committee thesis review within 48 hours. A cluster of insider
        selling alone is not a thesis breaker — but combined with a guidance cut or accounting alert, it is.</div>
        """, unsafe_allow_html=True)
    elif not universe:
        st.markdown('<div class="info-box">No Tier 1 or watchlist companies found yet — run the Scanner '
                    'first, or add tickers manually above.</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
# PAGE: DATA AUDIT
# ─────────────────────────────────────────────
elif page == "🔬 Data Audit":
    st.markdown("""
    <div class="mcis-header">
        <p class="mcis-title">🔬 Data Audit</p>
        <p class="mcis-subtitle">Spot-check FMP data against Yahoo Finance & SEC filings</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="info-box">
    <b>Why data audit matters:</b> FMP is fast and convenient, but occasionally returns stale or incorrect
    data. This page compares FMP against Yahoo Finance for a sample of companies.
    Under 5% variance flags caution, over 10% requires review.
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-header">🔍 Sample Companies to Validate</div>', unsafe_allow_html=True)
    st.caption("These 5 companies represent different sectors and market caps.")

    sample_tickers = ["NVDA", "MSFT", "ASML", "SNOW", "AMD"]

    if st.button("🚀 Run Data Audit on Sample"):
        audit_out = {}
        prog = st.progress(0, text="Starting audit...")
        for i, ticker in enumerate(sample_tickers):
            prog.progress((i + 1) / len(sample_tickers), text=f"Auditing {ticker}...")
            audit_out[ticker] = audit_fmp_vs_yahoo(ticker)
        prog.empty()
        st.session_state["audit_results"] = audit_out
        st.session_state["audit_time"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    results = st.session_state.get("audit_results", {})
    if results:
        st.caption(f"Last audit: {st.session_state.get('audit_time','')}")
        passed = sum(1 for r in results.values() if r.get("status") == "✅ MATCH")
        flagged = sum(1 for r in results.values() if r.get("status") == "⚠️ REVIEW")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f'<div class="metric-card tier1-card"><div class="metric-value" style="color:#1b5e20">'
                        f'{passed}</div><div class="metric-label">✅ Data Matches Yahoo</div></div>',
                        unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="metric-card tier3-card"><div class="metric-value" style="color:#e65100">'
                        f'{flagged}</div><div class="metric-label">⚠️ Minor Discrepancies</div></div>',
                        unsafe_allow_html=True)

        st.markdown('<div class="section-header">📋 Detailed Audit Results</div>', unsafe_allow_html=True)
        for ticker in sample_tickers:
            audit = results.get(ticker, {})
            status = audit.get("status", "⚠️ REVIEW")
            with st.expander(f"{status} — {ticker}"):
                if "error" in audit:
                    st.error(f"Error: {audit['error']}")
                else:
                    if audit.get("matches"):
                        st.success("✓ Data Matches:")
                        for metric, comparison in audit["matches"].items():
                            st.write(f"  • {metric.upper()}: {comparison}")
                    if audit.get("discrepancies"):
                        st.warning("⚠️ Discrepancies Found:")
                        for disc in audit["discrepancies"]:
                            st.write(f"  • {disc}")
                        st.caption("**Action:** Verify the higher variance in SEC filings")
                    else:
                        st.success("No material discrepancies detected")

        st.markdown("""
        <div class="warning-box">
        <b>Data Quality Guidelines:</b><br>
        🟢 &lt;5% variance = Confidence in FMP data<br>
        🟡 5-10% variance = Note the variance, use with caution<br>
        🔴 &gt;10% variance = Verify against SEC filings before using in analysis
        </div>
        """, unsafe_allow_html=True)

        audit_df = pd.DataFrame([{
            "Ticker": ticker,
            "Status": results.get(ticker, {}).get("status", "N/A"),
            "Matches": len(results.get(ticker, {}).get("matches", {})),
            "Discrepancies": len(results.get(ticker, {}).get("discrepancies", [])),
        } for ticker in sample_tickers])
        st.dataframe(audit_df, use_container_width=True, hide_index=True)

        st.markdown('<div class="section-header">📊 Add Custom Ticker to Audit</div>', unsafe_allow_html=True)
        custom_ticker = st.text_input("Enter ticker to audit", placeholder="e.g. AAPL").upper().strip()
        if st.button("🔍 Audit Ticker") and custom_ticker:
            with st.spinner(f"Auditing {custom_ticker}..."):
                custom_audit = audit_fmp_vs_yahoo(custom_ticker)
            st.subheader(f"{custom_audit.get('status', '⚠️ REVIEW')} — {custom_ticker}")
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
        st.markdown('<div class="info-box">Click <b>Run Data Audit</b> to validate FMP data against '
                    'Yahoo Finance for a sample of companies.</div>', unsafe_allow_html=True)
