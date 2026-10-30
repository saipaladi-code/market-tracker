import { BrokerDestination, CompanyTradingRoute } from '../types';

export interface VerifiedInstrumentMeta {
  company: string;
  ticker: string;
  exchange: string;
  country: 'IN' | 'US';
  isin?: string;
  preferredBroker: 'upstox' | 'ibkr';
  brokerName: string;
  entryUrl: string;
}

export const UPSTOX_BROKER_DEST: BrokerDestination = {
  broker_id: 'upstox',
  broker_name: 'Upstox Pro',
  country: 'IN',
  market_coverage: 'Indian Equities, F&O, Currency & Commodity (NSE & BSE)',
  entry_url: 'https://pro.upstox.com',
  is_direct_link_verified: false,
  requires_user_login: true,
  instructions: 'Sign in to your Upstox Pro account and search for the ticker on NSE/BSE to place your order.',
  compliance_notice: 'Orders must be authenticated and submitted directly on Upstox. FIN-SENTIMENT never stores brokerage credentials or automates trading.'
};

export const IBKR_BROKER_DEST: BrokerDestination = {
  broker_id: 'ibkr',
  broker_name: 'Interactive Brokers (IBKR)',
  country: 'US',
  market_coverage: 'US & Global Equities, ETFs, Options & Futures (NASDAQ, NYSE, Global)',
  entry_url: 'https://www.interactivebrokers.com/portal/',
  is_direct_link_verified: false,
  requires_user_login: true,
  instructions: 'Log in to the IBKR Client Portal and search for the ticker to review real-time market depth and execute your order.',
  compliance_notice: 'IBKR trading requires individual account authorization and margin/permissions compliance. FIN-SENTIMENT does not place automated trades.'
};

/**
 * Verified Indian Stocks (NSE) -> Strictly routed to Upstox Pro
 */
const INDIAN_INSTRUMENTS: Record<string, VerifiedInstrumentMeta> = {
  reliance: {
    company: 'Reliance Industries',
    ticker: 'RELIANCE',
    exchange: 'NSE',
    country: 'IN',
    isin: 'INE002A01018',
    preferredBroker: 'upstox',
    brokerName: 'Upstox Pro',
    entryUrl: 'https://pro.upstox.com'
  },
  'tata motors': {
    company: 'Tata Motors',
    ticker: 'TATAMOTORS',
    exchange: 'NSE',
    country: 'IN',
    isin: 'INE155A01022',
    preferredBroker: 'upstox',
    brokerName: 'Upstox Pro',
    entryUrl: 'https://pro.upstox.com'
  },
  tcs: {
    company: 'Tata Consultancy Services',
    ticker: 'TCS',
    exchange: 'NSE',
    country: 'IN',
    isin: 'INE467B01029',
    preferredBroker: 'upstox',
    brokerName: 'Upstox Pro',
    entryUrl: 'https://pro.upstox.com'
  },
  infosys: {
    company: 'Infosys',
    ticker: 'INFY',
    exchange: 'NSE',
    country: 'IN',
    isin: 'INE009A01021',
    preferredBroker: 'upstox',
    brokerName: 'Upstox Pro',
    entryUrl: 'https://pro.upstox.com'
  },
  'hdfc bank': {
    company: 'HDFC Bank',
    ticker: 'HDFCBANK',
    exchange: 'NSE',
    country: 'IN',
    isin: 'INE040A01034',
    preferredBroker: 'upstox',
    brokerName: 'Upstox Pro',
    entryUrl: 'https://pro.upstox.com'
  },
  'icici bank': {
    company: 'ICICI Bank',
    ticker: 'ICICIBANK',
    exchange: 'NSE',
    country: 'IN',
    isin: 'INE090A01021',
    preferredBroker: 'upstox',
    brokerName: 'Upstox Pro',
    entryUrl: 'https://pro.upstox.com'
  },
  'state bank of india': {
    company: 'State Bank of India',
    ticker: 'SBIN',
    exchange: 'NSE',
    country: 'IN',
    isin: 'INE062A01020',
    preferredBroker: 'upstox',
    brokerName: 'Upstox Pro',
    entryUrl: 'https://pro.upstox.com'
  },
  'bharti airtel': {
    company: 'Bharti Airtel',
    ticker: 'BHARTIARTL',
    exchange: 'NSE',
    country: 'IN',
    isin: 'INE397D01024',
    preferredBroker: 'upstox',
    brokerName: 'Upstox Pro',
    entryUrl: 'https://pro.upstox.com'
  },
  'larsen & toubro': {
    company: 'Larsen & Toubro',
    ticker: 'LT',
    exchange: 'NSE',
    country: 'IN',
    isin: 'INE018A01030',
    preferredBroker: 'upstox',
    brokerName: 'Upstox Pro',
    entryUrl: 'https://pro.upstox.com'
  },
  wipro: {
    company: 'Wipro',
    ticker: 'WIPRO',
    exchange: 'NSE',
    country: 'IN',
    isin: 'INE075A01022',
    preferredBroker: 'upstox',
    brokerName: 'Upstox Pro',
    entryUrl: 'https://pro.upstox.com'
  }
};

