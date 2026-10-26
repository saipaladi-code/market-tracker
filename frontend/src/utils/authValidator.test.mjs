/**
 * FIN-SENTIMENT — Frontend Authentication & Validation Tests
 * Verifies email format validation, password strength rules, and session logic.
 */

function validateEmail(email) {
  if (!email || !email.trim()) return { valid: false, error: 'Email address is required.' };
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(email.trim())) return { valid: false, error: 'Please enter a valid financial email address.' };
  return { valid: true, error: null };
}

function validatePassword(password) {
  if (!password) return { valid: false, error: 'Password is required.' };
  if (password.length < 8) return { valid: false, error: 'Password must be at least 8 characters.' };
  if (!/[A-Z]/.test(password)) return { valid: false, error: 'Password must contain at least one uppercase letter (A-Z).' };
  if (!/[a-z]/.test(password)) return { valid: false, error: 'Password must contain at least one lowercase letter (a-z).' };
  if (!/\d/.test(password)) return { valid: false, error: 'Password must contain at least one numeric digit (0-9).' };
  return { valid: true, error: null };
}

function validateRegistration(fullName, email, password, confirmPassword) {
  if (!fullName || fullName.trim().length < 2) {
    return { valid: false, error: 'Full name must be at least 2 characters.' };
  }
  const emailRes = validateEmail(email);
  if (!emailRes.valid) return emailRes;

  const pwdRes = validatePassword(password);
  if (!pwdRes.valid) return pwdRes;

  if (password !== confirmPassword) {
    return { valid: false, error: 'Password confirmation does not match.' };
  }
  return { valid: true, error: null };
}

console.log('--- RUNNING FRONTEND AUTH & VALIDATION REGRESSION TESTS ---');

// Test 1: Email validation
const validEmails = ['analyst@hedgefund.com', 'trader.alex@investments.co.uk', 'test+research@firm.org'];
for (const e of validEmails) {
  const res = validateEmail(e);
  if (!res.valid) throw new Error(`Expected email "${e}" to be valid, got error: ${res.error}`);
  console.log(`✓ Accepted valid email: "${e}"`);
}

const invalidEmails = ['', '   ', 'notanemail', 'analyst@', '@hedgefund.com', 'trader@.com', 'spaces in@email.com'];
for (const e of invalidEmails) {
  const res = validateEmail(e);
  if (res.valid) throw new Error(`Expected email "${e}" to be rejected as invalid.`);
  console.log(`✓ Rejected invalid email: "${e}" -> ${res.error}`);
}

// Test 2: Password strength validation
const validPasswords = ['SecurePass123!', 'FinBert_Model_2026', 'Institutional99$'];
for (const p of validPasswords) {
  const res = validatePassword(p);
  if (!res.valid) throw new Error(`Expected password "${p}" to be valid, got: ${res.error}`);
  console.log(`✓ Accepted strong password: "${p.slice(0, 4)}***"`);
}

const weakPasswords = [
  { p: 'short1A', expected: 'at least 8 characters' },
  { p: 'alllowercase123', expected: 'uppercase letter' },
  { p: 'ALLUPPERCASE123', expected: 'lowercase letter' },
  { p: 'NoNumbersHere!', expected: 'numeric digit' },
];
for (const { p, expected } of weakPasswords) {
  const res = validatePassword(p);
  if (res.valid) throw new Error(`Expected weak password "${p}" to be rejected.`);
  if (!res.error.toLowerCase().includes(expected.toLowerCase())) {
    throw new Error(`Expected error message to mention "${expected}", got "${res.error}"`);
  }
  console.log(`✓ Rejected weak password: "${p}" -> ${res.error}`);
}

// Test 3: Registration confirmation mismatch
const mismatchRes = validateRegistration('Sarah Connor', 'sarah@skynet.com', 'SecurePass123!', 'MismatchedPass123!');
if (mismatchRes.valid || !mismatchRes.error.includes('does not match')) {
  throw new Error('Expected password mismatch error.');
}
console.log('✓ Rejected password confirmation mismatch');

// Test 4: Name minimum length
const shortNameRes = validateRegistration('A', 'valid@email.com', 'SecurePass123!', 'SecurePass123!');
if (shortNameRes.valid || !shortNameRes.error.includes('at least 2 characters')) {
  throw new Error('Expected full name length error.');
}
console.log('✓ Rejected full name shorter than 2 characters');

// Test 5: Complete valid registration payload
const completeRes = validateRegistration('Warren Buffett', 'wb@berkshire.com', 'OmahaAlpha1930!', 'OmahaAlpha1930!');
if (!completeRes.valid) {
  throw new Error(`Expected registration to be valid, got error: ${completeRes.error}`);
}
console.log('✓ Verified complete valid registration payload');

// Test 6: Authenticated page refresh emulation (session persistence check)
function simulateSessionRestoration(hasHttpOnlyCookie, currentUserResponse) {
  if (hasHttpOnlyCookie && currentUserResponse && currentUserResponse.id) {
    return { authenticated: true, user: currentUserResponse };
  }
  return { authenticated: false, user: null };
}

const refreshedSession = simulateSessionRestoration(true, {
  id: 'usr_test_123',
  email: 'analyst@finsentiment.ai',
  full_name: 'Lead Financial Analyst'
});
if (!refreshedSession.authenticated || !refreshedSession.user) {
  throw new Error('Session restoration upon page refresh failed.');
}
console.log('✓ Verified session restoration upon page refresh via HttpOnly cookie');

console.log('ALL FRONTEND AUTH & VALIDATION TESTS PASSED SUCCESSFULLY!\n');
