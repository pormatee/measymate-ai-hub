from dataclasses import dataclass


@dataclass(frozen=True)
class ClientPolicy:
    client_id: str
    product_id: str
    token_sha256: str
    enabled: bool
    requests_per_minute: int
    daily_request_quota: int


@dataclass(frozen=True)
class ClientContext:
    client_id: str
    product_id: str
    requests_per_minute: int
    daily_request_quota: int
