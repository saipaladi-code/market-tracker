import assert from 'node:assert';
import {
  normalizeSentimentClass,
  normalizeConfidenceScore,
  buildCanonicalScores,
  getCanonicalSentimentResult,
  mergeExplanationTokens
} from './canonicalSentiment.ts';

console.log('--- RUNNING FINBERT SENTIMENT SCORE CONSISTENCY TESTS ---');

// Format function matching SentimentBadge.tsx: Math.round(confidence * 100)
function badgeDisplay(confidence) {
  return `${Math.round(confidence * 100)}%`;
}

// Format function matching ExplainModal.tsx: (score * 100).toFixed(1)
function modalProbabilityDisplay(score) {
  return `${(score * 100).toFixed(1)}%`;
}

// -------------------------------------------------------------
// TEST CASE 1: Open a bullish news card and verify its modal shows identical class & confidence
// -------------------------------------------------------------
console.log('\n[TEST 1] Bullish news card score consistency');
const bullishCardArticle = {
  id: 'art-demo-nvda-1',
  canonical_id: 'can-nvda-record-quarter-2026',
  title: 'Nvidia Reports Record Quarter as AI Infrastructure Demand Accelerates Globally',
  company: 'Nvidia',
  source: 'Bloomberg',
  published_at: '2026-10-24T14:30:00Z',
  sentiment: 'positive',
  confidence: 0.94,
  scores: { positive: 0.94, neutral: 0.04, negative: 0.02 },
  is_duplicate: false,
  is_demo: true
};

const bullishModalResult = getCanonicalSentimentResult(bullishCardArticle);

// Card badge vs Modal badge
const cardBullishBadge = badgeDisplay(bullishCardArticle.confidence);
const modalBullishBadge = badgeDisplay(bullishModalResult.confidence);
assert.strictEqual(bullishModalResult.sentiment, 'positive', 'Modal class must be positive');
assert.strictEqual(cardBullishBadge, '94%', 'Card must display BULLISH 94%');
assert.strictEqual(modalBullishBadge, '94%', 'Modal must display BULLISH 94%');
assert.strictEqual(cardBullishBadge, modalBullishBadge, 'Card and modal must show identical confidence badge');

// Modal probability distribution
assert.strictEqual(modalProbabilityDisplay(bullishModalResult.scores.positive), '94.0%', 'Modal bullish probability must be 94.0%');
assert.strictEqual(bullishModalResult.article_id, bullishCardArticle.id, 'Article ID must be preserved');
console.log('✓ PASS: Bullish news card ("art-demo-nvda-1") and modal both show BULLISH 94% (scores.positive = 94.0%)');

// -------------------------------------------------------------
// TEST CASE 2: Open a bearish news card and verify its modal shows identical class & confidence
// -------------------------------------------------------------
console.log('\n[TEST 2] Bearish news card score consistency');
const bearishCardArticle = {
  id: 'art-demo-nvda-2',
  canonical_id: 'can-nvda-export-scrutiny-2026',
  title: 'Nvidia Faces Export Scrutiny and Stricter Trade Limits in Emerging International Markets',
  company: 'Nvidia',
  source: 'Reuters',
  published_at: '2026-10-24T11:15:00Z',
  sentiment: 'negative',
  confidence: 0.89,
  scores: { positive: 0.03, neutral: 0.08, negative: 0.89 },
  is_duplicate: false,
  is_demo: true
};

const bearishModalResult = getCanonicalSentimentResult(bearishCardArticle);
const cardBearishBadge = badgeDisplay(bearishCardArticle.confidence);
const modalBearishBadge = badgeDisplay(bearishModalResult.confidence);
assert.strictEqual(bearishModalResult.sentiment, 'negative', 'Modal class must be negative');
assert.strictEqual(cardBearishBadge, '89%', 'Card must display BEARISH 89%');
assert.strictEqual(modalBearishBadge, '89%', 'Modal must display BEARISH 89%');
assert.strictEqual(cardBearishBadge, modalBearishBadge, 'Card and modal must show identical confidence badge');
assert.strictEqual(modalProbabilityDisplay(bearishModalResult.scores.negative), '89.0%', 'Modal bearish probability must be 89.0%');
console.log('✓ PASS: Bearish news card ("art-demo-nvda-2") and modal both show BEARISH 89% (scores.negative = 89.0%)');

