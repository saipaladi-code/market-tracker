import re
import math
from typing import Tuple, Optional, Dict, Any, Set

MIN_HEADLINE_LENGTH = 15
MAX_HEADLINE_LENGTH = 1000

INVALID_FINANCIAL_HEADLINE_MESSAGE = (
    "Invalid financial news headline. Please enter a relevant headline or statement "
    "about a company, stock, business, financial market, or economic event."
)

ERROR_INVALID_FINANCIAL_HEADLINE = "INVALID_FINANCIAL_HEADLINE"
ERROR_HEADLINE_TOO_SHORT = "HEADLINE_TOO_SHORT"
ERROR_HEADLINE_TOO_LONG = "HEADLINE_TOO_LONG"
ERROR_HEADLINE_EMPTY = "HEADLINE_EMPTY"


class HeadlineValidationError(ValueError):
    def __init__(
        self,
        message: str,
        error_code: str,
        char_count: int = 0,
        min_allowed: int = MIN_HEADLINE_LENGTH,
        max_allowed: int = MAX_HEADLINE_LENGTH,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.char_count = char_count
        self.min_allowed = min_allowed
        self.max_allowed = max_allowed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "detail": self.message,
            "error_code": self.error_code,
            "message": self.message,
            "character_count": self.char_count,
            "min_length": self.min_allowed,
            "max_length": self.max_allowed,
        }


# Conversational openings, greetings, or non-financial intent patterns
CONVERSATIONAL_PATTERNS = [
    re.compile(r"^\s*(?:hi|hello|hey|howdy|hola|namaste|greetings)\b", re.IGNORECASE),
    re.compile(r"^\s*(?:good\s+(?:morning|afternoon|evening|night|day))\b", re.IGNORECASE),
    re.compile(r"^\s*(?:how\s+are\s+you|how's\s+it\s+going|what's\s+up|sup)\b", re.IGNORECASE),
    re.compile(r"^\s*(?:what\s+is\s+your\s+name|who\s+are\s+you|who\s+made\s+you)\b", re.IGNORECASE),
    re.compile(r"^\s*(?:tell\s+me\s+a\s+joke|make\s+me\s+laugh|sing\s+a\s+song)\b", re.IGNORECASE),
    re.compile(r"^\s*(?:test|testing|testing\s+1\s*2\s*3)\b", re.IGNORECASE),
    re.compile(r"^\s*i\s+love\s+(?:pizza|ice\s*cream|burgers?|food|music|movies?|dogs?|cats?|you)\b", re.IGNORECASE),
    re.compile(r"\b(?:how\s+to\s+cook|recipe\s+for|weather\s+today|what\s+is\s+the\s+capital|capital\s+of)\b", re.IGNORECASE),
    re.compile(r"^\s*(?:can|could|would)\s+you\s+(?:please\s+)?(?:tell|explain|show|give|help)\b", re.IGNORECASE),
]

# High-confidence financial, market, corporate, and macroeconomic terms
FINANCIAL_METRICS_AND_TERMS: Set[str] = {
    # Revenue, earnings & profitability
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
    # Securities, stocks & investments
    "stock", "stocks", "share", "shares", "equity", "equities", "ticker",
    "shareholder", "shareholders", "investor", "investors", "stakeholder", "stakeholders",
    "stake", "bond", "bonds", "treasury", "treasuries",
    "debt", "credit", "loan", "loans", "default", "defaults", "yield curve",
    "ipo", "buyback", "buybacks", "repurchase", "repurchases", "dividend yield",
    "options", "futures", "derivatives", "etf", "etfs", "mutual fund",
    "hedge fund", "private equity", "venture capital", "angel investor",
    "bullish", "bearish", "volatility", "liquidity", "breakeven",
    "overweight", "underweight", "outperform", "underperform", "price target",
    # Markets, exchanges & indices
    "wall street", "nasdaq", "s&p", "s&p 500", "dow", "dow jones", "russell",
    "nifty", "sensex", "ftse", "dax", "cac", "nikkei", "hang seng", "bse", "nse",
    "stock exchange", "bourse", "forex", "fx", "currency market", "crypto market",
    # Macroeconomics & monetary policy
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
    # Corporate events & transactions
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
}

# Corporate entity suffixes & nouns (including Indian and international variants)
BUSINESS_ENTITY_MARKERS: Set[str] = {
    "company", "companies", "corp", "corporation", "corporations", "inc",
    "ltd", "limited", "llc", "plc", "pvt", "private limited", "holdings",
    "group", "industries", "technologies", "enterprises", "partners",
    "motors", "energy", "pharma", "pharmaceuticals", "bank", "banking",
    "financial", "services", "semiconductor", "semiconductors", "automaker",
    "retailer", "producer", "manufacturer", "firm", "firms", "conglomerate",
    "startup", "startups", "fintech", "hyperscaler", "carrier", "airline",
    "e-commerce", "business", "businesses", "enterprise", "division"
}

