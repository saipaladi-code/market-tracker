import assert from 'node:assert/strict';

// Verified routing maps for Upstox and Groww
const INDIAN_INSTRUMENTS = {
  reliance: {
    ticker: 'RELIANCE',
    growwUrl: 'https://groww.in/stocks/reliance-industries-ltd',
    upstoxUrl: 'https://upstox.com/stocks/reliance-industries-ltd-share-price/',
    growwAction: 'Open Reliance on Groww',
    upstoxAction: 'Open Reliance in Upstox'
  },
  'reliance industries': {
    ticker: 'RELIANCE',
    growwUrl: 'https://groww.in/stocks/reliance-industries-ltd',
    upstoxUrl: 'https://upstox.com/stocks/reliance-industries-ltd-share-price/',
    growwAction: 'Open Reliance on Groww',
    upstoxAction: 'Open Reliance in Upstox'
  },
  'tata motors': {
    ticker: 'TATAMOTORS',
    growwUrl: 'https://groww.in/stocks/tata-motors-ltd',
    upstoxUrl: 'https://upstox.com/stocks/tata-motors-limited-share-price/',
    growwAction: 'Open Tata Motors on Groww',
    upstoxAction: 'Open Tata Motors in Upstox'
  },
  tcs: {
    ticker: 'TCS',
    growwUrl: 'https://groww.in/stocks/tata-consultancy-services-ltd',
    upstoxUrl: 'https://upstox.com/stocks/tata-consultancy-serv-lt-share-price/',
    growwAction: 'Open TCS on Groww',
    upstoxAction: 'Open TCS in Upstox'
  },
  'tata consultancy services': {
    ticker: 'TCS',
    growwUrl: 'https://groww.in/stocks/tata-consultancy-services-ltd',
    upstoxUrl: 'https://upstox.com/stocks/tata-consultancy-serv-lt-share-price/',
    growwAction: 'Open TCS on Groww',
    upstoxAction: 'Open TCS in Upstox'
  },
  infosys: {
    ticker: 'INFY',
    growwUrl: 'https://groww.in/stocks/infosys-ltd',
    upstoxUrl: 'https://upstox.com/stocks/infosys-limited-share-price/',
    growwAction: 'Open Infosys on Groww',
    upstoxAction: 'Open Infosys in Upstox'
  },
  'hdfc bank': {
    ticker: 'HDFCBANK',
    growwUrl: 'https://groww.in/stocks/hdfc-bank-ltd',
    upstoxUrl: 'https://upstox.com/stocks/hdfc-bank-ltd-share-price/',
    growwAction: 'Open HDFC Bank on Groww',
    upstoxAction: 'Open HDFC Bank in Upstox'
  },
  'icici bank': {
    ticker: 'ICICIBANK',
    growwUrl: 'https://groww.in/stocks/icici-bank-ltd',
    upstoxUrl: 'https://upstox.com/stocks/icici-bank-ltd-share-price/',
    growwAction: 'Open ICICI Bank on Groww',
    upstoxAction: 'Open ICICI Bank in Upstox'
  },
  'state bank of india': {
    ticker: 'SBIN',
    growwUrl: 'https://groww.in/stocks/state-bank-of-india',
    upstoxUrl: 'https://upstox.com/stocks/state-bank-of-india-share-price/',
    growwAction: 'Open SBI on Groww',
    upstoxAction: 'Open SBI in Upstox'
  },
  'bharti airtel': {
    ticker: 'BHARTIARTL',
    growwUrl: 'https://groww.in/stocks/bharti-airtel-ltd',
    upstoxUrl: 'https://upstox.com/stocks/bharti-airtel-limited-share-price/',
    growwAction: 'Open Bharti Airtel on Groww',
    upstoxAction: 'Open Bharti Airtel in Upstox'
  },
  'larsen & toubro': {
    ticker: 'LT',
    growwUrl: 'https://groww.in/stocks/larsen-toubro-ltd',
    upstoxUrl: 'https://upstox.com/stocks/larsen-toubro-ltd-share-price/',
    growwAction: 'Open Larsen & Toubro on Groww',
    upstoxAction: 'Open Larsen & Toubro in Upstox'
  },
  wipro: {
    ticker: 'WIPRO',
    growwUrl: 'https://groww.in/stocks/wipro-ltd',
    upstoxUrl: 'https://upstox.com/stocks/wipro-ltd-share-price/',
    growwAction: 'Open Wipro on Groww',
    upstoxAction: 'Open Wipro in Upstox'
  },
  marico: {
    ticker: 'MARICO',
    growwUrl: 'https://groww.in/stocks/marico-ltd',
    upstoxUrl: 'https://upstox.com/stocks/marico-limited-share-price/',
    growwAction: 'Open Marico on Groww',
    upstoxAction: 'Open Marico in Upstox'
  }
};

