// Majid Investment API v4 - Batch + Cache Engine
// Cloudflare Worker for GPT Actions + FMP API
// Keep your Cloudflare secret named: FMP_API_KEY

const BASE_URL = "https://majid-investment-api.amajid-hussain-azad.workers.dev";
const FMP_BASE = "https://financialmodelingprep.com";

const CONFIG = {
  cache: {
    quoteSeconds: 300,
    profileSeconds: 604800,
    statementsSeconds: 86400,
    ratiosSeconds: 86400,
    dcfSeconds: 43200,
    historicalSeconds: 3600,
    analysisSeconds: 1800,
    screenSeconds: 900
  },
  halal: {
    maxDebtToMarketCapPercent: 33,
    maxInterestIncomeToRevenuePercent: 5,
    maxCashToMarketCapPercent: 33,
    prohibitedKeywords: [
      "bank", "banks", "insurance", "casino", "gambling", "alcohol", "tobacco",
      "adult", "pork", "weapons", "defense", "defence", "beer", "wine"
    ]
  },
  universe: [
    "AAPL","MSFT","GOOGL","GOOG","META","NVDA","AVGO","V","MA","COST",
    "ASML","TSM","AMD","ADBE","CRM","LRCX","KLAC","AMAT","ORCL","NOW",
    "INTU","QCOM","TXN","ANET","PANW","SNOW","NFLX","SHOP","MELI","UBER"
  ]
};

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;

    const corsHeaders = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization"
    };

    if (request.method === "OPTIONS") return new Response(null, { headers: corsHeaders });

    try {
      if (path === "/openapi.json") return json(openApiSpec(), 200, corsHeaders);
      if (path === "/health") return json({ status: "ok", version: "4.0", service: "Majid Investment API - Batch + Cache Engine" }, 200, corsHeaders);

      if (!env.FMP_API_KEY) return json({ error: "FMP_API_KEY secret is missing" }, 500, corsHeaders);

      if (path === "/profile") return fmpCached(`/stable/profile?symbol=${requiredTicker(url)}`, env, corsHeaders, CONFIG.cache.profileSeconds);
      if (path === "/quote") return fmpCached(`/stable/quote?symbol=${requiredTicker(url)}`, env, corsHeaders, CONFIG.cache.quoteSeconds);
      if (path === "/income") return statementEndpoint(url, env, corsHeaders, "income-statement");
      if (path === "/balance") return statementEndpoint(url, env, corsHeaders, "balance-sheet-statement");
      if (path === "/cashflow") return statementEndpoint(url, env, corsHeaders, "cash-flow-statement");
      if (path === "/ratios") return ratioEndpoint(url, env, corsHeaders, "ratios");
      if (path === "/key-metrics") return ratioEndpoint(url, env, corsHeaders, "key-metrics");
      if (path === "/dcf") return fmpCached(`/stable/discounted-cash-flow?symbol=${requiredTicker(url)}`, env, corsHeaders, CONFIG.cache.dcfSeconds);
      if (path === "/historical-price") return fmpCached(`/stable/historical-price-eod/full?symbol=${requiredTicker(url)}`, env, corsHeaders, CONFIG.cache.historicalSeconds);
      if (path === "/company-search") {
        const query = url.searchParams.get("query");
        if (!query) return json({ error: "Missing query parameter" }, 400, corsHeaders);
        return fmpCached(`/stable/search-symbol?query=${encodeURIComponent(query)}&limit=10`, env, corsHeaders, 86400);
      }

      if (path === "/analyze" || path === "/analyse") {
        const ticker = requiredTicker(url);
        const data = await cachedJson(`analysis:${ticker}`, CONFIG.cache.analysisSeconds, () => analyzeTicker(ticker, env));
        return json(data, 200, corsHeaders);
      }

      if (path === "/compare") {
        const tickers = parseTickers(url.searchParams.get("tickers"));
        if (!tickers.length) return json({ error: "Missing tickers parameter. Example: /compare?tickers=AAPL,MSFT" }, 400, corsHeaders);
        const results = await Promise.all(tickers.slice(0, 10).map(t => cachedJson(`analysis:${t}`, CONFIG.cache.analysisSeconds, () => analyzeTicker(t, env))));
        return json({ tickers, results: sortByScore(results), best: sortByScore(results)[0] || null }, 200, corsHeaders);
      }

      if (path === "/portfolio") {
        const tickers = parseTickers(url.searchParams.get("tickers"));
        if (!tickers.length) return json({ error: "Missing tickers parameter. Example: /portfolio?tickers=AAPL,MSFT,V" }, 400, corsHeaders);
        const results = await Promise.all(tickers.slice(0, 25).map(t => cachedJson(`analysis:${t}`, CONFIG.cache.analysisSeconds, () => analyzeTicker(t, env))));
        return json(buildPortfolioReview(results), 200, corsHeaders);
      }

      if (path === "/screen") {
        const mode = (url.searchParams.get("mode") || "long-term").toLowerCase();
        const limit = clampInt(url.searchParams.get("limit"), 5, 1, 20);
        const tickers = parseTickers(url.searchParams.get("tickers"));
        const universe = tickers.length ? tickers : CONFIG.universe;
        const cacheKey = `screen:${mode}:${limit}:${universe.join(",")}`;
        const data = await cachedJson(cacheKey, CONFIG.cache.screenSeconds, () => screenUniverse(universe, mode, limit, env));
        return json(data, 200, corsHeaders);
      }

      return json({ error: "Endpoint not found", available: ["/health", "/openapi.json", "/analyze?ticker=AAPL", "/screen?mode=long-term&limit=5", "/screen?mode=swing&limit=5", "/compare?tickers=AAPL,MSFT", "/portfolio?tickers=AAPL,MSFT,V"] }, 404, corsHeaders);
    } catch (error) {
      return json({ error: error.message, stack: error.stack }, 500, corsHeaders);
    }
  }
};

