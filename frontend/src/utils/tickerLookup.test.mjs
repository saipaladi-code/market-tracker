import assert from 'node:assert/strict';

// Test ticker lookup and broker routing logic
const INDIAN_TICKERS = {
  'reliance': 'RELIANCE',
  'reliance industries': 'RELIANCE',
  'tata motors': 'TATAMOTORS',
  'tcs': 'TCS',
  'tata consultancy services': 'TCS',
  'infosys': 'INFY',
  'hdfc bank': 'HDFCBANK',
  'icici bank': 'ICICIBANK',
  'state bank of india': 'SBIN'
};

const US_TICKERS = {
  'apple': 'AAPL',
  'microsoft': 'MSFT',
  'tesla': 'TSLA',
  'amazon': 'AMZN',
  'nvidia': 'NVDA'
};

function normalizeText(text) {
  return (text || '').toLowerCase().replace(/['"`,]/g, '').trim();
}

function resolveBroker(company, ticker) {
  const normComp = normalizeText(company);
  const normTick = normalizeText(ticker);

  // Check parenthetical ticker in company e.g. "Tata Consultancy Services (TCS)"
  const paren = (company || '').match(/^(.*?)\s*\(([A-Za-z0-9.\-:&]+)\)\s*$/);
  let parenTicker = paren ? paren[2].trim().toLowerCase() : '';
  let parenName = paren ? paren[1].trim().toLowerCase() : '';

  // 1. Check Indian
  if (
    INDIAN_TICKERS[normComp] ||
    INDIAN_TICKERS[normTick] ||
    INDIAN_TICKERS[parenTicker] ||
    INDIAN_TICKERS[parenName]
  ) {
    return 'upstox';
  }

  // 2. Check US
  if (
    US_TICKERS[normComp] ||
    US_TICKERS[normTick] ||
    US_TICKERS[parenTicker] ||
    US_TICKERS[parenName]
  ) {
    return 'ibkr';
  }

  // 3. Other international or unknown -> no broker
  return null;
}

console.log('--- RUNNING TICKER & BROKER ROUTING UNIT TESTS ---');

// Indian stocks MUST route to Upstox
assert.equal(resolveBroker('Reliance Industries', null), 'upstox');
assert.equal(resolveBroker('Reliance', 'RELIANCE'), 'upstox');
assert.equal(resolveBroker('Tata Consultancy Services (TCS)', null), 'upstox');
assert.equal(resolveBroker('TCS', 'TCS'), 'upstox');
assert.equal(resolveBroker('Tata Motors', null), 'upstox');
assert.equal(resolveBroker('Infosys', 'INFY'), 'upstox');
assert.equal(resolveBroker('HDFC Bank', null), 'upstox');
assert.equal(resolveBroker('ICICI Bank', null), 'upstox');

// US stocks MUST route to Interactive Brokers (IBKR)
assert.equal(resolveBroker('Apple (AAPL)', null), 'ibkr');
assert.equal(resolveBroker('Apple', 'AAPL'), 'ibkr');
assert.equal(resolveBroker('Microsoft (MSFT)', null), 'ibkr');
assert.equal(resolveBroker('Microsoft', 'MSFT'), 'ibkr');
assert.equal(resolveBroker('Tesla (TSLA)', null), 'ibkr');
assert.equal(resolveBroker('Tesla', 'TSLA'), 'ibkr');
assert.equal(resolveBroker('Amazon (AMZN)', null), 'ibkr');
assert.equal(resolveBroker('NVIDIA (NVDA)', null), 'ibkr');
assert.equal(resolveBroker('Nvidia', 'NVDA'), 'ibkr');

// Other international or unverified stocks MUST NOT route to IBKR
assert.equal(resolveBroker('Bavarian Nordic', null), null);
assert.equal(resolveBroker('Novo Nordisk', null), null);
assert.equal(resolveBroker('ASML', null), null);
assert.equal(resolveBroker('Toyota Motor', null), null);
assert.equal(resolveBroker('Unknown International Corp', null), null);
assert.equal(resolveBroker('General Market', null), null);
assert.equal(resolveBroker('', null), null);

console.log('ALL TICKER & BROKER ROUTING TESTS PASSED SUCCESSFULLY!');