// -------------------------------------------------------------
// TEST CASE 3: Open a neutral news card and verify its modal shows identical class & confidence
// -------------------------------------------------------------
console.log('\n[TEST 3] Neutral news card score consistency');
const neutralCardArticle = {
  id: 'art-demo-msft-2',
  canonical_id: 'can-msft-datacenter-capex-2026',
  title: 'Microsoft Signals High AI Datacenter Capital Expenditure to Meet Enterprise Capacity',
  company: 'Microsoft',
  source: 'Reuters',
  published_at: '2026-10-23T14:15:00Z',
  sentiment: 'neutral',
  confidence: 0.76,
  scores: { positive: 0.18, neutral: 0.76, negative: 0.06 },
  is_duplicate: false,
  is_demo: true
};

const neutralModalResult = getCanonicalSentimentResult(neutralCardArticle);
const cardNeutralBadge = badgeDisplay(neutralCardArticle.confidence);
const modalNeutralBadge = badgeDisplay(neutralModalResult.confidence);
assert.strictEqual(neutralModalResult.sentiment, 'neutral', 'Modal class must be neutral');
assert.strictEqual(cardNeutralBadge, '76%', 'Card must display NEUTRAL 76%');
assert.strictEqual(modalNeutralBadge, '76%', 'Modal must display NEUTRAL 76%');
assert.strictEqual(cardNeutralBadge, modalNeutralBadge, 'Card and modal must show identical confidence badge');
assert.strictEqual(modalProbabilityDisplay(neutralModalResult.scores.neutral), '76.0%', 'Modal neutral probability must be 76.0%');
console.log('✓ PASS: Neutral news card ("art-demo-msft-2") and modal both show NEUTRAL 76% (scores.neutral = 76.0%)');

// -------------------------------------------------------------
// TEST CASE 4: Open multiple different articles and ensure their predictions do not get mixed up
// -------------------------------------------------------------
console.log('\n[TEST 4] Multiple article isolation (no cross-article contamination)');
const testCorpus = [
  { id: 'art-1', title: 'Article 1 Bullish', sentiment: 'positive', confidence: 0.94, scores: { positive: 0.94, neutral: 0.04, negative: 0.02 } },
  { id: 'art-2', title: 'Article 2 Bearish', sentiment: 'negative', confidence: 0.89, scores: { positive: 0.03, neutral: 0.08, negative: 0.89 } },
  { id: 'art-3', title: 'Article 3 Bullish 88', sentiment: 'positive', confidence: 0.88, scores: { positive: 0.88, neutral: 0.08, negative: 0.04 } },
  { id: 'art-4', title: 'Article 4 Neutral 76', sentiment: 'neutral', confidence: 0.76, scores: { positive: 0.18, neutral: 0.76, negative: 0.06 } }
];

const modalResults = testCorpus.map(a => getCanonicalSentimentResult(a));
for (let i = 0; i < testCorpus.length; i++) {
  const art = testCorpus[i];
  const res = modalResults[i];
  assert.strictEqual(res.article_id, art.id, `Result ${i} must belong to article ${art.id}`);
  assert.strictEqual(res.sentiment, art.sentiment, `Result ${i} sentiment must match article`);
  assert.strictEqual(res.confidence, art.confidence, `Result ${i} confidence must match article`);
  assert.strictEqual(badgeDisplay(res.confidence), badgeDisplay(art.confidence), `Badges must match for article ${art.id}`);
}
console.log('✓ PASS: All 4 distinct articles maintain discrete canonical predictions without cross-leakage');

// -------------------------------------------------------------
// TEST CASE 5: Close and reopen a modal and verify the original result remains consistent
// -------------------------------------------------------------
console.log('\n[TEST 5] Modal close and reopen consistency');
const articleToReopen = {
  id: 'art-demo-aapl-1',
  canonical_id: 'can-apple-services-revenue-2026',
  title: 'Apple Services Revenue Hits All-Time High Despite Subdued Hardware Upgrades in China',
  company: 'Apple',
  sentiment: 'positive',
  confidence: 0.88,
  scores: { positive: 0.88, neutral: 0.08, negative: 0.04 }
};

// First open
const firstOpen = getCanonicalSentimentResult(articleToReopen);
assert.strictEqual(badgeDisplay(firstOpen.confidence), '88%');

// User closes modal (modal unmounts, selectedExplainResult = null)
let modalState = null;

