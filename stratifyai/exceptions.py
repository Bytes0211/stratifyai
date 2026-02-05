"""Custom exceptions for LLM abstraction layer."""


class LLMAbstractionError(Exception):
    """Base exception for all LLM abstraction errors."""
    pass


class ProviderError(LLMAbstractionError):
    """Base exception for provider-specific errors."""
    pass


class InvalidProviderError(ProviderError):
    """Raised when an invalid provider is specified."""
    pass


class ProviderAPIError(ProviderError):
    """Raised when a provider API call fails."""
    
    def __init__(self, message: str, provider: str, status_code: int = None):
        self.provider = provider
        self.status_code = status_code
        super().__init__(f"[{provider}] {message}")


class AuthenticationError(ProviderError):
    """Raised when API key authentication fails."""
    
    def __init__(self, provider: str):
        self.provider = provider
        super().__init__(f"Authentication failed for {provider}. Check API key.")


class InsufficientBalanceError(ProviderError):
    """Raised when provider account has insufficient balance."""
    
    def __init__(self, provider: str):
        self.provider = provider
        super().__init__(f"Insufficient balance in {provider} account. Please add credits.")


class RateLimitError(ProviderError):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, provider: str, retry_after: int = None):
        self.provider = provider
        self.retry_after = retry_after
        message = f"Rate limit exceeded for {provider}"
        if retry_after:
            message += f". Retry after {retry_after} seconds"
        super().__init__(message)


class InvalidModelError(ProviderError):
    """Raised when an invalid model is specified for a provider."""
    
    def __init__(self, model: str, provider: str):
        self.model = model
        self.provider = provider
        super().__init__(f"Model '{model}' not supported by {provider}")


class BudgetExceededError(LLMAbstractionError):
    """Raised when budget limit is exceeded."""
    
    def __init__(self, current_cost: float, budget_limit: float):
        self.current_cost = current_cost
        self.budget_limit = budget_limit
        super().__init__(
            f"Budget limit ${budget_limit:.2f} exceeded. "
            f"Current spend: ${current_cost:.2f}"
        )


class MaxRetriesExceededError(LLMAbstractionError):
    """Raised when maximum retry attempts are exceeded."""
    
    def __init__(self, attempts: int, last_error: Exception):
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(
            f"Maximum retry attempts ({attempts}) exceeded. "
            f"Last error: {str(last_error)}"
        )


class ValidationError(LLMAbstractionError):
    """Raised when input validation fails."""
    pass
