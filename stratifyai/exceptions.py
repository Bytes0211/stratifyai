"""Custom exceptions for LLM abstraction layer."""


class LLMAbstractionError(Exception):
    """Base exception for all LLM abstraction errors."""

    default_error_code = "LLM_ABSTRACTION_ERROR"

    def __init__(self, message: str, error_code: str | None = None):
        self.error_code = error_code or self.default_error_code
        super().__init__(message)

    def to_dict(self) -> dict[str, str]:
        """Return structured error details for programmatic handling."""
        return {
            "error_code": self.error_code,
            "message": str(self),
            "error_type": self.__class__.__name__,
        }


class ProviderError(LLMAbstractionError):
    """Base exception for provider-specific errors."""

    default_error_code = "PROVIDER_ERROR"


class InvalidProviderError(ProviderError):
    """Raised when an invalid provider is specified."""

    default_error_code = "INVALID_PROVIDER"


class ProviderAPIError(ProviderError):
    """Raised when a provider API call fails."""

    def __init__(self, message: str, provider: str, status_code: int | None = None):
        self.provider = provider
        self.status_code = status_code
        super().__init__(f"[{provider}] {message}", error_code="PROVIDER_API_ERROR")


class AuthenticationError(ProviderError):
    """Raised when API key authentication fails."""

    def __init__(self, provider: str, message: str | None = None):
        self.provider = provider
        super().__init__(
            message or f"Authentication failed for {provider}. Check API key.",
            error_code="AUTHENTICATION_FAILED",
        )


class InsufficientBalanceError(ProviderError):
    """Raised when provider account has insufficient balance."""

    def __init__(self, provider: str):
        self.provider = provider
        super().__init__(
            f"Insufficient balance in {provider} account. Please add credits.",
            error_code="INSUFFICIENT_BALANCE",
        )


class RateLimitError(ProviderError):
    """Raised when rate limit is exceeded."""

    def __init__(self, provider: str, retry_after: int | None = None):
        self.provider = provider
        self.retry_after = retry_after
        message = f"Rate limit exceeded for {provider}"
        if retry_after:
            message += f". Retry after {retry_after} seconds"
        super().__init__(message, error_code="RATE_LIMIT_EXCEEDED")


class InvalidModelError(ProviderError):
    """Raised when an invalid model is specified for a provider."""

    def __init__(self, model: str, provider: str):
        self.model = model
        self.provider = provider
        super().__init__(
            f"Model '{model}' not supported by {provider}",
            error_code="INVALID_MODEL",
        )


class BudgetExceededError(LLMAbstractionError):
    """Raised when budget limit is exceeded."""

    default_error_code = "BUDGET_EXCEEDED"

    def __init__(self, current_cost: float, budget_limit: float):
        self.current_cost = current_cost
        self.budget_limit = budget_limit
        super().__init__(
            f"Budget limit ${budget_limit:.2f} exceeded. "
            f"Current spend: ${current_cost:.2f}",
            error_code="BUDGET_EXCEEDED",
        )


class MaxRetriesExceededError(LLMAbstractionError):
    """Raised when maximum retry attempts are exceeded."""

    default_error_code = "MAX_RETRIES_EXCEEDED"

    def __init__(self, attempts: int, last_error: Exception):
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(
            f"Maximum retry attempts ({attempts}) exceeded. "
            f"Last error: {str(last_error)}",
            error_code="MAX_RETRIES_EXCEEDED",
        )


class ValidationError(LLMAbstractionError):
    """Raised when input validation fails."""

    default_error_code = "VALIDATION_ERROR"