async function statementEndpoint(url, env, corsHeaders, name) {
  const ticker = requiredTicker(url);
  const limit = clampInt(url.searchParams.get("limit"), 5, 1, 10);
  const period = url.searchParams.get("period") || "annual";
  return fmpCached(`/stable/${name}?symbol=${ticker}&period=${period}&limit=${limit}`, env, corsHeaders, CONFIG.cache.statementsSeconds);
}

async function ratioEndpoint(url, env, corsHeaders, name) {
  const ticker = requiredTicker(url);
  const limit = clampInt(url.searchParams.get("limit"), 5, 1, 10);
  const period = url.searchParams.get("period") || "annual";
  return fmpCached(`/stable/${name}?symbol=${ticker}&period=${period}&limit=${limit}`, env, corsHeaders, CONFIG.cache.ratiosSeconds);
}

async function analyzeTicker(ticker, env) {
  const [profile, quote, income, balance, cashflow, ratios, keyMetrics, dcf, historical] = await Promise.all([
    fetchFmpJson(`/stable/profile?symbol=${ticker}`, env, CONFIG.cache.profileSeconds),
    fetchFmpJson(`/stable/quote?symbol=${ticker}`, env, CONFIG.cache.quoteSeconds),
    fetchFmpJson(`/stable/income-statement?symbol=${ticker}&period=annual&limit=5`, env, CONFIG.cache.statementsSeconds),
    fetchFmpJson(`/stable/balance-sheet-statement?symbol=${ticker}&period=annual&limit=5`, env, CONFIG.cache.statementsSeconds),
    fetchFmpJson(`/stable/cash-flow-statement?symbol=${ticker}&period=annual&limit=5`, env, CONFIG.cache.statementsSeconds),
    fetchFmpJson(`/stable/ratios?symbol=${ticker}&period=annual&limit=5`, env, CONFIG.cache.ratiosSeconds),
    fetchFmpJson(`/stable/key-metrics?symbol=${ticker}&period=annual&limit=5`, env, CONFIG.cache.ratiosSeconds),
    fetchFmpJson(`/stable/discounted-cash-flow?symbol=${ticker}`, env, CONFIG.cache.dcfSeconds),
    fetchFmpJson(`/stable/historical-price-eod/full?symbol=${ticker}`, env, CONFIG.cache.historicalSeconds)
  ]);

  const p = first(profile), q = first(quote), latestIncome = first(income), latestBalance = first(balance), latestCash = first(cashflow), latestRatio = first(ratios), latestMetrics = first(keyMetrics), dcfRow = first(dcf);
  const price = Number(q?.price ?? p?.price ?? 0);
  const marketCap = Number(q?.marketCap ?? p?.marketCap ?? 0);
  const revenue = Number(latestIncome?.revenue ?? 0);
  const netIncome = Number(latestIncome?.netIncome ?? 0);
  const fcf = Number(latestCash?.freeCashFlow ?? 0);
  const cash = Number(latestBalance?.cashAndCashEquivalents ?? latestBalance?.cashAndShortTermInvestments ?? 0);
  const totalDebt = Number(latestBalance?.totalDebt ?? (Number(latestBalance?.shortTermDebt || 0) + Number(latestBalance?.longTermDebt || 0)));
  const interestIncome = Math.max(0, Number(latestIncome?.interestIncome ?? 0));
  const dcfFairValue = Number(dcfRow?.dcf ?? dcfRow?.DCF ?? 0);

  const revenueCagr5y = cagr(seriesValues(income, "revenue"));
  const epsCagr5y = cagr(seriesValues(income, "eps"));
  const netMargin = revenue ? (netIncome / revenue) * 100 : null;
  const fcfYield = marketCap ? (fcf / marketCap) * 100 : null;
  const marginOfSafety = (dcfFairValue && price) ? ((dcfFairValue - price) / price) * 100 : null;
  const debtToMarketCap = marketCap ? (totalDebt / marketCap) * 100 : null;
  const cashToMarketCap = marketCap ? (cash / marketCap) * 100 : null;
  const interestIncomeToRevenue = revenue ? (interestIncome / revenue) * 100 : 0;
  const roe = Number(latestRatio?.returnOnEquity ?? latestMetrics?.roe ?? 0) * (Math.abs(Number(latestRatio?.returnOnEquity ?? latestMetrics?.roe ?? 0)) <= 2 ? 100 : 1);
  const roic = Number(latestMetrics?.roic ?? latestRatio?.returnOnCapitalEmployed ?? 0) * (Math.abs(Number(latestMetrics?.roic ?? latestRatio?.returnOnCapitalEmployed ?? 0)) <= 2 ? 100 : 1);
  const peRatio = Number(latestRatio?.priceToEarningsRatio ?? latestMetrics?.peRatio ?? 0) || null;
  const pegRatio = (peRatio && epsCagr5y && epsCagr5y > 0) ? peRatio / epsCagr5y : null;
  const grahamNumber = graham(latestIncome, latestBalance);
  const halal = halalScreen(p, debtToMarketCap, cashToMarketCap, interestIncomeToRevenue);
  const technical = technicalScore(historical, price);

  const qualityScore = scoreQuality({ roe, roic, netMargin, fcf, revenueCagr5y });
  const valuationScore = scoreValuation({ marginOfSafety, fcfYield, peRatio, pegRatio });
  const growthScore = scoreGrowth({ revenueCagr5y, epsCagr5y });
  const financialStrengthScore = scoreFinancial({ debtToMarketCap, cashToMarketCap, fcf, netIncome });
  const halalScore = halal.pass ? 10 : 0;
  const technical10 = technical.score;
  const riskScore = scoreRisk({ debtToMarketCap, beta: Number(p?.beta ?? q?.beta ?? 1), marginOfSafety });

  const majidScore = round1(
    qualityScore * 0.20 +
    financialStrengthScore * 0.15 +
    growthScore * 0.15 +
    valuationScore * 0.20 +
    halalScore * 0.20 +
    technical10 * 0.05 +
    riskScore * 0.05
  ) * 10;

  const lynchCategory = classifyLynch(revenueCagr5y, epsCagr5y);
  const recommendation = finalRecommendation(majidScore, halal.pass, marginOfSafety);
  const swingDecision = swingRecommendation(technical, price);

  return {
    ticker,
    companyName: p?.companyName || q?.name || ticker,
    price,
    sector: p?.sector || null,
    industry: p?.industry || null,
    halal,
    lynchCategory,
    keyMetrics: {
      revenueCagr5y: round2(revenueCagr5y), epsCagr5y: round2(epsCagr5y), roic: nullableRound(roic), roe: nullableRound(roe),
      netMargin: nullableRound(netMargin), peRatio: nullableRound(peRatio), pegRatio: nullableRound(pegRatio),
      freeCashFlowYield: nullableRound(fcfYield), dcfFairValue: nullableRound(dcfFairValue), grahamNumber: nullableRound(grahamNumber),
      marginOfSafety: nullableRound(marginOfSafety), debtToMarketCap: nullableRound(debtToMarketCap), cashToMarketCap: nullableRound(cashToMarketCap)
    },
    scores: { qualityScore, valuationScore, growthScore, financialStrengthScore, halalScore, technicalScore: technical10, riskScore, majidScore: round1(majidScore) },
    longTermDecision: recommendation,
    swingDecision,
    technical,
    dataEfficiency: { cacheEnabled: true, note: "Analysis uses Cloudflare cache to reduce repeated FMP calls." },
    rawDataSummary: { profile: p, quote: q, latestIncome, latestCashFlow: latestCash }
  };
}

