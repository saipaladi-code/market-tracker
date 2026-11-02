import assert from 'node:assert/strict';

// Test ticker lookup and broker routing logic
const INDIAN_INSTRUMENTS = {
  reliance: {
    ticker: 'RELIANCE',
    url: 'https://upstox.com/stocks/reliance-industries-ltd-share-price/',
    actionLabel: 'Open Reliance in Upstox'
  },
  'reliance industries': {
    ticker: 'RELIANCE',
    url: 'https://upstox.com/stocks/reliance-industries-ltd-share-price/',
    actionLabel: 'Open Reliance in Upstox'
  },
  'tata motors': {
    ticker: 'TATAMOTORS',
    url: 'https://upstox.com/stocks/tata-motors-limited-share-price/',
    actionLabel: 'Open Tata Motors in Upstox'
  },
  tcs: {
    ticker: 'TCS',
    url: 'https://upstox.com/stocks/tata-consultancy-serv-lt-share-price/',
    actionLabel: 'Open TCS in Upstox'
  },
  'tata consultancy services': {
    ticker: 'TCS',
    url: 'https://upstox.com/stocks/tata-consultancy-serv-lt-share-price/',
    actionLabel: 'Open TCS in Upstox'
  },
  infosys: {
    ticker: 'INFY',
    url: 'https://upstox.com/stocks/infosys-limited-share-price/',
    actionLabel: 'Open Infosys in Upstox'
  },
  'hdfc bank': {
    ticker: 'HDFCBANK',
    url: 'https://upstox.com/stocks/hdfc-bank-ltd-share-price/',
    actionLabel: 'Open HDFC Bank in Upstox'
  },
  'icici bank': {
    ticker: 'ICICIBANK',
    url: 'https://upstox.com/stocks/icici-bank-ltd-share-price/',
    actionLabel: 'Open ICICI Bank in Upstox'
  },
  'state bank of india': {
    ticker: 'SBIN',
    url: 'https://upstox.com/stocks/state-bank-of-india-share-price/',
    actionLabel: 'Open SBI in Upstox'
  }
};

const US_INSTRUMENTS = {
  apple: {
    ticker: 'AAPL',
    actionLabel: 'Open Apple in Interactive Brokers'
  },
  microsoft: {
    ticker: 'MSFT',
    actionLabel: 'Open Microsoft in Interactive Brokers'
  },
  tesla: {
    ticker: 'TSLA',
    actionLabel: 'Open Tesla in Interactive Brokers'
  },
  amazon: {
    ticker: 'AMZN',
    actionLabel: 'Open Amazon in Interactive Brokers'
  },
  nvidia: {
    ticker: 'NVDA',
    actionLabel: 'Open Nvidia in Interactive Brokers'
  },
  alphabet: {
    ticker: 'GOOGL',
    actionLabel: 'Open Alphabet (GOOGL) in Interactive Brokers'
  }
};

