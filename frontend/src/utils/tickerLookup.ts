import { BrokerDestination, CompanyTradingRoute } from '../types';

export interface VerifiedInstrumentMeta {
  company: string;
  short_name: string;
  ticker: string;
  exchange: string;
  country: 'IN' | 'US';
  isin?: string;
  preferredBroker: 'upstox' | 'ibkr';
  brokerName: string;
  destination_type: 'direct_instrument' | 'verified_portal_with_ticker_search';
  direct_url?: string;
  portal_fallback_url: string;
  entryUrl: string;
  action_label: string;
  share_class_note?: string;
}

export const UPSTOX_BROKER_DEST: BrokerDestination = {
  broker_id: 'upstox',
  broker_name: 'Upstox Pro',
  country: 'IN',
  market_coverage: 'Indian Equities, F&O, Currency & Commodity (NSE & BSE)',
  entry_url: 'https://pro.upstox.com',
  direct_url: null,
  destination_type: 'direct_instrument',
  is_direct_link_verified: true,
  requires_user_login: true,
  action_label: 'Open in Upstox',
  instructions: 'Review the verified stock page on Upstox. To place an order, sign in to your Upstox Pro account and execute the order.',
  compliance_notice: 'Orders must be authenticated and submitted directly on Upstox. FIN-SENTIMENT never stores brokerage credentials or automates trading.'
};

export const IBKR_BROKER_DEST: BrokerDestination = {
  broker_id: 'ibkr',
  broker_name: 'Interactive Brokers (IBKR)',
  country: 'US',
  market_coverage: 'US & Global Equities, ETFs, Options & Futures (NASDAQ, NYSE, Global)',
  entry_url: 'https://www.interactivebrokers.com/portal/',
  direct_url: null,
  destination_type: 'verified_portal_with_ticker_search',
  is_direct_link_verified: false,
  requires_user_login: true,
  action_label: 'Open in Interactive Brokers',
  instructions: 'Log in to the IBKR Client Portal and search for the ticker to review real-time quote depth and execute your order.',
  compliance_notice: 'IBKR trading requires individual account authorization and margin/permissions compliance. FIN-SENTIMENT does not place automated trades.'
};

/**
 * Verified Indian Stocks (NSE) -> Strictly routed to Upstox with verified stock pages
 */