async function screenUniverse(universe, mode, limit, env) {
  const unique = [...new Set(universe.map(t => t.trim().toUpperCase()).filter(Boolean))];
  const analyses = [];

  // Stage 1: use cached detailed analysis for the configured universe.
  // This is safe and reliable. Future upgrade can replace this with FMP batch quotes.
  for (const ticker of unique) {
    try {
      const a = await cachedJson(`analysis:${ticker}`, CONFIG.cache.analysisSeconds, () => analyzeTicker(ticker, env));
      analyses.push(a);
    } catch (e) {
      analyses.push({ ticker, error: e.message });
    }
  }

  let filtered = analyses.filter(x => !x.error && x.halal?.pass);
  if (mode === "swing") filtered = filtered.sort((a, b) => (b.scores?.technicalScore || 0) - (a.scores?.technicalScore || 0));
  else if (mode === "value") filtered = filtered.sort((a, b) => (b.keyMetrics?.marginOfSafety || -999) - (a.keyMetrics?.marginOfSafety || -999));
  else if (mode === "dividend") filtered = filtered.sort((a, b) => (b.rawDataSummary?.profile?.lastDividend || 0) - (a.rawDataSummary?.profile?.lastDividend || 0));
  else filtered = sortByScore(filtered);

  return {
    mode,
    universeSize: unique.length,
    limit,
    cacheEnabled: true,
    results: filtered.slice(0, limit),
    note: "Version 4 adds Cloudflare caching and staged screening discipline. Next upgrade can use FMP batch quote endpoints where available to reduce calls further."
  };
}

