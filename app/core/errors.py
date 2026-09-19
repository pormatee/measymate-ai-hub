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
