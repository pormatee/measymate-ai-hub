from dataclasses import dataclass

@dataclass(frozen=True)
class ProductPolicy:
    product_id: str
    ai_enabled: bool
    ai_mode: str
    allowed_profiles: tuple[str, ...]

@dataclass(frozen=True)
class EntitlementPolicy:
    license_id: str
    product_id: str
    plan: str
    ai_enabled: bool
    expires_at: str | None
    monthly_token_quota: int

@dataclass(frozen=True)
class EntitlementDecision:
    available: bool
    reason: str | None
    product_id: str
    license_id: str
    plan: str | None
    ai_mode: str
    expires_at: str | None
    monthly_token_quota: int