function buildPortfolioReview(results) {
  const clean = results.filter(r => !r.error);
  const avgScore = clean.length ? clean.reduce((s, r) => s + (r.scores?.majidScore || 0), 0) / clean.length : 0;
  const weakest = [...clean].sort((a, b) => (a.scores?.majidScore || 0) - (b.scores?.majidScore || 0))[0] || null;
  const strongest = sortByScore(clean)[0] || null;
  const sectors = {};
  clean.forEach(r => sectors[r.sector || "Unknown"] = (sectors[r.sector || "Unknown"] || 0) + 1);
  return { holdings: clean.length, averageMajidScore: round1(avgScore), strongestHolding: strongest, weakestHolding: weakest, sectorCounts: sectors, holdingsDetail: sortByScore(clean) };
}

function halalScreen(profile, debtToMarketCap, cashToMarketCap, interestIncomeToRevenue) {
  const text = `${profile?.sector || ""} ${profile?.industry || ""} ${profile?.description || ""}`.toLowerCase();
  const flagged = CONFIG.halal.prohibitedKeywords.filter(k => text.includes(k));
  const fail = flagged.length || (debtToMarketCap ?? 0) > CONFIG.halal.maxDebtToMarketCapPercent || (interestIncomeToRevenue ?? 0) > CONFIG.halal.maxInterestIncomeToRevenuePercent;
  return { pass: !fail, status: fail ? "FAIL" : "PASS", flaggedActivities: flagged, debtToMarketCap: nullableRound(debtToMarketCap), cashToMarketCap: nullableRound(cashToMarketCap), interestIncomeToRevenue: nullableRound(interestIncomeToRevenue), note: "Automated screen using available FMP data. Final Shariah judgement should be verified manually." };
}