const INDIAN_INSTRUMENTS: Record<string, VerifiedInstrumentMeta> = {
  reliance: {
    company: 'Reliance Industries',
    short_name: 'Reliance',
    ticker: 'RELIANCE',
    exchange: 'NSE',
    country: 'IN',
    isin: 'INE002A01018',
    preferredBroker: 'upstox',
    brokerName: 'Upstox Pro',
    destination_type: 'direct_instrument',
    direct_url: 'https://upstox.com/stocks/reliance-industries-ltd-share-price/',
    portal_fallback_url: 'https://pro.upstox.com',
    entryUrl: 'https://upstox.com/stocks/reliance-industries-ltd-share-price/',
    action_label: 'Open Reliance in Upstox'
  },
  'tata motors': {
    company: 'Tata Motors',
    short_name: 'Tata Motors',
    ticker: 'TATAMOTORS',
    exchange: 'NSE',
    country: 'IN',
    isin: 'INE155A01022',
    preferredBroker: 'upstox',
    brokerName: 'Upstox Pro',
    destination_type: 'direct_instrument',
    direct_url: 'https://upstox.com/stocks/tata-motors-limited-share-price/',
    portal_fallback_url: 'https://pro.upstox.com',
    entryUrl: 'https://upstox.com/stocks/tata-motors-limited-share-price/',
    action_label: 'Open Tata Motors in Upstox',
    share_class_note: 'Commercial vehicles & core listed equity (TATAMOTORS, NSE). Passenger vehicles division trades under TMPV.'
  },
  tcs: {
    company: 'Tata Consultancy Services',
    short_name: 'TCS',
    ticker: 'TCS',
    exchange: 'NSE',
    country: 'IN',
    isin: 'INE467B01029',
    preferredBroker: 'upstox',
    brokerName: 'Upstox Pro',
    destination_type: 'direct_instrument',
    direct_url: 'https://upstox.com/stocks/tata-consultancy-serv-lt-share-price/',
    portal_fallback_url: 'https://pro.upstox.com',
    entryUrl: 'https://upstox.com/stocks/tata-consultancy-serv-lt-share-price/',
    action_label: 'Open TCS in Upstox'
  },
  infosys: {
    company: 'Infosys',
    short_name: 'Infosys',
    ticker: 'INFY',
    exchange: 'NSE',
    country: 'IN',
    isin: 'INE009A01021',
    preferredBroker: 'upstox',
    brokerName: 'Upstox Pro',
    destination_type: 'direct_instrument',
    direct_url: 'https://upstox.com/stocks/infosys-limited-share-price/',
    portal_fallback_url: 'https://pro.upstox.com',
    entryUrl: 'https://upstox.com/stocks/infosys-limited-share-price/',
    action_label: 'Open Infosys in Upstox'
  },
  'hdfc bank': {
    company: 'HDFC Bank',
    short_name: 'HDFC Bank',
    ticker: 'HDFCBANK',
    exchange: 'NSE',
    country: 'IN',
    isin: 'INE040A01034',
    preferredBroker: 'upstox',
    brokerName: 'Upstox Pro',
    destination_type: 'direct_instrument',
    direct_url: 'https://upstox.com/stocks/hdfc-bank-ltd-share-price/',
    portal_fallback_url: 'https://pro.upstox.com',
    entryUrl: 'https://upstox.com/stocks/hdfc-bank-ltd-share-price/',
    action_label: 'Open HDFC Bank in Upstox'
  },
  'icici bank': {
    company: 'ICICI Bank',
    short_name: 'ICICI Bank',
    ticker: 'ICICIBANK',
    exchange: 'NSE',
    country: 'IN',
    isin: 'INE090A01021',
    preferredBroker: 'upstox',
    brokerName: 'Upstox Pro',
    destination_type: 'direct_instrument',
    direct_url: 'https://upstox.com/stocks/icici-bank-ltd-share-price/',
    portal_fallback_url: 'https://pro.upstox.com',
    entryUrl: 'https://upstox.com/stocks/icici-bank-ltd-share-price/',
    action_label: 'Open ICICI Bank in Upstox'
  },
  'state bank of india': {
    company: 'State Bank of India',
    short_name: 'SBI',
    ticker: 'SBIN',
    exchange: 'NSE',
    country: 'IN',
    isin: 'INE062A01020',
    preferredBroker: 'upstox',
    brokerName: 'Upstox Pro',
    destination_type: 'direct_instrument',
    direct_url: 'https://upstox.com/stocks/state-bank-of-india-share-price/',
    portal_fallback_url: 'https://pro.upstox.com',
    entryUrl: 'https://upstox.com/stocks/state-bank-of-india-share-price/',
    action_label: 'Open SBI in Upstox'
  },
  'bharti airtel': {
    company: 'Bharti Airtel',
    short_name: 'Bharti Airtel',
    ticker: 'BHARTIARTL',
    exchange: 'NSE',
    country: 'IN',
    isin: 'INE397D01024',
    preferredBroker: 'upstox',
    brokerName: 'Upstox Pro',
    destination_type: 'direct_instrument',
    direct_url: 'https://upstox.com/stocks/bharti-airtel-limited-share-price/',
    portal_fallback_url: 'https://pro.upstox.com',
    entryUrl: 'https://upstox.com/stocks/bharti-airtel-limited-share-price/',
    action_label: 'Open Bharti Airtel in Upstox'
  },
  'larsen & toubro': {
    company: 'Larsen & Toubro',
    short_name: 'Larsen & Toubro',
    ticker: 'LT',
    exchange: 'NSE',
    country: 'IN',
    isin: 'INE018A01030',
    preferredBroker: 'upstox',
    brokerName: 'Upstox Pro',
    destination_type: 'direct_instrument',
    direct_url: 'https://upstox.com/stocks/larsen-toubro-ltd-share-price/',
    portal_fallback_url: 'https://pro.upstox.com',
    entryUrl: 'https://upstox.com/stocks/larsen-toubro-ltd-share-price/',
    action_label: 'Open Larsen & Toubro in Upstox'
  },
  wipro: {
    company: 'Wipro',
    short_name: 'Wipro',
    ticker: 'WIPRO',
    exchange: 'NSE',
    country: 'IN',
    isin: 'INE075A01022',
    preferredBroker: 'upstox',
    brokerName: 'Upstox Pro',
    destination_type: 'direct_instrument',
    direct_url: 'https://upstox.com/stocks/wipro-ltd-share-price/',
    portal_fallback_url: 'https://pro.upstox.com',
    entryUrl: 'https://upstox.com/stocks/wipro-ltd-share-price/',
    action_label: 'Open Wipro in Upstox'
  }
};

