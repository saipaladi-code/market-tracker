/**
 * Financial News Headline Validator (Frontend)
 * Mirrors backend validation logic in backend/app/services/headline_validator.py
 */

export const MIN_HEADLINE_LENGTH = 15;
export const MAX_HEADLINE_LENGTH = 1000;

export const INVALID_FINANCIAL_HEADLINE_MESSAGE =
  "Invalid financial news headline. Please enter a relevant headline or statement " +
  "about a company, stock, business, financial market, or economic event.";

export const ERROR_INVALID_FINANCIAL_HEADLINE = "INVALID_FINANCIAL_HEADLINE";
export const ERROR_HEADLINE_TOO_SHORT = "HEADLINE_TOO_SHORT";
export const ERROR_HEADLINE_TOO_LONG = "HEADLINE_TOO_LONG";
export const ERROR_HEADLINE_EMPTY = "HEADLINE_EMPTY";

export interface HeadlineValidationResult {
  isValid: boolean;
  cleaned: string;
  errorCode: string | null;
  message: string | null;
  charCount: number;
}

const CONVERSATIONAL_PATTERNS = [
  /^\s*(?:hi|hello|hey|howdy|hola|namaste|greetings)\b/i,
  /^\s*(?:good\s+(?:morning|afternoon|evening|night|day))\b/i,
  /^\s*(?:how\s+are\s+you|how's\s+it\s+going|what's\s+up|sup)\b/i,
  /^\s*(?:what\s+is\s+your\s+name|who\s+are\s+you|who\s+made\s+you)\b/i,
  /^\s*(?:tell\s+me\s+a\s+joke|make\s+me\s+laugh|sing\s+a\s+song)\b/i,
  /^\s*(?:test|testing|testing\s+1\s*2\s*3)\b/i,
  /^\s*i\s+love\s+(?:pizza|ice\s*cream|burgers?|food|music|movies?|dogs?|cats?|you)\b/i,
  /\b(?:how\s+to\s+cook|recipe\s+for|weather\s+today|what\s+is\s+the\s+capital|capital\s+of)\b/i,
  /^\s*(?:can|could|would)\s+you\s+(?:please\s+)?(?:tell|explain|show|give|help)\b/i,
];