function technicalScore(historical, price) {
  const rows = Array.isArray(historical?.historical) ? historical.historical : (Array.isArray(historical) ? historical : []);
  const closes = rows.map(r => Number(r.close)).filter(Boolean).slice(0, 220);
  const ma20 = avg(closes.slice(0, 20));
  const ma50 = avg(closes.slice(0, 50));
  const ma200 = avg(closes.slice(0, 200));
  const rsi14 = rsi(closes.slice(0, 30));
  let score = 5;
  if (price > ma20) score += 1;
  if (price > ma50) score += 1;
  if (price > ma200) score += 1;
  if (rsi14 >= 45 && rsi14 <= 65) score += 1;
  if (rsi14 < 35) score += 0.5;
  if (price < ma50 && price < ma200) score -= 1;
  score = Math.max(0, Math.min(10, score));
  const stopLoss = ma50 ? Math.min(price * 0.94, ma50 * 0.97) : price * 0.94;
  const target = price + (price - stopLoss) * 3;
  return { score: round1(score), price, ma20: nullableRound(ma20), ma50: nullableRound(ma50), ma200: nullableRound(ma200), rsi14: nullableRound(rsi14), support: nullableRound(ma50 || ma200), suggestedEntry: price, suggestedStopLoss: nullableRound(stopLoss), targetPrice: nullableRound(target), riskReward: 3 };
}

function swingRecommendation(t, price) {
  if ((t.score || 0) >= 8) return { recommendation: "SWING BUY SETUP", confidence: "Medium", entry: price, stopLoss: t.suggestedStopLoss, target: t.targetPrice, riskReward: 3, note: "Confirm with live chart, volume and news before trading." };
  if ((t.score || 0) >= 6.5) return { recommendation: "WATCHLIST SETUP", confidence: "Medium", entry: price, stopLoss: t.suggestedStopLoss, target: t.targetPrice, riskReward: 3, note: "Setup is not strong enough for automatic entry. Wait for confirmation." };
  return { recommendation: "NO TRADE", confidence: "Medium", entry: price, stopLoss: t.suggestedStopLoss, target: t.targetPrice, riskReward: 3, note: "Technical conditions are not attractive." };
}

function finalRecommendation(score, halalPass, marginOfSafety) {
  if (!halalPass) return { recommendation: "AVOID", confidence: "High", reason: "Fails automated halal screening." };
  if (score >= 90) return { recommendation: "STRONG BUY", confidence: "High", reason: "High Majid Score with strong combined quality, growth, valuation and risk profile." };
  if (score >= 80) return { recommendation: "BUY", confidence: "High", reason: "Strong overall investment profile." };
  if (score >= 70) return { recommendation: "WATCHLIST", confidence: "Medium", reason: "Good business profile but valuation or risk requires patience." };
  if (score >= 60) return { recommendation: "HOLD", confidence: "Medium", reason: "Acceptable but not compelling." };
  return { recommendation: "AVOID", confidence: "Medium", reason: "Score is below required threshold." };
}