/**
 * Verified US Stocks (NASDAQ / NYSE) -> Routed to Interactive Brokers (IBKR)
 */
const US_INSTRUMENTS: Record<string, VerifiedInstrumentMeta> = {
  apple: {
    company: 'Apple',
    short_name: 'Apple',
    ticker: 'AAPL',
    exchange: 'NASDAQ',
    country: 'US',
    isin: 'US0378331005',
    preferredBroker: 'ibkr',
    brokerName: 'Interactive Brokers (IBKR)',
    destination_type: 'verified_portal_with_ticker_search',
    portal_fallback_url: 'https://www.interactivebrokers.com/portal/',
    entryUrl: 'https://www.interactivebrokers.com/portal/',
    action_label: 'Open Apple in Interactive Brokers'
  },
  microsoft: {
    company: 'Microsoft',
    short_name: 'Microsoft',
    ticker: 'MSFT',
    exchange: 'NASDAQ',
    country: 'US',
    isin: 'US5949181045',
    preferredBroker: 'ibkr',
    brokerName: 'Interactive Brokers (IBKR)',
    destination_type: 'verified_portal_with_ticker_search',
    portal_fallback_url: 'https://www.interactivebrokers.com/portal/',
    entryUrl: 'https://www.interactivebrokers.com/portal/',
    action_label: 'Open Microsoft in Interactive Brokers'
  },
  nvidia: {
    company: 'Nvidia',
    short_name: 'Nvidia',
    ticker: 'NVDA',
    exchange: 'NASDAQ',
    country: 'US',
    isin: 'US67066G1040',
    preferredBroker: 'ibkr',
    brokerName: 'Interactive Brokers (IBKR)',
    destination_type: 'verified_portal_with_ticker_search',
    portal_fallback_url: 'https://www.interactivebrokers.com/portal/',
    entryUrl: 'https://www.interactivebrokers.com/portal/',
    action_label: 'Open Nvidia in Interactive Brokers'
  },
  tesla: {
    company: 'Tesla',
    short_name: 'Tesla',
    ticker: 'TSLA',
    exchange: 'NASDAQ',
    country: 'US',
    isin: 'US88160R1014',
    preferredBroker: 'ibkr',
    brokerName: 'Interactive Brokers (IBKR)',
    destination_type: 'verified_portal_with_ticker_search',
    portal_fallback_url: 'https://www.interactivebrokers.com/portal/',
    entryUrl: 'https://www.interactivebrokers.com/portal/',
    action_label: 'Open Tesla in Interactive Brokers'
  },
  alphabet_googl: {
    company: 'Alphabet (Class A)',
    short_name: 'Alphabet (GOOGL)',
    ticker: 'GOOGL',
    exchange: 'NASDAQ',
    country: 'US',
    isin: 'US02079K3059',
    preferredBroker: 'ibkr',
    brokerName: 'Interactive Brokers (IBKR)',
    destination_type: 'verified_portal_with_ticker_search',
    portal_fallback_url: 'https://www.interactivebrokers.com/portal/',
    entryUrl: 'https://www.interactivebrokers.com/portal/',
    action_label: 'Open Alphabet (GOOGL) in Interactive Brokers',
    share_class_note: 'Alphabet Inc. Class A Common Stock (Voting). For Class C Non-Voting shares, use ticker GOOG.'
  },
  alphabet_goog: {
    company: 'Alphabet (Class C)',
    short_name: 'Alphabet (GOOG)',
    ticker: 'GOOG',
    exchange: 'NASDAQ',
    country: 'US',
    isin: 'US02079K1079',
    preferredBroker: 'ibkr',
    brokerName: 'Interactive Brokers (IBKR)',
    destination_type: 'verified_portal_with_ticker_search',
    portal_fallback_url: 'https://www.interactivebrokers.com/portal/',
    entryUrl: 'https://www.interactivebrokers.com/portal/',
    action_label: 'Open Alphabet (GOOG) in Interactive Brokers',
    share_class_note: 'Alphabet Inc. Class C Capital Stock (Non-Voting). For Class A Voting shares, use ticker GOOGL.'
  },
  amazon: {
    company: 'Amazon',
    short_name: 'Amazon',
    ticker: 'AMZN',
    exchange: 'NASDAQ',
    country: 'US',
    isin: 'US0231351067',
    preferredBroker: 'ibkr',
    brokerName: 'Interactive Brokers (IBKR)',
    destination_type: 'verified_portal_with_ticker_search',
    portal_fallback_url: 'https://www.interactivebrokers.com/portal/',
    entryUrl: 'https://www.interactivebrokers.com/portal/',
    action_label: 'Open Amazon in Interactive Brokers'
  },
  'jpmorgan chase': {
    company: 'JPMorgan Chase',
    short_name: 'JPMorgan Chase',
    ticker: 'JPM',
    exchange: 'NYSE',
    country: 'US',
    isin: 'US46625H1005',
    preferredBroker: 'ibkr',
    brokerName: 'Interactive Brokers (IBKR)',
    destination_type: 'verified_portal_with_ticker_search',
    portal_fallback_url: 'https://www.interactivebrokers.com/portal/',
    entryUrl: 'https://www.interactivebrokers.com/portal/',
    action_label: 'Open JPMorgan Chase in Interactive Brokers'
  },
  pfizer: {
    company: 'Pfizer',
    short_name: 'Pfizer',
    ticker: 'PFE',
    exchange: 'NYSE',
    country: 'US',
    isin: 'US7170811035',
    preferredBroker: 'ibkr',
    brokerName: 'Interactive Brokers (IBKR)',
    destination_type: 'verified_portal_with_ticker_search',
    portal_fallback_url: 'https://www.interactivebrokers.com/portal/',
    entryUrl: 'https://www.interactivebrokers.com/portal/',
    action_label: 'Open Pfizer in Interactive Brokers'
  },
  exxonmobil: {
    company: 'ExxonMobil',
    short_name: 'ExxonMobil',
    ticker: 'XOM',
    exchange: 'NYSE',
    country: 'US',
    isin: 'US30231G1022',
    preferredBroker: 'ibkr',
    brokerName: 'Interactive Brokers (IBKR)',
    destination_type: 'verified_portal_with_ticker_search',
    portal_fallback_url: 'https://www.interactivebrokers.com/portal/',
    entryUrl: 'https://www.interactivebrokers.com/portal/',
    action_label: 'Open ExxonMobil in Interactive Brokers'
  },
  meta: {
    company: 'Meta Platforms',
    short_name: 'Meta',
    ticker: 'META',
    exchange: 'NASDAQ',
    country: 'US',
    isin: 'US30303M1027',
    preferredBroker: 'ibkr',
    brokerName: 'Interactive Brokers (IBKR)',
    destination_type: 'verified_portal_with_ticker_search',
    portal_fallback_url: 'https://www.interactivebrokers.com/portal/',
    entryUrl: 'https://www.interactivebrokers.com/portal/',
    action_label: 'Open Meta in Interactive Brokers'
  }
};