function normalizeText(text) {
  return (text || '').toLowerCase().replace(/['"`,]/g, '').trim();
}

function resolveNavigation(company, ticker) {
  const normComp = normalizeText(company);
  const normTick = normalizeText(ticker);

  const paren = (company || '').match(/^(.*?)\s*\(([A-Za-z0-9.\-:&]+)\)\s*$/);
  let parenTicker = paren ? paren[2].trim().toLowerCase() : '';
  let parenName = paren ? paren[1].trim().toLowerCase() : '';

  const candidates = [normComp, normTick, parenTicker, parenName].filter(Boolean);

  // 1. Check Indian Instruments
  for (const c of candidates) {
    if (INDIAN_INSTRUMENTS[c]) {
      return {
        broker: 'upstox',
        destinationType: 'direct_instrument',
        directUrl: INDIAN_INSTRUMENTS[c].url,
        actionLabel: INDIAN_INSTRUMENTS[c].actionLabel,
        ticker: INDIAN_INSTRUMENTS[c].ticker
      };
    }
  }

  // 2. Check US Instruments
  for (const c of candidates) {
    if (US_INSTRUMENTS[c]) {
      return {
        broker: 'ibkr',
        destinationType: 'verified_portal_with_ticker_search',
        directUrl: null,
        portalUrl: 'https://www.interactivebrokers.com/portal/',
        actionLabel: US_INSTRUMENTS[c].actionLabel,
        ticker: US_INSTRUMENTS[c].ticker
      };
    }
  }

  // 3. Other international or unknown
  return null;
}

console.log('--- RUNNING TICKER & BROKER ROUTING UNIT TESTS ---');

// Indian stocks MUST route to Upstox with verified direct URLs
const rel = resolveNavigation('Reliance Industries', null);
assert.equal(rel.broker, 'upstox');
assert.equal(rel.destinationType, 'direct_instrument');
assert.equal(rel.directUrl, 'https://upstox.com/stocks/reliance-industries-ltd-share-price/');
assert.equal(rel.actionLabel, 'Open Reliance in Upstox');

const tcs = resolveNavigation('Tata Consultancy Services (TCS)', null);
assert.equal(tcs.broker, 'upstox');
assert.equal(tcs.directUrl, 'https://upstox.com/stocks/tata-consultancy-serv-lt-share-price/');

const tm = resolveNavigation('Tata Motors', null);
assert.equal(tm.broker, 'upstox');
assert.equal(tm.ticker, 'TATAMOTORS');
assert.equal(tm.directUrl, 'https://upstox.com/stocks/tata-motors-limited-share-price/');

const infy = resolveNavigation('Infosys', 'INFY');
assert.equal(infy.broker, 'upstox');
assert.equal(infy.directUrl, 'https://upstox.com/stocks/infosys-limited-share-price/');

const hdfc = resolveNavigation('HDFC Bank', null);
assert.equal(hdfc.broker, 'upstox');
assert.equal(hdfc.directUrl, 'https://upstox.com/stocks/hdfc-bank-ltd-share-price/');

const icici = resolveNavigation('ICICI Bank', null);
assert.equal(icici.broker, 'upstox');
assert.equal(icici.directUrl, 'https://upstox.com/stocks/icici-bank-ltd-share-price/');

// US stocks MUST route to Interactive Brokers (IBKR)
const apple = resolveNavigation('Apple (AAPL)', null);
assert.equal(apple.broker, 'ibkr');
assert.equal(apple.destinationType, 'verified_portal_with_ticker_search');
assert.equal(apple.actionLabel, 'Open Apple in Interactive Brokers');
assert.equal(apple.portalUrl, 'https://www.interactivebrokers.com/portal/');

const tesla = resolveNavigation('Tesla (TSLA)', null);
assert.equal(tesla.broker, 'ibkr');
assert.equal(tesla.actionLabel, 'Open Tesla in Interactive Brokers');

const msft = resolveNavigation('Microsoft (MSFT)', null);
assert.equal(msft.broker, 'ibkr');

const amzn = resolveNavigation('Amazon (AMZN)', null);
assert.equal(amzn.broker, 'ibkr');

const nvda = resolveNavigation('NVIDIA (NVDA)', null);
assert.equal(nvda.broker, 'ibkr');

// Other international or unverified stocks MUST NOT route to IBKR
assert.equal(resolveNavigation('Bavarian Nordic', null), null);
assert.equal(resolveNavigation('Novo Nordisk', null), null);
assert.equal(resolveNavigation('ASML', null), null);
assert.equal(resolveNavigation('Toyota Motor', null), null);
assert.equal(resolveNavigation('Unknown International Corp', null), null);
assert.equal(resolveNavigation('General Market', null), null);
assert.equal(resolveNavigation('', null), null);

console.log('ALL TICKER & BROKER ROUTING TESTS PASSED SUCCESSFULLY!');