/**
 * Verified US Stocks (NASDAQ / NYSE) -> Routed to Interactive Brokers (IBKR)
 */
const US_INSTRUMENTS: Record<string, VerifiedInstrumentMeta> = {
  apple: {
    company: 'Apple',
    ticker: 'AAPL',
    exchange: 'NASDAQ',
    country: 'US',
    isin: 'US0378331005',
    preferredBroker: 'ibkr',
    brokerName: 'Interactive Brokers (IBKR)',
    entryUrl: 'https://www.interactivebrokers.com/portal/'
  },
  microsoft: {
    company: 'Microsoft',
    ticker: 'MSFT',
    exchange: 'NASDAQ',
    country: 'US',
    isin: 'US5949181045',
    preferredBroker: 'ibkr',
    brokerName: 'Interactive Brokers (IBKR)',
    entryUrl: 'https://www.interactivebrokers.com/portal/'
  },
  nvidia: {
    company: 'Nvidia',
    ticker: 'NVDA',
    exchange: 'NASDAQ',
    country: 'US',
    isin: 'US67066G1040',
    preferredBroker: 'ibkr',
    brokerName: 'Interactive Brokers (IBKR)',
    entryUrl: 'https://www.interactivebrokers.com/portal/'
  },
  tesla: {
    company: 'Tesla',
    ticker: 'TSLA',
    exchange: 'NASDAQ',
    country: 'US',
    isin: 'US88160R1014',
    preferredBroker: 'ibkr',
    brokerName: 'Interactive Brokers (IBKR)',
    entryUrl: 'https://www.interactivebrokers.com/portal/'
  },
  alphabet: {
    company: 'Alphabet',
    ticker: 'GOOGL',
    exchange: 'NASDAQ',
    country: 'US',
    isin: 'US02079K3059',
    preferredBroker: 'ibkr',
    brokerName: 'Interactive Brokers (IBKR)',
    entryUrl: 'https://www.interactivebrokers.com/portal/'
  },
  amazon: {
    company: 'Amazon',
    ticker: 'AMZN',
    exchange: 'NASDAQ',
    country: 'US',
    isin: 'US0231351067',
    preferredBroker: 'ibkr',
    brokerName: 'Interactive Brokers (IBKR)',
    entryUrl: 'https://www.interactivebrokers.com/portal/'
  },
  'jpmorgan chase': {
    company: 'JPMorgan Chase',
    ticker: 'JPM',
    exchange: 'NYSE',
    country: 'US',
    isin: 'US46625H1005',
    preferredBroker: 'ibkr',
    brokerName: 'Interactive Brokers (IBKR)',
    entryUrl: 'https://www.interactivebrokers.com/portal/'
  },
  pfizer: {
    company: 'Pfizer',
    ticker: 'PFE',
    exchange: 'NYSE',
    country: 'US',
    isin: 'US7170811035',
    preferredBroker: 'ibkr',
    brokerName: 'Interactive Brokers (IBKR)',
    entryUrl: 'https://www.interactivebrokers.com/portal/'
  },
  exxonmobil: {
    company: 'ExxonMobil',
    ticker: 'XOM',
    exchange: 'NYSE',
    country: 'US',
    isin: 'US30231G1022',
    preferredBroker: 'ibkr',
    brokerName: 'Interactive Brokers (IBKR)',
    entryUrl: 'https://www.interactivebrokers.com/portal/'
  },
  meta: {
    company: 'Meta Platforms',
    ticker: 'META',
    exchange: 'NASDAQ',
    country: 'US',
    isin: 'US30303M1027',
    preferredBroker: 'ibkr',
    brokerName: 'Interactive Brokers (IBKR)',
    entryUrl: 'https://www.interactivebrokers.com/portal/'
  }
};

