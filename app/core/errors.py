class HubError(Exception):
    code = "INTERNAL_ERROR"
    http_status = 500
    retryable = False

    def __init__(self, message: str = "Request failed"):
        super().__init__(message)
        self.public_message = message


class InvalidRequestError(HubError):
    code = "INVALID_REQUEST"
    http_status = 400


class UnauthorizedError(HubError):
    code = "UNAUTHORIZED"
    http_status = 401


class ClientDisabledError(HubError):
    code = "CLIENT_DISABLED"
    http_status = 403


class IdentityMismatchError(HubError):
    code = "IDENTITY_MISMATCH"
    http_status = 403


class RateLimitedError(HubError):
    code = "RATE_LIMITED"
    http_status = 429
    retryable = True


class QuotaExceededError(HubError):
    code = "QUOTA_EXCEEDED"
    http_status = 429
    retryable = False


class AuthenticationConfigurationError(HubError):
    code = "AUTH_NOT_CONFIGURED"
    http_status = 503


class ProviderConfigurationError(HubError):
    code = "PROVIDER_NOT_CONFIGURED"
    http_status = 503


class ProviderTimeoutError(HubError):
    code = "PROVIDER_TIMEOUT"
    http_status = 504
    retryable = True


class ProviderRateLimitedError(HubError):
    code = "PROVIDER_RATE_LIMITED"
    http_status = 503
    retryable = True


class ProviderUnavailableError(HubError):
    code = "PROVIDER_UNAVAILABLE"
    http_status = 503
    retryable = True