// User reopens modal
modalState = getCanonicalSentimentResult(articleToReopen);
assert.strictEqual(badgeDisplay(modalState.confidence), '88%');
assert.strictEqual(modalState.confidence, firstOpen.confidence, 'Reopening must preserve identical confidence');
assert.deepStrictEqual(modalState.scores, firstOpen.scores, 'Reopening must preserve identical class probabilities');
console.log('✓ PASS: Modal close and reopen yields identical prediction (BULLISH 88%)');

// -------------------------------------------------------------
// TEST CASE 6: Refresh the page and verify card & modal consistency from stored prediction
// -------------------------------------------------------------
console.log('\n[TEST 6] Page refresh / re-hydration from stored prediction');
// Simulated database round-trip (e.g. JSON serialization/deserialization)
const storedArticleJson = JSON.stringify(bullishCardArticle);
const reloadedArticle = JSON.parse(storedArticleJson);

const refreshedCardBadge = badgeDisplay(reloadedArticle.confidence);
const refreshedModalResult = getCanonicalSentimentResult(reloadedArticle);
const refreshedModalBadge = badgeDisplay(refreshedModalResult.confidence);

assert.strictEqual(refreshedCardBadge, '94%');
assert.strictEqual(refreshedModalBadge, '94%');
assert.strictEqual(refreshedCardBadge, refreshedModalBadge);
assert.strictEqual(modalProbabilityDisplay(refreshedModalResult.scores.positive), '94.0%');
console.log('✓ PASS: Refreshed / re-hydrated page maintains 100% card-modal score consistency');

// -------------------------------------------------------------
// TEST CASE 7: Verify that explanation calculations do not overwrite the canonical prediction
// -------------------------------------------------------------
console.log('\n[TEST 7] Explanation calculations do NOT overwrite canonical prediction');
const canonicalBeforeExplain = getCanonicalSentimentResult(bullishCardArticle);
assert.strictEqual(canonicalBeforeExplain.confidence, 0.94);
assert.strictEqual(canonicalBeforeExplain.sentiment, 'positive');

// Simulated token-level perturbation / explanation returns different heuristic inference
const externalInferenceTokens = [
  { token: 'Record', impact: 0.18, direction: 'positive', method: 'perturbation-delta' },
  { token: 'Accelerates', impact: 0.14, direction: 'positive', method: 'perturbation-delta' }
];

// Merge explanation into canonical result
const explainedResult = mergeExplanationTokens(
  canonicalBeforeExplain,
  externalInferenceTokens,
  'Perturbation word salience applied.',
  false
);

// Verify canonical prediction is 100% UNTOUCHED
assert.strictEqual(explainedResult.sentiment, 'positive', 'Sentiment class must NOT change');
assert.strictEqual(explainedResult.confidence, 0.94, 'Confidence score must NOT change to 0.96');
assert.strictEqual(badgeDisplay(explainedResult.confidence), '94%', 'Badge must remain 94%');
assert.strictEqual(modalProbabilityDisplay(explainedResult.scores.positive), '94.0%', 'Bullish probability must remain 94.0%');
assert.strictEqual(explainedResult.tokens.length, 2, 'Tokens must be populated');
assert.strictEqual(explainedResult.tokens[0].token, 'Record');
console.log('✓ PASS: Explanation calculations enriched tokens while preserving canonical BULLISH 94% confidence');

// -------------------------------------------------------------
// TEST CASE 8: Rounding rule verification (e.g., 93.6% rounds to 94%)
// -------------------------------------------------------------
console.log('\n[TEST 8] Precise rounding rule verification (e.g., 93.6% -> 94%)');
const testFloatArticle = {
  id: 'art-float-test',
  title: 'Float Test Article',
  sentiment: 'positive',
  confidence: 0.936,
  scores: { positive: 0.936, neutral: 0.044, negative: 0.020 }
};
const floatResult = getCanonicalSentimentResult(testFloatArticle);
assert.strictEqual(badgeDisplay(testFloatArticle.confidence), '94%');
assert.strictEqual(badgeDisplay(floatResult.confidence), '94%');
assert.strictEqual(modalProbabilityDisplay(floatResult.scores.positive), '93.6%');
console.log('✓ PASS: Both card and modal badge round 0.936 to 94% without truncation error');

console.log('\nALL 8 SENTIMENT CONSISTENCY REGRESSION TESTS PASSED SUCCESSFULLY!\n');