/**
 * Common Alias mapping to standard keys
 */
const ALIAS_LOOKUP: Record<string, string> = {
  // Indian aliases
  'reliance': 'reliance',
  'reliance industries': 'reliance',
  'reliance industries limited': 'reliance',
  'reliance industries ltd': 'reliance',
  'ril': 'reliance',
  'jio': 'reliance',
  'tatamotors': 'tata motors',
  'tata motors': 'tata motors',
  'tata motors limited': 'tata motors',
  'tata motors ltd': 'tata motors',
  'tcs': 'tcs',
  'tata consultancy services': 'tcs',
  'tata consultancy': 'tcs',
  'infosys': 'infosys',
  'infy': 'infosys',
  'infosys limited': 'infosys',
  'hdfc bank': 'hdfc bank',
  'hdfcbank': 'hdfc bank',
  'hdfc': 'hdfc bank',
  'icici bank': 'icici bank',
  'icicibank': 'icici bank',
  'icici': 'icici bank',
  'sbin': 'state bank of india',
  'sbi': 'state bank of india',
  'state bank of india': 'state bank of india',
  'state bank': 'state bank of india',
  'bharti airtel': 'bharti airtel',
  'airtel': 'bharti airtel',
  'bhartiartl': 'bharti airtel',
  'larsen & toubro': 'larsen & toubro',
  'larsen and toubro': 'larsen & toubro',
  'l&t': 'larsen & toubro',
  'lt': 'larsen & toubro',
  'wipro': 'wipro',

  // US aliases
  'apple': 'apple',
  'aapl': 'apple',
  'apple inc': 'apple',
  'apple inc.': 'apple',
  'microsoft': 'microsoft',
  'msft': 'microsoft',
  'microsoft corp': 'microsoft',
  'microsoft corporation': 'microsoft',
  'nvidia': 'nvidia',
  'nvda': 'nvidia',
  'nvidia corp': 'nvidia',
  'nvidia corporation': 'nvidia',
  'tesla': 'tesla',
  'tsla': 'tesla',
  'tesla inc': 'tesla',
  'tesla inc.': 'tesla',
  'alphabet': 'alphabet',
  'google': 'alphabet',
  'googl': 'alphabet',
  'goog': 'alphabet',
  'amazon': 'amazon',
  'amzn': 'amazon',
  'amazon.com': 'amazon',
  'meta': 'meta',
  'facebook': 'meta',
  'meta platforms': 'meta',
  'jpmorgan chase': 'jpmorgan chase',
  'jpmorgan': 'jpmorgan chase',
  'jpm': 'jpmorgan chase',
  'chase': 'jpmorgan chase',
  'pfizer': 'pfizer',
  'pfe': 'pfizer',
  'exxonmobil': 'exxonmobil',
  'exxon': 'exxonmobil',
  'xom': 'exxonmobil'
};

