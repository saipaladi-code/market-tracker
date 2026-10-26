/**
 * Compatibility wrapper for financial headline validation.
 * Re-exports from services/headlineValidator.
 */
import {
  validateFinancialHeadline as validateHeadline,
  MIN_HEADLINE_LENGTH,
  MAX_HEADLINE_LENGTH,
  INVALID_FINANCIAL_HEADLINE_MESSAGE
} from '../services/headlineValidator.ts';
import type { HeadlineValidationResult } from '../services/headlineValidator.ts';

export {
  MIN_HEADLINE_LENGTH,
  MAX_HEADLINE_LENGTH,
  INVALID_FINANCIAL_HEADLINE_MESSAGE as INVALID_HEADLINE_MESSAGE
};

export interface ClientValidationResult {
  isValid: boolean;
  errorCode: string | null;
  errorMessage: string | null;
  length: number;
}

export function validateFinancialHeadlineClient(text: string): ClientValidationResult {
  const res: HeadlineValidationResult = validateHeadline(text);
  return {
    isValid: res.isValid,
    errorCode: res.errorCode,
    errorMessage: res.message,
    length: res.charCount
  };
}

export const validateFinancialHeadline = validateHeadline;