function scoreQuality({ roe, roic, netMargin, fcf, revenueCagr5y }) { let s = 5; if (roe > 15) s += 1.5; if (roic > 15) s += 1.5; if (netMargin > 20) s += 1; if (fcf > 0) s += 1; if (revenueCagr5y > 10) s += 1; return round1(Math.min(10, s)); }
function scoreValuation({ marginOfSafety, fcfYield, peRatio, pegRatio }) { let s = 5; if (marginOfSafety > 25) s += 3; else if (marginOfSafety > 10) s += 1.5; else if (marginOfSafety < -25) s -= 2; if (fcfYield > 4) s += 1; if (peRatio && peRatio < 25) s += 0.5; if (pegRatio && pegRatio < 1.5) s += 0.5; return round1(Math.max(0, Math.min(10, s))); }
function scoreGrowth({ revenueCagr5y, epsCagr5y }) { let s = 5; if (revenueCagr5y > 10) s += 2; if (revenueCagr5y > 20) s += 1; if (epsCagr5y > 10) s += 1.5; if (epsCagr5y > 20) s += 0.5; return round1(Math.min(10, s)); }
function scoreFinancial({ debtToMarketCap, cashToMarketCap, fcf, netIncome }) { let s = 5; if ((debtToMarketCap ?? 99) < 15) s += 2; else if ((debtToMarketCap ?? 99) < 33) s += 1; if ((cashToMarketCap ?? 0) > 3) s += 1; if (fcf > 0) s += 1; if (netIncome > 0) s += 1; return round1(Math.min(10, s)); }
function scoreRisk({ debtToMarketCap, beta, marginOfSafety }) { let s = 7; if ((debtToMarketCap ?? 0) > 33) s -= 3; if (beta > 1.5) s -= 1; if ((marginOfSafety ?? 0) < -30) s -= 1; return round1(Math.max(0, Math.min(10, s))); }

async function fmpCached(endpoint, env, corsHeaders, ttl) { const data = await fetchFmpText(endpoint, env, ttl); return new Response(data, { status: 200, headers: { "Content-Type": "application/json", "Cache-Control": `public, max-age=${ttl}`, ...corsHeaders } }); }
async function fetchFmpJson(endpoint, env, ttl) { const text = await fetchFmpText(endpoint, env, ttl); try { return JSON.parse(text); } catch { return { error: "Invalid JSON from FMP", raw: text }; } }
async function fetchFmpText(endpoint, env, ttl) {
  const sep = endpoint.includes("?") ? "&" : "?";
  const fmpUrl = `${FMP_BASE}${endpoint}${sep}apikey=${env.FMP_API_KEY}`;
  const cache = caches.default;
  const cacheKey = new Request(`https://cache.majid.local${endpoint}`);
  const cached = await cache.match(cacheKey);
  if (cached) return await cached.text();
  const res = await fetch(fmpUrl);
  const text = await res.text();
  await cache.put(cacheKey, new Response(text, { headers: { "Cache-Control": `public, max-age=${ttl}`, "Content-Type": "application/json" } }));
  return text;
}
async function cachedJson(key, ttl, producer) {
  const cache = caches.default;
  const req = new Request(`https://cache.majid.local/custom/${encodeURIComponent(key)}`);
  const hit = await cache.match(req);
  if (hit) return JSON.parse(await hit.text());
  const data = await producer();
  await cache.put(req, new Response(JSON.stringify(data), { headers: { "Cache-Control": `public, max-age=${ttl}`, "Content-Type": "application/json" } }));
  return data;
}

function openApiSpec() {
  return {
    openapi: "3.1.0",
    info: { title: "Majid Investment API", version: "4.0.0", description: "Batch and cache enabled investment analysis engine." },
    servers: [{ url: BASE_URL }],
    paths: {
      "/health": { get: { operationId: "healthCheck", summary: "Check API status", responses: { "200": { description: "OK" } } } },
      "/analyze": { get: { operationId: "analyzeStock", summary: "Analyse one ticker", parameters: [param("ticker", true)], responses: { "200": { description: "Analysis" } } } },
      "/analyse": { get: { operationId: "analyseStockBritish", summary: "Analyse one ticker", parameters: [param("ticker", true)], responses: { "200": { description: "Analysis" } } } },
      "/screen": { get: { operationId: "screenStocks", summary: "Screen a ticker universe for long-term, swing, value or dividend opportunities", parameters: [enumParam("mode", ["long-term", "swing", "value", "dividend", "halal"], false), intParam("limit", false), { name: "tickers", in: "query", required: false, schema: { type: "string" }, description: "Optional comma-separated tickers" }], responses: { "200": { description: "Screen results" } } } },
      "/compare": { get: { operationId: "compareStocks", summary: "Compare multiple tickers", parameters: [{ name: "tickers", in: "query", required: true, schema: { type: "string" } }], responses: { "200": { description: "Comparison" } } } },
      "/portfolio": { get: { operationId: "reviewPortfolio", summary: "Review a portfolio by tickers", parameters: [{ name: "tickers", in: "query", required: true, schema: { type: "string" } }], responses: { "200": { description: "Portfolio review" } } } },
      "/profile": basicPath("getCompanyProfile"), "/quote": basicPath("getStockQuote"), "/income": basicPath("getIncomeStatement"), "/balance": basicPath("getBalanceSheet"), "/cashflow": basicPath("getCashFlowStatement"), "/ratios": basicPath("getFinancialRatios"), "/key-metrics": basicPath("getKeyMetrics"), "/dcf": basicPath("getDCFValuation"), "/historical-price": basicPath("getHistoricalPrice"),
      "/company-search": { get: { operationId: "searchCompany", summary: "Search company", parameters: [{ name: "query", in: "query", required: true, schema: { type: "string" } }], responses: { "200": { description: "Search results" } } } }
    }
  };
}

