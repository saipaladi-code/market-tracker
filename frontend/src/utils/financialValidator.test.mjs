import {
  validateFinancialHeadlineClient,
  MAX_HEADLINE_LENGTH,
  MIN_HEADLINE_LENGTH,
  INVALID_HEADLINE_MESSAGE
} from './financialValidator.ts';
import assert from 'node:assert';

console.log('--- RUNNING FRONTEND FINANCIAL VALIDATOR TESTS ---');

// 1. Rejection tests
const rejectionCases = [
  'hi',
  'hello',
  'how are you',
  'what is your name',
  'I love pizza',
  'good morning',
  'tell me a joke',
  '12345',
  '',
  '   ',
  '?!?!?!!',
  '!@#$%^&*()',
  'asdfghjk qwerty zxcvbnm',
  'What is the capital of France?',
  'The weather is lovely outside today.',
];

for (const text of rejectionCases) {
  const res = validateFinancialHeadlineClient(text);
  assert.strictEqual(res.isValid, false, `Expected rejection for: "${text}"`);
  assert(res.errorCode, `Expected errorCode for: "${text}"`);
  console.log(`✓ Rejected "${text.slice(0, 25)}" -> ${res.errorCode}`);
}

// 2. Acceptance tests
const acceptanceCases = [
  'Apple reports record quarterly revenue, beating analyst expectations.',
  'Tesla shares fall after quarterly profits decline.',
  'Microsoft announces stronger-than-expected cloud revenue growth.',
  'Microsoft announces a new earnings forecast.',
  'NVIDIA stock rises following positive earnings guidance.',
  'Reliance Industries reports higher operating revenue.',
  'The central bank keeps interest rates unchanged.',
  'A company announces layoffs amid declining sales.',
  'Amazon faces regulatory scrutiny over its business practices.',
  'A previously unknown company announces a major quarterly loss.',
  'A business reports mixed earnings results and lowers its annual forecast.',
  'Tata Motors reports rising commercial vehicle sales across European markets.',
  'Bavarian Nordic announces surging quarterly operating profit.'
];

for (const text of acceptanceCases) {
  const res = validateFinancialHeadlineClient(text);
  assert.strictEqual(res.isValid, true, `Expected acceptance for: "${text}"`);
  console.log(`✓ Accepted: "${text.slice(0, 45)}..."`);
}

// 3. Boundary tests
// Min length boundary
const short14 = 'Fed rate cut 1'; // Exactly 14 chars with financial signals
const resShort14 = validateFinancialHeadlineClient(short14);
assert.strictEqual(resShort14.isValid, false);
assert.strictEqual(resShort14.errorCode, 'HEADLINE_TOO_SHORT');
console.log('✓ Boundary 14 chars correctly rejected as HEADLINE_TOO_SHORT');

const valid15 = 'Fed rate cut 10'; // Exactly 15 chars with financial signals
const resValid15 = validateFinancialHeadlineClient(valid15);
assert.strictEqual(resValid15.isValid, true);
console.log('✓ Boundary 15 chars correctly accepted');

// Max length boundary: exactly 1000 chars
const base = 'Apple reports record quarterly revenue and rising operating margin. ';
const text1000 = base.repeat(20).slice(0, 1000);
assert.strictEqual(text1000.length, 1000);
const res1000 = validateFinancialHeadlineClient(text1000);
assert.strictEqual(res1000.isValid, true);
console.log('✓ Boundary 1,000 chars correctly accepted');

// 1001 chars
const text1001 = text1000 + '!';
assert.strictEqual(text1001.length, 1001);
const res1001 = validateFinancialHeadlineClient(text1001);
assert.strictEqual(res1001.isValid, false);
assert.strictEqual(res1001.errorCode, 'HEADLINE_TOO_LONG');
console.log('✓ Boundary 1,001 chars correctly rejected as HEADLINE_TOO_LONG');

console.log('ALL FRONTEND VALIDATION TESTS PASSED SUCCESSFULLY!');