const FINANCIAL_METRICS_AND_TERMS = new Set([
  // Revenue, earnings & profitability
  "revenue", "revenues", "profit", "profits", "profitable", "profitability",
  "earning", "earnings", "eps", "ebitda", "sales", "loss", "losses",
  "dividend", "dividends", "yield", "yields", "margin", "margins",
  "gross margin", "operating margin", "operating revenue", "operating profit",
  "net income", "guidance", "forecast", "forecasts", "outlook", "projection",
  "projections", "balance sheet", "cash flow", "free cash flow", "capex",
  "turnaround", "valuation", "market cap", "market capitalization",
  "growth", "slowdown", "slows", "slowing", "slowed", "demand", "supply",
  "pricing", "contracts", "deliveries", "shipments", "production", "orders",
  "monetization", "spending", "infrastructure",
  "cost", "costs", "operating cost", "operating costs", "expense", "expenses",
  "operating expense", "operating expenses", "overhead", "freight", "logistics",
  "fda", "drugmaker", "clinical trial", "biologics", "patent", "licensing",
  "conference", "investor day", "annual meeting", "shareholder meeting",
  "contract", "contracts", "commercial", "booking", "bookings",
  // Securities, stocks & investments
  "stock", "stocks", "share", "shares", "equity", "equities", "ticker",
  "shareholder", "shareholders", "investor", "investors", "stakeholder", "stakeholders",
  "stake", "bond", "bonds", "treasury", "treasuries",
  "debt", "credit", "loan", "loans", "default", "defaults", "yield curve",
  "ipo", "buyback", "buybacks", "repurchase", "repurchases", "dividend yield",
  "options", "futures", "derivatives", "etf", "etfs", "mutual fund",
  "hedge fund", "private equity", "venture capital", "angel investor",
  "bullish", "bearish", "volatility", "liquidity", "breakeven",
  "overweight", "underweight", "outperform", "underperform", "price target",
  // Markets, exchanges & indices
  "wall street", "nasdaq", "s&p", "s&p 500", "dow", "dow jones", "russell",
  "nifty", "sensex", "ftse", "dax", "cac", "nikkei", "hang seng", "bse", "nse",
  "stock exchange", "bourse", "forex", "fx", "currency market", "crypto market",
  // Macroeconomics & monetary policy
  "central bank", "federal reserve", "the fed", "fomc", "rbi", "reserve bank",
  "ecb", "european central bank", "bank of england", "bank of japan",
  "interest rate", "interest rates", "rate hike", "rate hikes", "rate cut", "rate cuts",
  "monetary policy", "fiscal policy", "basis points", "bps",
  "inflation", "cpi", "ppi", "pce", "core inflation", "deflation", "disinflation",
  "gdp", "gross domestic product", "recession", "stagflation", "economic growth",
  "unemployment", "payroll", "payrolls", "jobs report", "nonfarm payrolls",
  "trade deficit", "trade surplus", "tariff", "tariffs", "sanctions",
  "export", "exports", "import", "imports", "crude oil", "brent", "wti", "opec",
  "stimulus", "deficit", "surplus", "subsidies", "subsidy",
  // Corporate events & transactions
  "layoff", "layoffs", "restructuring", "acquisition", "acquisitions",
  "acquire", "acquires", "acquired", "merger", "mergers", "merge", "merges", "merged",
  "takeover", "takeovers", "spinoff", "spinoffs", "divestiture", "divestitures",
  "bankruptcy", "bankrupt", "chapter 11", "insolvency", "insolvent",
  "filing", "filings", "10-k", "10-q", "8-k", "sec filing", "sec",
  "antitrust", "subpoena", "lawsuit", "lawsuits", "litigation", "compliance",
  "regulatory", "regulation", "regulations", "regulators", "remedies", "remedy",
  "scrutiny", "probe", "investigation", "penalty", "penalties", "fine", "fines",
  "doj", "ftc", "trial", "court hearings", "patent", "licensing",
  "board of directors", "ceo", "cfo", "chief executive", "chief financial officer",
  "quarterly", "first quarter", "second quarter", "third quarter", "fourth quarter",
  "q1", "q2", "q3", "q4", "fiscal year", "fy24", "fy25", "fy26", "h1", "h2",
  "annual report", "earnings report", "earnings call", "analyst call",
  "analyst expectation", "analyst expectations", "consensus estimate", "consensus estimates",
  "price war", "price wars", "discounting", "headwind", "headwinds", "catalyst", "catalysts",
  "downsizing", "headcount", "hiring freeze"
]);

const BUSINESS_ENTITY_MARKERS = new Set([
  "company", "companies", "corp", "corporation", "corporations", "inc",
  "ltd", "limited", "llc", "plc", "pvt", "private limited", "holdings",
  "group", "industries", "technologies", "enterprises", "partners",
  "motors", "energy", "pharma", "pharmaceuticals", "bank", "banking",
  "financial", "services", "semiconductor", "semiconductors", "automaker",
  "retailer", "producer", "manufacturer", "firm", "firms", "conglomerate",
  "startup", "startups", "fintech", "hyperscaler", "carrier", "airline",
  "e-commerce", "business", "businesses", "enterprise", "division"
]);

const FINANCIAL_ACTION_VERBS = new Set([
  "reports", "reported", "reporting", "announces", "announced", "announcing",
  "beats", "beat", "beating", "misses", "missed", "missing",
  "exceeds", "exceeded", "exceeding", "surges", "surged", "surging",
  "plunges", "plunged", "plunging", "falls", "fell", "falling",
  "drops", "dropped", "dropping", "slumps", "slumped", "slumping",
  "rises", "rose", "rising", "climbs", "climbed", "climbing",
  "gains", "gained", "gaining", "rallies", "rallied", "rallying",
  "cuts", "cut", "cutting", "lowers", "lowered", "lowering",
  "raises", "raised", "raising", "hikes", "hiked", "hiking",
  "trims", "trimmed", "trimming", "slashes", "slashed", "slashing",
  "declines", "declined", "declining", "contracts", "contracted", "contracting",
  "expands", "expanded", "expanding", "rebounds", "rebounded", "rebounding",
  "secures", "secured", "securing", "acquires", "acquired", "acquiring",
  "warns", "warned", "warning", "forecasts", "forecasted", "projecting",
  "slows", "slowed", "slowing", "accelerates", "accelerated", "accelerating",
  "invests", "invested", "investing", "approves", "approved", "approving",
  "settles", "settled", "settling", "files", "filed", "filing",
  "schedules", "scheduled", "scheduling", "submits", "submitted", "submitting",
  "spikes", "spiked", "spiking", "unveils", "unveiled", "unveiling",
  "launches", "launched", "launching",
  "increase", "increases", "increased", "increasing",
  "decrease", "decreases", "decreased", "decreasing"
]);

