class AIException(Exception):
    """Base exception for all AI-related operations."""
    def __init__(self, message: str, code: str = "AI_ERROR", details: dict = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class AIProviderUnavailableException(AIException):
    """Raised when the configured AI provider or model endpoint cannot be reached."""
    def __init__(self, message: str = "AI provider service is unreachable or offline", details: dict = None):
        super().__init__(message, code="AI_PROVIDER_UNAVAILABLE", details=details)


class AIRequestTimeoutException(AIException):
    """Raised when an AI request exceeds the configured timeout threshold."""
    def __init__(self, message: str = "AI model inference request timed out", details: dict = None):
        super().__init__(message, code="AI_REQUEST_TIMEOUT", details=details)


class AIResponseInvalidException(AIException):
    """Raised when the AI provider returns an empty or unparseable response."""
    def __init__(self, message: str = "AI provider returned an invalid or malformed response", details: dict = None):
        super().__init__(message, code="AI_RESPONSE_INVALID", details=details)


class AIModelNotFoundException(AIException):
    """Raised when the requested model is not available on the provider."""
    def __init__(self, message: str = "Configured AI model was not found on provider", details: dict = None):
        super().__init__(message, code="AI_MODEL_NOT_FOUND", details=details)
