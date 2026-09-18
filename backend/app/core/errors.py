class VyapaarError(Exception):
    code = "VYAPAAR_ERROR"
    status_code = 400

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class AuthenticationError(VyapaarError):
    code = "AUTHENTICATION_FAILED"
    status_code = 401


class AuthorizationError(VyapaarError):
    code = "NOT_AUTHORIZED"
    status_code = 403


class NotFoundError(VyapaarError):
    code = "NOT_FOUND"
    status_code = 404


class ConflictError(VyapaarError):
    code = "CONFLICT"
    status_code = 409


class DuplicateEventError(ConflictError):
    code = "DUPLICATE_EVENT"


class StaleApprovalError(ConflictError):
    code = "STALE_APPROVAL"


class InvalidSignatureError(AuthenticationError):
    code = "INVALID_SIGNATURE"


class ProviderError(VyapaarError):
    code = "PROVIDER_ERROR"
    status_code = 502


class ProviderAuthenticationError(ProviderError):
    code = "PROVIDER_AUTHENTICATION_FAILED"


class ProviderTimeoutError(ProviderError):
    code = "PROVIDER_TIMEOUT"
    status_code = 504


class RateLimitError(ProviderError):
    code = "RATE_LIMITED"
    status_code = 429


class SupplierUnavailableError(ProviderError):
    code = "SUPPLIER_UNAVAILABLE"


class AgentFailureError(VyapaarError):
    code = "AGENT_FAILURE"
    status_code = 500


class DatabaseError(VyapaarError):
    code = "DATABASE_FAILURE"
    status_code = 503


class RedisError(VyapaarError):
    code = "REDIS_FAILURE"
    status_code = 503
