class HubError(Exception):
    code = "INTERNAL_ERROR"
    http_status = 500
    retryable = False
    def __init__(self, message: str = "Request failed"):
        super().__init__(message)
        self.public_message = message

class InvalidRequestError(HubError):
    code = "INVALID_REQUEST"; http_status = 400

class UnauthorizedError(HubError):
    code = "UNAUTHORIZED"; http_status = 401

class ClientDisabledError(HubError):
    code = "CLIENT_DISABLED"; http_status = 403

class IdentityMismatchError(HubError):
    code = "IDENTITY_MISMATCH"; http_status = 403

class RateLimitedError(HubError):
    code = "RATE_LIMITED"; http_status = 429; retryable = True

class QuotaExceededError(HubError):
    code = "QUOTA_EXCEEDED"; http_status = 429

class MonthlyTokenQuotaExceededError(HubError):
    code = "MONTHLY_TOKEN_QUOTA_EXCEEDED"; http_status = 429

class AuthenticationConfigurationError(HubError):
    code = "AUTH_NOT_CONFIGURED"; http_status = 503

class EntitlementConfigurationError(HubError):
    code = "ENTITLEMENT_NOT_CONFIGURED"; http_status = 503

class ProductAIDisabledError(HubError):
    code = "PRODUCT_AI_DISABLED"; http_status = 403

class AIEntitlementDisabledError(HubError):
    code = "AI_ENTITLEMENT_DISABLED"; http_status = 403

class AIEntitlementExpiredError(HubError):
    code = "AI_ENTITLEMENT_EXPIRED"; http_status = 403

class ProfileNotAllowedError(HubError):
    code = "PROFILE_NOT_ALLOWED"; http_status = 403

class ProviderConfigurationError(HubError):
    code = "PROVIDER_NOT_CONFIGURED"; http_status = 503

class ProviderTimeoutError(HubError):
    code = "PROVIDER_TIMEOUT"; http_status = 504; retryable = True

class ProviderRateLimitedError(HubError):
    code = "PROVIDER_RATE_LIMITED"; http_status = 503; retryable = True

class ProviderUnavailableError(HubError):
    code = "PROVIDER_UNAVAILABLE"; http_status = 503; retryable = True