const US_INSTRUMENTS = {
  apple: { ticker: 'AAPL' },
  microsoft: { ticker: 'MSFT' },
  tesla: { ticker: 'TSLA' },
  amazon: { ticker: 'AMZN' },
  nvidia: { ticker: 'NVDA' },
  alphabet: { ticker: 'GOOGL' },
  meta: { ticker: 'META' },
  'jpmorgan chase': { ticker: 'JPM' },
  pfizer: { ticker: 'PFE' },
  exxonmobil: { ticker: 'XOM' }
};

function normalizeText(text) {
  return (text || '').toLowerCase().replace(/['"`,]/g, '').trim();
}

function resolveNavigation(company, ticker, requestedBroker = 'upstox') {
  const normComp = normalizeText(company);
  const normTick = normalizeText(ticker);

  const paren = (company || '').match(/^(.*?)\s*\(([A-Za-z0-9.\-:&]+)\)\s*$/);
  let parenTicker = paren ? paren[2].trim().toLowerCase() : '';
  let parenName = paren ? paren[1].trim().toLowerCase() : '';

  const candidates = [normComp, normTick, parenTicker, parenName].filter(Boolean);

  // 1. Check Indian Instruments -> Routed according to requestedBroker
  for (const c of candidates) {
    if (INDIAN_INSTRUMENTS[c]) {
      const isUpstox = requestedBroker === 'upstox';
      const inst = INDIAN_INSTRUMENTS[c];
      return {
        broker: requestedBroker,
        isSupported: true,
        destinationType: 'direct_instrument',
        directUrl: isUpstox ? inst.upstoxUrl : inst.growwUrl,
        actionLabel: isUpstox ? inst.upstoxAction : inst.growwAction,
        ticker: inst.ticker
      };
    }
  }

  // 2. Check US Instruments -> Unsupported on Indian retail brokers under RBI LRS
  for (const c of candidates) {
    if (US_INSTRUMENTS[c]) {
      return {
        broker: requestedBroker,
        isSupported: false,
        destinationType: 'unsupported',
        directUrl: null,
        portalUrl: null,
        actionLabel: 'US Stocks Unsupported on Indian Brokers',
        ticker: US_INSTRUMENTS[c].ticker,
        reason: 'RBI LRS regulations restrict active trading on Indian retail brokers'
      };
    }
  }

  // 3. Other international or unknown / general market
  return null;
}

console.log('--- RUNNING INDEPENDENT UPSTOX & GROWW ROUTING UNIT TESTS ---');

// TEST 1: Indian stocks routed to UPSTOX
console.log('Test 1: Indian stocks routed to Upstox...');
const upstoxStocks = [
  ['Reliance Industries', 'RELIANCE', 'https://upstox.com/stocks/reliance-industries-ltd-share-price/'],
  ['Tata Motors', 'TATAMOTORS', 'https://upstox.com/stocks/tata-motors-limited-share-price/'],
  ['Tata Consultancy Services (TCS)', 'TCS', 'https://upstox.com/stocks/tata-consultancy-serv-lt-share-price/'],
  ['Infosys', 'INFY', 'https://upstox.com/stocks/infosys-limited-share-price/'],
  ['HDFC Bank', 'HDFCBANK', 'https://upstox.com/stocks/hdfc-bank-ltd-share-price/'],
  ['ICICI Bank', 'ICICIBANK', 'https://upstox.com/stocks/icici-bank-ltd-share-price/'],
  ['State Bank of India', 'SBIN', 'https://upstox.com/stocks/state-bank-of-india-share-price/'],
  ['Bharti Airtel', 'BHARTIARTL', 'https://upstox.com/stocks/bharti-airtel-limited-share-price/'],
  ['Larsen & Toubro', 'LT', 'https://upstox.com/stocks/larsen-toubro-ltd-share-price/'],
  ['Wipro', 'WIPRO', 'https://upstox.com/stocks/wipro-ltd-share-price/'],
  ['Marico', 'MARICO', 'https://upstox.com/stocks/marico-limited-share-price/'],
];

for (const [company, expectedTicker, expectedUrl] of upstoxStocks) {
  const res = resolveNavigation(company, null, 'upstox');
  assert.equal(res.broker, 'upstox');
  assert.equal(res.isSupported, true);
  assert.equal(res.destinationType, 'direct_instrument');
  assert.equal(res.ticker, expectedTicker);
  assert.equal(res.directUrl, expectedUrl);
}
console.log('  -> All 11 Indian stocks correctly routed to Upstox direct URLs.');

// TEST 2: Indian stocks routed to GROWW
console.log('Test 2: Indian stocks routed to Groww...');
const growwStocks = [
  ['Reliance Industries', 'RELIANCE', 'https://groww.in/stocks/reliance-industries-ltd'],
  ['Tata Motors', 'TATAMOTORS', 'https://groww.in/stocks/tata-motors-ltd'],
  ['Tata Consultancy Services (TCS)', 'TCS', 'https://groww.in/stocks/tata-consultancy-services-ltd'],
  ['Infosys', 'INFY', 'https://groww.in/stocks/infosys-ltd'],
  ['HDFC Bank', 'HDFCBANK', 'https://groww.in/stocks/hdfc-bank-ltd'],
  ['ICICI Bank', 'ICICIBANK', 'https://groww.in/stocks/icici-bank-ltd'],
  ['State Bank of India', 'SBIN', 'https://groww.in/stocks/state-bank-of-india'],
  ['Bharti Airtel', 'BHARTIARTL', 'https://groww.in/stocks/bharti-airtel-ltd'],
  ['Larsen & Toubro', 'LT', 'https://groww.in/stocks/larsen-toubro-ltd'],
  ['Wipro', 'WIPRO', 'https://groww.in/stocks/wipro-ltd'],
  ['Marico', 'MARICO', 'https://groww.in/stocks/marico-ltd'],
];

for (const [company, expectedTicker, expectedUrl] of growwStocks) {
  const res = resolveNavigation(company, null, 'groww');
  assert.equal(res.broker, 'groww');
  assert.equal(res.isSupported, true);
  assert.equal(res.destinationType, 'direct_instrument');
  assert.equal(res.ticker, expectedTicker);
  assert.equal(res.directUrl, expectedUrl);
}
console.log('  -> All 11 Indian stocks correctly routed to Groww direct URLs.');

// TEST 3: Strict anti-redirection guarantee
console.log('Test 3: Strict broker destination non-mismatch...');
const iciciUpstox = resolveNavigation('ICICI Bank', null, 'upstox');
assert.equal(iciciUpstox.broker, 'upstox');
assert.match(iciciUpstox.directUrl, /upstox\.com/);
assert.doesNotMatch(iciciUpstox.directUrl, /groww\.in/);

const iciciGroww = resolveNavigation('ICICI Bank', null, 'groww');
assert.equal(iciciGroww.broker, 'groww');
assert.match(iciciGroww.directUrl, /groww\.in/);
assert.doesNotMatch(iciciGroww.directUrl, /upstox\.com/);

// TEST 4: US stocks unsupported status
console.log('Test 4: US stocks unsupported status under RBI LRS...');
const usList = ['Apple (AAPL)', 'Tesla (TSLA)', 'Microsoft (MSFT)', 'Amazon (AMZN)', 'NVIDIA (NVDA)', 'Meta', 'Pfizer'];
for (const stock of usList) {
  const res = resolveNavigation(stock, null, 'upstox');
  assert.equal(res.isSupported, false);
  assert.equal(res.destinationType, 'unsupported');
  assert.equal(res.directUrl, null);
}
console.log('  -> US stocks clearly flagged as unsupported for active trading on Indian retail brokers.');

// TEST 5: General market & macroeconomic news suppression
console.log('Test 5: General market news suppression...');
assert.equal(resolveNavigation('General Market', null), null);
assert.equal(resolveNavigation('RBI Monetary Policy Committee Review', null), null);
assert.equal(resolveNavigation('Bavarian Nordic', null), null);
assert.equal(resolveNavigation('Unknown Macro Indicator', null), null);
assert.equal(resolveNavigation('', null), null);
console.log('  -> General market articles do not produce misleading stock trading routes.');

console.log('ALL UNIT TESTS PASSED SUCCESSFULLY!');