function basicPath(operationId) { return { get: { operationId, summary: operationId, parameters: [param("ticker", true), intParam("limit", false)], responses: { "200": { description: "Successful response" } } } }; }
function param(name, required) { return { name, in: "query", required, schema: { type: "string" } }; }
function intParam(name, required) { return { name, in: "query", required, schema: { type: "integer", default: 5 } }; }
function enumParam(name, values, required) { return { name, in: "query", required, schema: { type: "string", enum: values } }; }
function requiredTicker(url) { const t = url.searchParams.get("ticker"); if (!t) throw new Error("Missing ticker parameter"); return t.toUpperCase().trim(); }
function parseTickers(value) { return (value || "").split(",").map(x => x.trim().toUpperCase()).filter(Boolean); }
function clampInt(v, def, min, max) { const n = parseInt(v || def, 10); return Math.max(min, Math.min(max, Number.isFinite(n) ? n : def)); }
function json(data, status, corsHeaders) { return new Response(JSON.stringify(data, null, 2), { status, headers: { "Content-Type": "application/json", ...corsHeaders } }); }
function first(x) { return Array.isArray(x) ? x[0] : x; }
function seriesValues(rows, key) { return (Array.isArray(rows) ? rows : []).map(r => Number(r[key])).filter(v => Number.isFinite(v) && v > 0).reverse(); }
function cagr(values) { if (!values || values.length < 2) return null; const start = values[0], end = values[values.length - 1], years = values.length - 1; if (start <= 0 || end <= 0 || years <= 0) return null; return (Math.pow(end / start, 1 / years) - 1) * 100; }
function avg(arr) { const a = arr.filter(Number.isFinite); return a.length ? a.reduce((s, x) => s + x, 0) / a.length : null; }
function rsi(closes) { if (!closes || closes.length < 15) return null; let gains = 0, losses = 0; for (let i = 0; i < 14; i++) { const diff = closes[i] - closes[i + 1]; if (diff > 0) gains += diff; else losses -= diff; } if (losses === 0) return 100; const rs = gains / losses; return 100 - (100 / (1 + rs)); }
function graham(income, balance) { const eps = Number(income?.eps || 0); const shares = Number(income?.weightedAverageShsOutDil || income?.weightedAverageShsOut || 0); const equity = Number(balance?.totalStockholdersEquity || balance?.totalEquity || 0); if (!eps || !shares || !equity) return null; const bvps = equity / shares; if (eps <= 0 || bvps <= 0) return null; return Math.sqrt(22.5 * eps * bvps); }
function classifyLynch(rev, eps) { const g = Math.max(Number(rev || 0), Number(eps || 0)); if (g >= 20) return "Fast grower"; if (g >= 10) return "Stalwart"; if (g > 0) return "Slow grower"; return "Cyclical / Turnaround"; }
function sortByScore(results) { return [...results].sort((a, b) => (b.scores?.majidScore || b.scores?.longTermScore || 0) - (a.scores?.majidScore || a.scores?.longTermScore || 0)); }
function round1(x) { return x == null || !Number.isFinite(Number(x)) ? null : Math.round(Number(x) * 10) / 10; }
function round2(x) { return x == null || !Number.isFinite(Number(x)) ? null : Math.round(Number(x) * 100) / 100; }
function nullableRound(x) { return x == null || !Number.isFinite(Number(x)) || Number(x) === 0 ? null : round2(x); }