# Action verbs commonly tied to financial & corporate announcements
FINANCIAL_ACTION_VERBS: Set[str] = {
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
}

# Tickers & currency markers
CURRENCY_AND_NUMBER_PATTERNS = [
    re.compile(r"[$€£¥₹]\s*\d+(?:\.\d+)?"),
    re.compile(r"\b\d+(?:\.\d+)?\s*(?:percent|%|bps|basis\s+points)\b", re.IGNORECASE),
    re.compile(r"\b\d+(?:\.\d+)?\s*(?:billion|billions|million|millions|trillion|trillions|crore|crores|lakh|lakhs)\b", re.IGNORECASE),
    re.compile(r"\b(?:usd|inr|eur|gbp|jpy|cny)\s*\d+", re.IGNORECASE),
    re.compile(r"\b\d+\s*(?:cents?|pence)\s+per\s+share\b", re.IGNORECASE),
    re.compile(r"\$[A-Z]{1,5}\b"),  # e.g. $NVDA, $AAPL
]

# Prominent Indian and global corporate identifiers
KNOWN_ENTERPRISES = {
    "apple", "microsoft", "nvidia", "tesla", "alphabet", "google", "amazon",
    "meta", "netflix", "jpmorgan", "chase", "goldman sachs", "morgan stanley",
    "bank of america", "citigroup", "wells fargo", "pfizer", "moderna",
    "eli lilly", "johnson & johnson", "exxonmobil", "chevron", "bp", "shell",
    "reliance", "reliance industries", "tata motors", "tata consultancy services",
    "tcs", "infosys", "wipro", "hcl tech", "hdfc", "hdfc bank", "icici bank",
    "state bank of india", "sbi", "bharti airtel", "adani", "adani enterprises",
    "larsen & toubro", "itc", "maruti suzuki", "bajaj finance", "sun pharma",
    "tsmc", "asml", "samsung", "toyota", "volkswagen", "alibaba", "tencent"
}


def _has_repeated_characters(text: str) -> bool:
    """Detects spam or random keys smashing like 'aaaaaaa' or 'zzzzzz'."""
    return bool(re.search(r"(.)\1{4,}", text))


def _has_gibberish_words(words: list[str]) -> bool:
    """Flags words with 5+ consonants in a row or devoid of vowels (keyboard smashes)."""
    for w in words:
        wl = w.lower()
        if len(wl) >= 6:
            # Check for 5 consonants in a row (excluding y which can serve as a vowel in English)
            if re.search(r"[bcdfghjklmnpqrstvwxz]{5,}", wl):
                return True
            # Word length >= 6 with zero vowels
            if not any(v in wl for v in "aeiouy"):
                return True
    return False