const CURRENCY_AND_NUMBER_PATTERNS = [
  /[$€£¥₹]\s*\d+(?:\.\d+)?/,
  /\b\d+(?:\.\d+)?\s*(?:percent|%|bps|basis\s+points)\b/i,
  /\b\d+(?:\.\d+)?\s*(?:billion|billions|million|millions|trillion|trillions|crore|crores|lakh|lakhs)\b/i,
  /\b(?:usd|inr|eur|gbp|jpy|cny)\s*\d+/i,
  /\b\d+\s*(?:cents?|pence)\s+per\s+share\b/i,
  /\$[A-Z]{1,5}\b/,
];

const KNOWN_ENTERPRISES = new Set([
  "apple", "microsoft", "nvidia", "tesla", "alphabet", "google", "amazon",
  "meta", "netflix", "jpmorgan", "chase", "goldman sachs", "morgan stanley",
  "bank of america", "citigroup", "wells fargo", "pfizer", "moderna",
  "eli lilly", "johnson & johnson", "exxonmobil", "chevron", "bp", "shell",
  "reliance", "reliance industries", "tata motors", "tata consultancy services",
  "tcs", "infosys", "wipro", "hcl tech", "hdfc", "hdfc bank", "icici bank",
  "state bank of india", "sbi", "bharti airtel", "adani", "adani enterprises",
  "larsen & toubro", "itc", "maruti suzuki", "bajaj finance", "sun pharma",
  "tsmc", "asml", "samsung", "toyota", "volkswagen", "alibaba", "tencent"
]);

function hasRepeatedCharacters(text: string): boolean {
  return /(.)\1{4,}/.test(text);
}

function hasGibberishWords(words: string[]): boolean {
  for (const w of words) {
    const wl = w.toLowerCase();
    if (wl.length >= 6) {
      if (/[bcdfghjklmnpqrstvwxz]{5,}/.test(wl)) return true;
      if (!/[aeiouy]/.test(wl)) return true;
    }
  }
  return false;
}