function normalizeText(text: string): string {
  return text
    .toLowerCase()
    .replace(/['"`,]/g, '')
    .trim();
}

function extractCandidates(identifier: string): string[] {
  const raw = identifier.trim();
  const candidates: string[] = [raw];

  // Match parenthetical symbol: e.g. "Apple (AAPL)" or "Tata Consultancy Services (TCS)"
  const paren = raw.match(/^(.*?)\s*\(([A-Za-z0-9.\-:&]+)\)\s*$/);
  if (paren) {
    if (paren[2]) candidates.push(paren[2].trim());
    if (paren[1]) candidates.push(paren[1].trim());
  }

  // Strip corporate suffixes
  for (const c of [...candidates]) {
    const stripped = c.replace(/\b(inc\.|inc|corp\.|corp|corporation|ltd\.|ltd|limited|co\.|co|plc|holdings|platforms)\b/gi, '').trim();
    if (stripped && stripped !== c) {
      candidates.push(stripped);
    }
  }

  return candidates;
}

export function resolveVerifiedInstrument(company?: string, explicitTicker?: string): VerifiedInstrumentMeta | null {
  const inputs: string[] = [];
  if (explicitTicker && explicitTicker.trim()) inputs.push(explicitTicker.trim());
  if (company && company.trim()) inputs.push(company.trim());

  for (const input of inputs) {
    const candidates = extractCandidates(input);
    for (const cand of candidates) {
      const norm = normalizeText(cand);

      // Check alias lookup
      const resolvedKey = ALIAS_LOOKUP[norm];
      if (resolvedKey) {
        if (INDIAN_INSTRUMENTS[resolvedKey]) return INDIAN_INSTRUMENTS[resolvedKey];
        if (US_INSTRUMENTS[resolvedKey]) return US_INSTRUMENTS[resolvedKey];
      }

      // Check direct Indian instrument key or ticker
      if (INDIAN_INSTRUMENTS[norm]) return INDIAN_INSTRUMENTS[norm];
      for (const inst of Object.values(INDIAN_INSTRUMENTS)) {
        if (inst.ticker.toLowerCase() === norm || inst.company.toLowerCase() === norm) {
          return inst;
        }
      }

      // Check direct US instrument key or ticker
      if (US_INSTRUMENTS[norm]) return US_INSTRUMENTS[norm];
      for (const inst of Object.values(US_INSTRUMENTS)) {
        if (inst.ticker.toLowerCase() === norm || inst.company.toLowerCase() === norm) {
          return inst;
        }
      }
    }
  }

  return null;
}

export function resolveVerifiedTicker(company?: string, explicitTicker?: string): string | null {
  const inst = resolveVerifiedInstrument(company, explicitTicker);
  return inst ? inst.ticker : null;
}

/**
 * Builds a deterministic, verified CompanyTradingRoute object.
 * Guarantees Upstox for Indian stocks, Interactive Brokers for verified US stocks,
 * and clear unsupported status for other international/unverified companies.
 */
export function getClientSideTradingRoute(company?: string, ticker?: string): CompanyTradingRoute {
  const inst = resolveVerifiedInstrument(company, ticker);
  if (!inst) {
    const rawName = (company || ticker || 'Unknown').trim();
    return {
      status: 'unsupported',
      is_tradable: false,
      company: rawName,
      ticker: null,
      exchange: null,
      country: null,
      isin: null,
      upstox_instrument_key: null,
      brokers: [],
      recommended_broker: null,
      message: 'Trading destination not verified or currently unavailable. FIN-SENTIMENT only routes to verified broker instruments.',
      disclaimer: 'FIN-SENTIMENT never silently routes unsupported international stocks to a broker.'
    };
  }

  if (inst.country === 'IN') {
    const upstoxBroker: BrokerDestination = {
      ...UPSTOX_BROKER_DEST,
      instructions: `Sign in to your Upstox Pro account and search for ${inst.ticker} (${inst.exchange}) to execute your order.`
    };
    return {
      status: 'supported',
      is_tradable: true,
      company: inst.company,
      ticker: inst.ticker,
      exchange: inst.exchange,
      country: 'IN',
      isin: inst.isin || null,
      upstox_instrument_key: `NSE_EQ|${inst.isin || ''}`,
      brokers: [upstoxBroker],
      recommended_broker: upstoxBroker,
      message: `Verified Indian equity instrument: ${inst.ticker} (${inst.exchange}). Preferred route: Upstox Pro.`,
      disclaimer: 'Sentiment scores reflect news reporting tone and do not guarantee investment performance. Always perform independent diligence.'
    };
  }

  // Verified US Stock
  const ibkrBroker: BrokerDestination = {
    ...IBKR_BROKER_DEST,
    instructions: `Log in to the IBKR Client Portal and search for ${inst.ticker} (${inst.exchange}) to review real-time quote depth and execute your order.`
  };
  return {
    status: 'supported',
    is_tradable: true,
    company: inst.company,
    ticker: inst.ticker,
    exchange: inst.exchange,
    country: 'US',
    isin: inst.isin || null,
    upstox_instrument_key: null,
    brokers: [ibkrBroker],
    recommended_broker: ibkrBroker,
    message: `Verified US equity instrument: ${inst.ticker} (${inst.exchange}). Preferred route: Interactive Brokers (IBKR).`,
    disclaimer: 'Sentiment scores reflect news reporting tone and do not guarantee investment performance. Always perform independent diligence.'
  };
}