/**
 * Common Alias mapping to standard keys
 */
const ALIAS_LOOKUP: Record<string, string> = {
  // Indian aliases
  reliance: 'reliance',
  'reliance industries': 'reliance',
  'reliance industries limited': 'reliance',
  'reliance industries ltd': 'reliance',
  ril: 'reliance',
  jio: 'reliance',
  tatamotors: 'tata motors',
  'tata motors': 'tata motors',
  'tata motors limited': 'tata motors',
  'tata motors ltd': 'tata motors',
  tmcv: 'tata motors',
  tcs: 'tcs',
  'tata consultancy services': 'tcs',
  'tata consultancy': 'tcs',
  infosys: 'infosys',
  infy: 'infosys',
  'infosys limited': 'infosys',
  'hdfc bank': 'hdfc bank',
  hdfcbank: 'hdfc bank',
  hdfc: 'hdfc bank',
  'icici bank': 'icici bank',
  icicibank: 'icici bank',
  icici: 'icici bank',
  sbin: 'state bank of india',
  sbi: 'state bank of india',
  'state bank of india': 'state bank of india',
  'state bank': 'state bank of india',
  'bharti airtel': 'bharti airtel',
  airtel: 'bharti airtel',
  bhartiartl: 'bharti airtel',
  'larsen & toubro': 'larsen & toubro',
  'larsen and toubro': 'larsen & toubro',
  'l&t': 'larsen & toubro',
  lt: 'larsen & toubro',
  wipro: 'wipro',

  // US aliases
  apple: 'apple',
  aapl: 'apple',
  'apple inc': 'apple',
  'apple inc.': 'apple',
  microsoft: 'microsoft',
  msft: 'microsoft',
  'microsoft corp': 'microsoft',
  'microsoft corporation': 'microsoft',
  nvidia: 'nvidia',
  nvda: 'nvidia',
  'nvidia corp': 'nvidia',
  'nvidia corporation': 'nvidia',
  tesla: 'tesla',
  tsla: 'tesla',
  'tesla inc': 'tesla',
  'tesla inc.': 'tesla',
  alphabet: 'alphabet_googl',
  google: 'alphabet_googl',
  googl: 'alphabet_googl',
  'alphabet inc': 'alphabet_googl',
  goog: 'alphabet_goog',
  'alphabet class c': 'alphabet_goog',
  'google class c': 'alphabet_goog',
  amazon: 'amazon',
  amzn: 'amazon',
  'amazon.com': 'amazon',
  meta: 'meta',
  facebook: 'meta',
  'meta platforms': 'meta',
  'jpmorgan chase': 'jpmorgan chase',
  jpmorgan: 'jpmorgan chase',
  jpm: 'jpmorgan chase',
  chase: 'jpmorgan chase',
  pfizer: 'pfizer',
  pfe: 'pfizer',
  exxonmobil: 'exxonmobil',
  exxon: 'exxonmobil',
  xom: 'exxonmobil'
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
 * Guarantees Upstox with verified stock URLs for Indian stocks,
 * Interactive Brokers for verified US stocks, and clear unsupported
 * status for other international/unverified companies.
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
      destination_type: 'unsupported',
      direct_url: null,
      portal_fallback_url: null,
      action_label: null,
      share_class_note: null,
      brokers: [],
      recommended_broker: null,
      message: 'Trading destination not verified or currently unavailable. FIN-SENTIMENT only routes to verified broker instruments.',
      disclaimer: 'FIN-SENTIMENT never silently routes unsupported international stocks to a broker.'
    };
  }

  if (inst.country === 'IN') {
    const directUrl = inst.direct_url || 'https://pro.upstox.com';
    const upstoxBroker: BrokerDestination = {
      ...UPSTOX_BROKER_DEST,
      entry_url: directUrl,
      direct_url: inst.direct_url || null,
      destination_type: 'direct_instrument',
      is_direct_link_verified: Boolean(inst.direct_url),
      action_label: inst.action_label,
      instructions: `Review the verified ${inst.short_name} page on Upstox with live NSE charts and fundamentals. To execute a trade, log in to your Upstox Pro account and search for ${inst.ticker} on ${inst.exchange}.`
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
      destination_type: 'direct_instrument',
      direct_url: inst.direct_url || null,
      portal_fallback_url: 'https://pro.upstox.com',
      action_label: inst.action_label,
      share_class_note: inst.share_class_note || null,
      brokers: [upstoxBroker],
      recommended_broker: upstoxBroker,
      message: `Verified Indian equity instrument: ${inst.ticker} (${inst.exchange}). Official route: Upstox Pro.`,
      disclaimer: 'Sentiment scores reflect news reporting tone and do not guarantee investment performance. Always perform independent diligence.'
    };
  }

  // Verified US Stock
  const ibkrBroker: BrokerDestination = {
    ...IBKR_BROKER_DEST,
    entry_url: 'https://www.interactivebrokers.com/portal/',
    direct_url: null,
    destination_type: 'verified_portal_with_ticker_search',
    is_direct_link_verified: false,
    action_label: inst.action_label,
    instructions: `Interactive Brokers requires an authenticated session. Open the IBKR Client Portal, log in with your account, and search for ${inst.ticker} (${inst.exchange}) to review quote depth and place your order.`
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
    destination_type: 'verified_portal_with_ticker_search',
    direct_url: null,
    portal_fallback_url: 'https://www.interactivebrokers.com/portal/',
    action_label: inst.action_label,
    share_class_note: inst.share_class_note || null,
    brokers: [ibkrBroker],
    recommended_broker: ibkrBroker,
    message: `Verified US equity instrument: ${inst.ticker} (${inst.exchange}). Official route: Interactive Brokers (IBKR).`,
    disclaimer: 'Sentiment scores reflect news reporting tone and do not guarantee investment performance. Always perform independent diligence.'
  };
}
