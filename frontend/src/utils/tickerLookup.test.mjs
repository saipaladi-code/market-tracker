import assert from 'node:assert/strict';

// Test ticker lookup and broker routing logic for Groww
const INDIAN_INSTRUMENTS = {
  reliance: {
    ticker: 'RELIANCE',
    url: 'https://groww.in/stocks/reliance-industries-ltd',
    actionLabel: 'Open Reliance Industries on Groww'
  },
  'reliance industries': {
    ticker: 'RELIANCE',
    url: 'https://groww.in/stocks/reliance-industries-ltd',
    actionLabel: 'Open Reliance Industries on Groww'
  },
  'tata motors': {
    ticker: 'TATAMOTORS',
    url: 'https://groww.in/stocks/tata-motors-ltd',
    actionLabel: 'Open Tata Motors on Groww'
  },
  tcs: {
    ticker: 'TCS',
    url: 'https://groww.in/stocks/tata-consultancy-services-ltd',
    actionLabel: 'Open Tata Consultancy Services on Groww'
  },
  'tata consultancy services': {
    ticker: 'TCS',
    url: 'https://groww.in/stocks/tata-consultancy-services-ltd',
    actionLabel: 'Open Tata Consultancy Services on Groww'
  },
  infosys: {
    ticker: 'INFY',
    url: 'https://groww.in/stocks/infosys-ltd',
    actionLabel: 'Open Infosys on Groww'
  },
  'hdfc bank': {
    ticker: 'HDFCBANK',
    url: 'https://groww.in/stocks/hdfc-bank-ltd',
    actionLabel: 'Open HDFC Bank on Groww'
  },
  'icici bank': {
    ticker: 'ICICIBANK',
    url: 'https://groww.in/stocks/icici-bank-ltd',
    actionLabel: 'Open ICICI Bank on Groww'
  },
  'state bank of india': {
    ticker: 'SBIN',
    url: 'https://groww.in/stocks/state-bank-of-india',
    actionLabel: 'Open State Bank of India on Groww'
  }
};

const US_INSTRUMENTS = {
  apple: {
    ticker: 'AAPL',
    isGrowwSupported: false,
    reason: 'Groww does not support active trading for US-listed equities'
  },
  microsoft: {
    ticker: 'MSFT',
    isGrowwSupported: false,
    reason: 'Groww does not support active trading for US-listed equities'
  },
  tesla: {
    ticker: 'TSLA',
    isGrowwSupported: false,
    reason: 'Groww does not support active trading for US-listed equities'
  },
  amazon: {
    ticker: 'AMZN',
    isGrowwSupported: false,
    reason: 'Groww does not support active trading for US-listed equities'
  },
  nvidia: {
    ticker: 'NVDA',
    isGrowwSupported: false,
    reason: 'Groww does not support active trading for US-listed equities'
  },
  alphabet: {
    ticker: 'GOOGL',
    isGrowwSupported: false,
    reason: 'Groww does not support active trading for US-listed equities'
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

  // 1. Check Indian Instruments -> Routed to Groww with verified stock page
  for (const c of candidates) {
    if (INDIAN_INSTRUMENTS[c]) {
      return {
        broker: 'groww',
        isSupported: true,
        destinationType: 'direct_instrument',
        directUrl: INDIAN_INSTRUMENTS[c].url,
        actionLabel: INDIAN_INSTRUMENTS[c].actionLabel,
        ticker: INDIAN_INSTRUMENTS[c].ticker
      };
    }
  }

  // 2. Check US Instruments -> Groww does NOT support active trading for US stocks
  for (const c of candidates) {
    if (US_INSTRUMENTS[c]) {
      return {
        broker: 'groww',
        isSupported: false,
        destinationType: 'unsupported',
        directUrl: null,
        portalUrl: 'https://groww.in/us-stocks/popular-us-stocks-and-etfs',
        actionLabel: 'US Stocks Unsupported on Groww',
        ticker: US_INSTRUMENTS[c].ticker
      };
    }
  }

  // 3. Other international or unknown
  return null;
}

console.log('--- RUNNING TICKER & BROKER ROUTING UNIT TESTS ---');

// Indian stocks MUST route to Groww with verified direct stock-specific URLs
const rel = resolveNavigation('Reliance Industries', null);
assert.equal(rel.broker, 'groww');
assert.equal(rel.isSupported, true);
assert.equal(rel.destinationType, 'direct_instrument');
assert.equal(rel.directUrl, 'https://groww.in/stocks/reliance-industries-ltd');
assert.equal(rel.actionLabel, 'Open Reliance Industries on Groww');

const tcs = resolveNavigation('Tata Consultancy Services (TCS)', null);
assert.equal(tcs.broker, 'groww');
assert.equal(tcs.isSupported, true);
assert.equal(tcs.directUrl, 'https://groww.in/stocks/tata-consultancy-services-ltd');
assert.equal(tcs.actionLabel, 'Open Tata Consultancy Services on Groww');

const tm = resolveNavigation('Tata Motors', null);
assert.equal(tm.broker, 'groww');
assert.equal(tm.isSupported, true);
assert.equal(tm.ticker, 'TATAMOTORS');
assert.equal(tm.directUrl, 'https://groww.in/stocks/tata-motors-ltd');

const infy = resolveNavigation('Infosys', 'INFY');
assert.equal(infy.broker, 'groww');
assert.equal(infy.isSupported, true);
assert.equal(infy.directUrl, 'https://groww.in/stocks/infosys-ltd');
assert.equal(infy.actionLabel, 'Open Infosys on Groww');

const hdfc = resolveNavigation('HDFC Bank', null);
assert.equal(hdfc.broker, 'groww');
assert.equal(hdfc.directUrl, 'https://groww.in/stocks/hdfc-bank-ltd');

const icici = resolveNavigation('ICICI Bank', null);
assert.equal(icici.broker, 'groww');
assert.equal(icici.directUrl, 'https://groww.in/stocks/icici-bank-ltd');

// US stocks MUST be clearly classified as unsupported on Groww for active trading
const apple = resolveNavigation('Apple (AAPL)', null);
assert.equal(apple.broker, 'groww');
assert.equal(apple.isSupported, false);
assert.equal(apple.destinationType, 'unsupported');
assert.equal(apple.directUrl, null);

const tesla = resolveNavigation('Tesla (TSLA)', null);
assert.equal(tesla.broker, 'groww');
assert.equal(tesla.isSupported, false);

const msft = resolveNavigation('Microsoft (MSFT)', null);
assert.equal(msft.broker, 'groww');
assert.equal(msft.isSupported, false);

const amzn = resolveNavigation('Amazon (AMZN)', null);
assert.equal(amzn.broker, 'groww');
assert.equal(amzn.isSupported, false);

const nvda = resolveNavigation('NVIDIA (NVDA)', null);
assert.equal(nvda.broker, 'groww');
assert.equal(nvda.isSupported, false);

// Other international or unverified stocks MUST NOT route to arbitrary instruments
assert.equal(resolveNavigation('Bavarian Nordic', null), null);
assert.equal(resolveNavigation('Novo Nordisk', null), null);
assert.equal(resolveNavigation('ASML', null), null);
assert.equal(resolveNavigation('Toyota Motor', null), null);
assert.equal(resolveNavigation('Unknown International Corp', null), null);
assert.equal(resolveNavigation('General Market', null), null);
assert.equal(resolveNavigation('', null), null);

console.log('ALL TICKER & BROKER ROUTING TESTS PASSED SUCCESSFULLY!');
