/**
 * Verified ticker and exchange mapping for Indian and International companies.
 */
export const KNOWN_TICKERS: Record<string, { ticker: string; exchange: string; country: string }> = {
  // Indian Equities (NSE)
  reliance: { ticker: 'RELIANCE', exchange: 'NSE', country: 'IN' },
  'reliance industries': { ticker: 'RELIANCE', exchange: 'NSE', country: 'IN' },
  ril: { ticker: 'RELIANCE', exchange: 'NSE', country: 'IN' },
  'tata motors': { ticker: 'TATAMOTORS', exchange: 'NSE', country: 'IN' },
  tatamotors: { ticker: 'TATAMOTORS', exchange: 'NSE', country: 'IN' },
  tcs: { ticker: 'TCS', exchange: 'NSE', country: 'IN' },
  'tata consultancy services': { ticker: 'TCS', exchange: 'NSE', country: 'IN' },
  infosys: { ticker: 'INFY', exchange: 'NSE', country: 'IN' },
  infy: { ticker: 'INFY', exchange: 'NSE', country: 'IN' },
  'hdfc bank': { ticker: 'HDFCBANK', exchange: 'NSE', country: 'IN' },
  hdfcbank: { ticker: 'HDFCBANK', exchange: 'NSE', country: 'IN' },
  'icici bank': { ticker: 'ICICIBANK', exchange: 'NSE', country: 'IN' },
  icicibank: { ticker: 'ICICIBANK', exchange: 'NSE', country: 'IN' },
  sbin: { ticker: 'SBIN', exchange: 'NSE', country: 'IN' },
  sbi: { ticker: 'SBIN', exchange: 'NSE', country: 'IN' },
  'state bank of india': { ticker: 'SBIN', exchange: 'NSE', country: 'IN' },
  'bharti airtel': { ticker: 'BHARTIARTL', exchange: 'NSE', country: 'IN' },
  airtel: { ticker: 'BHARTIARTL', exchange: 'NSE', country: 'IN' },
  'larsen & toubro': { ticker: 'LT', exchange: 'NSE', country: 'IN' },
  lt: { ticker: 'LT', exchange: 'NSE', country: 'IN' },
  wipro: { ticker: 'WIPRO', exchange: 'NSE', country: 'IN' },

  // International Equities (NASDAQ / NYSE)
  apple: { ticker: 'AAPL', exchange: 'NASDAQ', country: 'US' },
  aapl: { ticker: 'AAPL', exchange: 'NASDAQ', country: 'US' },
  nvidia: { ticker: 'NVDA', exchange: 'NASDAQ', country: 'US' },
  nvda: { ticker: 'NVDA', exchange: 'NASDAQ', country: 'US' },
  tesla: { ticker: 'TSLA', exchange: 'NASDAQ', country: 'US' },
  tsla: { ticker: 'TSLA', exchange: 'NASDAQ', country: 'US' },
  microsoft: { ticker: 'MSFT', exchange: 'NASDAQ', country: 'US' },
  msft: { ticker: 'MSFT', exchange: 'NASDAQ', country: 'US' },
  alphabet: { ticker: 'GOOGL', exchange: 'NASDAQ', country: 'US' },
  google: { ticker: 'GOOGL', exchange: 'NASDAQ', country: 'US' },
  googl: { ticker: 'GOOGL', exchange: 'NASDAQ', country: 'US' },
  amazon: { ticker: 'AMZN', exchange: 'NASDAQ', country: 'US' },
  amzn: { ticker: 'AMZN', exchange: 'NASDAQ', country: 'US' },
  meta: { ticker: 'META', exchange: 'NASDAQ', country: 'US' },
  facebook: { ticker: 'META', exchange: 'NASDAQ', country: 'US' },
  'jpmorgan chase': { ticker: 'JPM', exchange: 'NYSE', country: 'US' },
  jpmorgan: { ticker: 'JPM', exchange: 'NYSE', country: 'US' },
  jpm: { ticker: 'JPM', exchange: 'NYSE', country: 'US' },
  pfizer: { ticker: 'PFE', exchange: 'NYSE', country: 'US' },
  pfe: { ticker: 'PFE', exchange: 'NYSE', country: 'US' },
  exxonmobil: { ticker: 'XOM', exchange: 'NYSE', country: 'US' },
  exxon: { ticker: 'XOM', exchange: 'NYSE', country: 'US' },
  xom: { ticker: 'XOM', exchange: 'NYSE', country: 'US' },
};

export function resolveVerifiedTicker(company?: string, explicitTicker?: string): string | null {
  if (explicitTicker && explicitTicker.trim()) {
    return explicitTicker.trim().toUpperCase();
  }
  if (!company) return null;
  const key = company.trim().toLowerCase();
  return KNOWN_TICKERS[key]?.ticker || null;
}