def validate_financial_headline(text: Optional[str]) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Validates a financial news headline or statement.
    
    Returns:
        (cleaned_text, error_code, error_message)
        If valid: error_code and error_message are None.
        If invalid: cleaned_text is stripped input, error_code and error_message are populated.
    """
    if text is None:
        return "", ERROR_HEADLINE_EMPTY, "Headline text cannot be empty or null."

    cleaned = text.strip()

    if not cleaned:
        return "", ERROR_HEADLINE_EMPTY, "Headline text cannot be empty or whitespace-only."

    char_count = len(cleaned)

    # 1. Maximum length check (strictly 1,000 characters)
    if char_count > MAX_HEADLINE_LENGTH:
        return (
            cleaned,
            ERROR_HEADLINE_TOO_LONG,
            f"Headline exceeds the {MAX_HEADLINE_LENGTH}-character limit (current length: {char_count} characters)."
        )

    # 2. Character and structural sanity
    # Check if string is only numbers
    if re.fullmatch(r"[\d\s\.,;:+-]+", cleaned):
        return cleaned, ERROR_INVALID_FINANCIAL_HEADLINE, INVALID_FINANCIAL_HEADLINE_MESSAGE

    # Check if string is only punctuation / symbols
    if not re.search(r"[a-zA-Z]", cleaned):
        return cleaned, ERROR_INVALID_FINANCIAL_HEADLINE, INVALID_FINANCIAL_HEADLINE_MESSAGE

    # Check for character smashes or repetitive characters (e.g. "aaaaaa", "zzzzzz")
    if _has_repeated_characters(cleaned):
        return cleaned, ERROR_INVALID_FINANCIAL_HEADLINE, INVALID_FINANCIAL_HEADLINE_MESSAGE

    # Conversational / greetings / non-financial chatbot queries
    for pattern in CONVERSATIONAL_PATTERNS:
        if pattern.search(cleaned):
            return cleaned, ERROR_INVALID_FINANCIAL_HEADLINE, INVALID_FINANCIAL_HEADLINE_MESSAGE

    # Word extraction
    words = re.findall(r"\b[\w'-]+\b", cleaned)

    # Check for gibberish words (e.g. "asdfghjk")
    if _has_gibberish_words(words):
        return cleaned, ERROR_INVALID_FINANCIAL_HEADLINE, INVALID_FINANCIAL_HEADLINE_MESSAGE

    # Single-word repetitive spam (e.g. "blah blah blah blah")
    word_set = set(w.lower() for w in words)
    if len(words) >= 4 and len(word_set) <= 2:
        return cleaned, ERROR_INVALID_FINANCIAL_HEADLINE, INVALID_FINANCIAL_HEADLINE_MESSAGE

    # 3. Contextual Financial Relevance Detection
    cleaned_lower = cleaned.lower()
    cleaned_normalized = cleaned_lower.replace("-", " ")
    financial_signals = 0

    # Dimension A: Direct financial metrics & terms (match multi-word or single words)
    for term in FINANCIAL_METRICS_AND_TERMS:
        if " " in term:
            if term in cleaned_lower or term in cleaned_normalized:
                financial_signals += 3
        else:
            if re.search(r"\b" + re.escape(term) + r"\b", cleaned_lower) or re.search(r"\b" + re.escape(term) + r"\b", cleaned_normalized):
                financial_signals += 2

    # Dimension B: Business entity indicators (company, firm, Ltd, Inc, automaker, etc.)
    for entity in BUSINESS_ENTITY_MARKERS:
        if re.search(r"\b" + re.escape(entity) + r"\b", cleaned_lower) or re.search(r"\b" + re.escape(entity) + r"\b", cleaned_normalized):
            financial_signals += 2

    # Dimension C: Financial action verbs (beats, misses, reports, surges, cuts, etc.)
    for verb in FINANCIAL_ACTION_VERBS:
        if re.search(r"\b" + re.escape(verb) + r"\b", cleaned_lower) or re.search(r"\b" + re.escape(verb) + r"\b", cleaned_normalized):
            financial_signals += 1

    # Dimension D: Currency & numbers ($26 billion, 15%, 50 bps, €50M)
    for num_pattern in CURRENCY_AND_NUMBER_PATTERNS:
        if num_pattern.search(cleaned):
            financial_signals += 2

    # Dimension E: Known Indian & global corporate names
    for comp in KNOWN_ENTERPRISES:
        if re.search(r"\b" + re.escape(comp) + r"\b", cleaned_lower) or re.search(r"\b" + re.escape(comp) + r"\b", cleaned_normalized):
            financial_signals += 2
            break

    # If the text has insufficient financial relevance signals, reject as non-financial headline
    if financial_signals < 3:
        return cleaned, ERROR_INVALID_FINANCIAL_HEADLINE, INVALID_FINANCIAL_HEADLINE_MESSAGE

    # 4. Minimum length boundary (15 characters)
    if char_count < MIN_HEADLINE_LENGTH:
        return (
            cleaned,
            ERROR_HEADLINE_TOO_SHORT,
            f"Headline is too short ({char_count} characters). Minimum required length is {MIN_HEADLINE_LENGTH} characters."
        )

    # Ensure alphabetic ratio is at least 30%
    alpha_count = sum(1 for c in cleaned if c.isalpha())
    if alpha_count / char_count < 0.30:
        return cleaned, ERROR_INVALID_FINANCIAL_HEADLINE, INVALID_FINANCIAL_HEADLINE_MESSAGE

    # Word count check
    if len(words) < 3:
        return cleaned, ERROR_INVALID_FINANCIAL_HEADLINE, INVALID_FINANCIAL_HEADLINE_MESSAGE

    return cleaned, None, None


def assert_valid_financial_headline(text: Optional[str]) -> str:
    """
    Validates the headline and raises HeadlineValidationError if invalid.
    Returns cleaned text if valid.
    """
    cleaned, error_code, error_message = validate_financial_headline(text)
    if error_code is not None:
        char_count = len((text or "").strip())
        raise HeadlineValidationError(
            message=error_message or INVALID_FINANCIAL_HEADLINE_MESSAGE,
            error_code=error_code,
            char_count=char_count,
        )
    return cleaned
