"""
Financial News Headline Validator Module.
Re-exports and aliases from app.services.headline_validator for backwards compatibility.
"""
from app.services.headline_validator import (
    validate_financial_headline,
    assert_valid_financial_headline,
    HeadlineValidationError,
    INVALID_FINANCIAL_HEADLINE_MESSAGE,
    ERROR_INVALID_FINANCIAL_HEADLINE,
    ERROR_HEADLINE_TOO_SHORT,
    ERROR_HEADLINE_TOO_LONG,
    ERROR_HEADLINE_EMPTY,
    MIN_HEADLINE_LENGTH,
    MAX_HEADLINE_LENGTH
)

# Compatibility aliases
FinancialValidationError = HeadlineValidationError
INVALID_HEADLINE_MESSAGE = INVALID_FINANCIAL_HEADLINE_MESSAGE

__all__ = [
    "validate_financial_headline",
    "assert_valid_financial_headline",
    "HeadlineValidationError",
    "FinancialValidationError",
    "INVALID_FINANCIAL_HEADLINE_MESSAGE",
    "INVALID_HEADLINE_MESSAGE",
    "ERROR_INVALID_FINANCIAL_HEADLINE",
    "ERROR_HEADLINE_TOO_SHORT",
    "ERROR_HEADLINE_TOO_LONG",
    "ERROR_HEADLINE_EMPTY",
    "MIN_HEADLINE_LENGTH",
    "MAX_HEADLINE_LENGTH"
]