export function validateFinancialHeadline(text: string | null | undefined): HeadlineValidationResult {
  if (text === null || text === undefined) {
    return {
      isValid: false,
      cleaned: "",
      errorCode: ERROR_HEADLINE_EMPTY,
      message: "Headline text cannot be empty or null.",
      charCount: 0,
    };
  }

  const cleaned = text.trim();
  const charCount = cleaned.length;

  if (charCount === 0) {
    return {
      isValid: false,
      cleaned: "",
      errorCode: ERROR_HEADLINE_EMPTY,
      message: "Headline text cannot be empty or whitespace-only.",
      charCount: 0,
    };
  }

  // 1. Strict 1,000-character upper limit
  if (charCount > MAX_HEADLINE_LENGTH) {
    return {
      isValid: false,
      cleaned,
      errorCode: ERROR_HEADLINE_TOO_LONG,
      message: `Headline exceeds the ${MAX_HEADLINE_LENGTH}-character limit (current length: ${charCount} characters).`,
      charCount,
    };
  }

  // 2. Character and structural sanity
  if (/^[\d\s\.,;:+-]+$/.test(cleaned)) {
    return {
      isValid: false,
      cleaned,
      errorCode: ERROR_INVALID_FINANCIAL_HEADLINE,
      message: INVALID_FINANCIAL_HEADLINE_MESSAGE,
      charCount,
    };
  }

  if (!/[a-zA-Z]/.test(cleaned)) {
    return {
      isValid: false,
      cleaned,
      errorCode: ERROR_INVALID_FINANCIAL_HEADLINE,
      message: INVALID_FINANCIAL_HEADLINE_MESSAGE,
      charCount,
    };
  }

  if (hasRepeatedCharacters(cleaned)) {
    return {
      isValid: false,
      cleaned,
      errorCode: ERROR_INVALID_FINANCIAL_HEADLINE,
      message: INVALID_FINANCIAL_HEADLINE_MESSAGE,
      charCount,
    };
  }

  for (const pattern of CONVERSATIONAL_PATTERNS) {
    if (pattern.test(cleaned)) {
      return {
        isValid: false,
        cleaned,
        errorCode: ERROR_INVALID_FINANCIAL_HEADLINE,
        message: INVALID_FINANCIAL_HEADLINE_MESSAGE,
        charCount,
      };
    }
  }

  const words = cleaned.match(/\b[\w'-]+\b/g) || [];

  if (hasGibberishWords(words)) {
    return {
      isValid: false,
      cleaned,
      errorCode: ERROR_INVALID_FINANCIAL_HEADLINE,
      message: INVALID_FINANCIAL_HEADLINE_MESSAGE,
      charCount,
    };
  }

  const wordSet = new Set(words.map((w) => w.toLowerCase()));
  if (words.length >= 4 && wordSet.size <= 2) {
    return {
      isValid: false,
      cleaned,
      errorCode: ERROR_INVALID_FINANCIAL_HEADLINE,
      message: INVALID_FINANCIAL_HEADLINE_MESSAGE,
      charCount,
    };
  }

  // 3. Contextual Financial Relevance Detection
  const cleanedLower = cleaned.toLowerCase();
  const cleanedNormalized = cleanedLower.replace(/-/g, " ");
  let financialSignals = 0;

  // Dimension A: Financial metrics & terms
  for (const term of FINANCIAL_METRICS_AND_TERMS) {
    if (term.includes(" ")) {
      if (cleanedLower.includes(term) || cleanedNormalized.includes(term)) {
        financialSignals += 3;
      }
    } else {
      const regex = new RegExp(`\\b${term}\\b`, "i");
      if (regex.test(cleanedLower) || regex.test(cleanedNormalized)) {
        financialSignals += 2;
      }
    }
  }

  // Dimension B: Business entity markers
  for (const entity of BUSINESS_ENTITY_MARKERS) {
    const regex = new RegExp(`\\b${entity}\\b`, "i");
    if (regex.test(cleanedLower) || regex.test(cleanedNormalized)) {
      financialSignals += 2;
    }
  }

  // Dimension C: Financial action verbs
  for (const verb of FINANCIAL_ACTION_VERBS) {
    const regex = new RegExp(`\\b${verb}\\b`, "i");
    if (regex.test(cleanedLower) || regex.test(cleanedNormalized)) {
      financialSignals += 1;
    }
  }

  // Dimension D: Currency & numbers
  for (const numPat of CURRENCY_AND_NUMBER_PATTERNS) {
    if (numPat.test(cleaned)) {
      financialSignals += 2;
    }
  }

  // Dimension E: Known enterprises
  for (const comp of KNOWN_ENTERPRISES) {
    const regex = new RegExp(`\\b${comp}\\b`, "i");
    if (regex.test(cleanedLower) || regex.test(cleanedNormalized)) {
      financialSignals += 2;
      break;
    }
  }

  if (financialSignals < 3) {
    return {
      isValid: false,
      cleaned,
      errorCode: ERROR_INVALID_FINANCIAL_HEADLINE,
      message: INVALID_FINANCIAL_HEADLINE_MESSAGE,
      charCount,
    };
  }

  // 4. Minimum length boundary
  if (charCount < MIN_HEADLINE_LENGTH) {
    return {
      isValid: false,
      cleaned,
      errorCode: ERROR_HEADLINE_TOO_SHORT,
      message: `Headline is too short (${charCount} characters). Minimum required length is ${MIN_HEADLINE_LENGTH} characters.`,
      charCount,
    };
  }

  const alphaCount = (cleaned.match(/[a-zA-Z]/g) || []).length;
  if (alphaCount / charCount < 0.30) {
    return {
      isValid: false,
      cleaned,
      errorCode: ERROR_INVALID_FINANCIAL_HEADLINE,
      message: INVALID_FINANCIAL_HEADLINE_MESSAGE,
      charCount,
    };
  }

  if (words.length < 3) {
    return {
      isValid: false,
      cleaned,
      errorCode: ERROR_INVALID_FINANCIAL_HEADLINE,
      message: INVALID_FINANCIAL_HEADLINE_MESSAGE,
      charCount,
    };
  }

  return {
    isValid: true,
    cleaned,
    errorCode: null,
    message: null,
    charCount,
  };
}
