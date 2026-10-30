import assert from 'node:assert/strict';

// Test ticker lookup logic
const KNOWN_TICKERS = {
  reliance: { ticker: 'RELIANCE', exchange: 'NSE', country: 'IN' },
  'tata motors': { ticker: 'TATAMOTORS', exchange: 'NSE', country: 'IN' },
  tcs: { ticker: 'TCS', exchange: 'NSE', country: 'IN' },
  infosys: { ticker: 'INFY', exchange: 'NSE', country: 'IN' },
  'hdfc bank': { ticker: 'HDFCBANK', exchange: 'NSE', country: 'IN' },
  apple: { ticker: 'AAPL', exchange: 'NASDAQ', country: 'US' },
  nvidia: { ticker: 'NVDA', exchange: 'NASDAQ', country: 'US' },
  tesla: { ticker: 'TSLA', exchange: 'NASDAQ', country: 'US' },
  microsoft: { ticker: 'MSFT', exchange: 'NASDAQ', country: 'US' },
};

function resolveVerifiedTicker(company, explicitTicker) {
  if (explicitTicker && explicitTicker.trim()) {
    return explicitTicker.trim().toUpperCase();
  }
  if (!company) return null;
  const key = company.trim().toLowerCase();
  return KNOWN_TICKERS[key]?.ticker || null;
}

console.log('--- RUNNING TICKER LOOKUP UNIT TESTS ---');

// Indian stocks
assert.equal(resolveVerifiedTicker('Reliance'), 'RELIANCE');
assert.equal(resolveVerifiedTicker('Tata Motors'), 'TATAMOTORS');
assert.equal(resolveVerifiedTicker('TCS'), 'TCS');
assert.equal(resolveVerifiedTicker('Infosys'), 'INFY');
assert.equal(resolveVerifiedTicker('HDFC Bank'), 'HDFCBANK');

// International stocks
assert.equal(resolveVerifiedTicker('Apple'), 'AAPL');
assert.equal(resolveVerifiedTicker('Nvidia'), 'NVDA');
assert.equal(resolveVerifiedTicker('Tesla'), 'TSLA');
assert.equal(resolveVerifiedTicker('Microsoft'), 'MSFT');

// Explicit ticker override
assert.equal(resolveVerifiedTicker('Unknown Entity', 'CUSTOM'), 'CUSTOM');

// Unsupported / ambiguous companies
assert.equal(resolveVerifiedTicker('General Market'), null);
assert.equal(resolveVerifiedTicker(''), null);
assert.equal(resolveVerifiedTicker(null), null);

console.log('ALL TICKER LOOKUP TESTS PASSED SUCCESSFULLY!');
