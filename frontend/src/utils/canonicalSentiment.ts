import type { Article, SentimentAnalysisResult, SentimentScores, AttributionToken } from '../types';

/**
 * Normalizes sentiment string into one of the canonical 3 classes: 'positive' | 'negative' | 'neutral'.
 */
export function normalizeSentimentClass(sentiment?: string): 'positive' | 'negative' | 'neutral' {
  const norm = (sentiment || 'neutral').toLowerCase().trim();
  if (norm === 'positive' || norm === 'bullish') return 'positive';
  if (norm === 'negative' || norm === 'bearish') return 'negative';
  return 'neutral';
}

/**
 * Normalizes a confidence probability to a bounded float [0.0, 1.0].
 */
export function normalizeConfidenceScore(confidence?: number): number {
  if (typeof confidence === 'number' && !isNaN(confidence)) {
    return Math.max(0.0, Math.min(1.0, confidence));
  }
  return 0.70;
}

/**
 * Builds canonical class probability scores where the predicted class probability
 * exactly matches the article confidence score, and all three probabilities sum to 1.000.
 */
export function buildCanonicalScores(
  sentiment: 'positive' | 'negative' | 'neutral',
  confidence: number,
  existingScores?: SentimentScores
): SentimentScores {
  // If valid existing scores exist, align the winning class to confidence
  if (
    existingScores &&
    typeof existingScores.positive === 'number' &&
    typeof existingScores.neutral === 'number' &&
    typeof existingScores.negative === 'number'
  ) {
    const rawPos = Number(existingScores.positive);
    const rawNeu = Number(existingScores.neutral);
    const rawNeg = Number(existingScores.negative);

    if (sentiment === 'positive') {
      const otherTotal = rawNeu + rawNeg || 1.0;
      const rem = Math.max(0.0, 1.0 - confidence);
      const neu = Number(((rawNeu / otherTotal) * rem).toFixed(3));
      const neg = Number((rem - neu).toFixed(3));
      return { positive: confidence, neutral: neu, negative: Math.max(0.0, neg) };
    } else if (sentiment === 'negative') {
      const otherTotal = rawPos + rawNeu || 1.0;
      const rem = Math.max(0.0, 1.0 - confidence);
      const pos = Number(((rawPos / otherTotal) * rem).toFixed(3));
      const neu = Number((rem - pos).toFixed(3));
      return { positive: Math.max(0.0, pos), neutral: neu, negative: confidence };
    } else {
      const otherTotal = rawPos + rawNeg || 1.0;
      const rem = Math.max(0.0, 1.0 - confidence);
      const pos = Number(((rawPos / otherTotal) * rem).toFixed(3));
      const neg = Number((rem - pos).toFixed(3));
      return { positive: Math.max(0.0, pos), neutral: confidence, negative: Math.max(0.0, neg) };
    }
  }

  // If no existing scores, calibrate distribution symmetrically from remainder
  const remainder = Math.max(0.0, 1.0 - confidence);
  if (sentiment === 'positive') {
    const neu = Number((remainder * 0.7).toFixed(3));
    const neg = Number((remainder - neu).toFixed(3));
    return { positive: confidence, neutral: neu, negative: Math.max(0.0, neg) };
  } else if (sentiment === 'negative') {
    const neu = Number((remainder * 0.7).toFixed(3));
    const pos = Number((remainder - neu).toFixed(3));
    return { positive: Math.max(0.0, pos), neutral: neu, negative: confidence };
  } else {
    const half = Number((remainder / 2).toFixed(3));
    const otherHalf = Number((remainder - half).toFixed(3));
    return { positive: half, neutral: confidence, negative: otherHalf };
  }
}

/**
 * Builds the canonical FinBERT inference result from a given article.
 * Guarantees that the news card and explanation modal consume the exact same
 * inference result, identical confidence score, identical rounding rule, and
 * consistent class probability distribution.
 */
export function getCanonicalSentimentResult(article: Article): SentimentAnalysisResult {
  const sentiment = normalizeSentimentClass(article.sentiment);
  const confidence = normalizeConfidenceScore(article.confidence);
  const scores = buildCanonicalScores(sentiment, confidence, article.scores);

  const model_name =
    article.model_name ||
    (article.is_demo
      ? 'ProsusAI/finbert (Curated Intelligence)'
      : article.is_fallback
      ? 'ProsusAI/finbert (Institutional Fallback)'
      : 'ProsusAI/finbert');

  return {
    article_id: article.id,
    text: article.title,
    sentiment,
    confidence,
    scores,
    model_name,
    analyzed_at: article.published_at || new Date().toISOString(),
    tokens: article.tokens ? [...article.tokens] : [],
    explanation_note:
      article.explanation_note ||
      (article.is_demo
        ? 'Verified institutional sentiment classification from curated corpus.'
        : article.is_fallback
        ? 'Rule-based financial lexicon classification.'
        : 'FinBERT neural sentiment classification.'),
    is_fallback: Boolean(article.is_fallback),
    engine_mode: article.engine_mode || (article.is_demo ? 'curated-demo' : undefined),
  };
}

/**
 * Merges newly computed explanation tokens into an existing canonical result.
 * CRITICAL RULE: This strictly preserves the article's canonical prediction,
 * sentiment class, confidence, scores, and identifier, ensuring explanation
 * calculations never overwrite or drift the article's saved sentiment result.
 */
export function mergeExplanationTokens(
  canonical: SentimentAnalysisResult,
  tokens?: AttributionToken[],
  explanationNote?: string,
  isFallback?: boolean
): SentimentAnalysisResult {
  return {
    ...canonical,
    tokens: tokens && tokens.length > 0 ? tokens : canonical.tokens,
    explanation_note: explanationNote || canonical.explanation_note,
    // Only upgrade is_fallback indicator if explanation method used fallback dictionary
    is_fallback: isFallback !== undefined ? isFallback : canonical.is_fallback,
  };
}
