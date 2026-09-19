from datetime import datetime, timezone
from app.auth.models import ClientContext
from app.core.errors import (
    AIEntitlementDisabledError,
    AIEntitlementExpiredError,
    EntitlementConfigurationError,
    ProductAIDisabledError,
    ProfileNotAllowedError,
)
from app.entitlements.models import EntitlementDecision
from app.entitlements.registry import EntitlementRegistry, ProductRegistry

def _parse_expiry(value: str | None) -> datetime | None:
    if value is None or value == "":
        return None
    try:
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError as exc:
        raise EntitlementConfigurationError("AI entitlement is not configured.") from exc

class EntitlementService:
    def __init__(self, products: ProductRegistry, entitlements: EntitlementRegistry, now=None):
        self.products = products
        self.entitlements = entitlements
        self._now = now or (lambda: datetime.now(timezone.utc))

    def evaluate(self, client: ClientContext) -> EntitlementDecision:
        product = self.products.get(client.product_id)
        if product is None:
            raise EntitlementConfigurationError("Product AI policy is not configured.")
        entitlement = self.entitlements.get(client.license_id, client.product_id)
        if entitlement is None:
            return EntitlementDecision(False, "NO_AI_ENTITLEMENT", client.product_id, client.license_id, None, product.ai_mode, None, 0)
        if not product.ai_enabled or product.ai_mode == "OFF":
            return EntitlementDecision(False, "PRODUCT_AI_DISABLED", client.product_id, client.license_id, entitlement.plan, product.ai_mode, entitlement.expires_at, entitlement.monthly_token_quota)
        if not entitlement.ai_enabled:
            return EntitlementDecision(False, "AI_ENTITLEMENT_DISABLED", client.product_id, client.license_id, entitlement.plan, product.ai_mode, entitlement.expires_at, entitlement.monthly_token_quota)
        expires = _parse_expiry(entitlement.expires_at)
        if expires is not None and self._now() >= expires:
            return EntitlementDecision(False, "AI_ENTITLEMENT_EXPIRED", client.product_id, client.license_id, entitlement.plan, product.ai_mode, entitlement.expires_at, entitlement.monthly_token_quota)
        return EntitlementDecision(True, None, client.product_id, client.license_id, entitlement.plan, product.ai_mode, entitlement.expires_at, entitlement.monthly_token_quota)

    def require_access(self, client: ClientContext, profile: str | None = None) -> EntitlementDecision:
        decision = self.evaluate(client)
        if not decision.available:
            if decision.reason == "PRODUCT_AI_DISABLED":
                raise ProductAIDisabledError("AI is disabled for this product.")
            if decision.reason == "AI_ENTITLEMENT_DISABLED":
                raise AIEntitlementDisabledError("AI service is not enabled for this license.")
            if decision.reason == "AI_ENTITLEMENT_EXPIRED":
                raise AIEntitlementExpiredError("AI service has expired.")
            raise AIEntitlementDisabledError("AI service is not enabled for this license.")
        if profile is not None:
            product = self.products.get(client.product_id)
            if product is None or profile not in product.allowed_profiles:
                raise ProfileNotAllowedError("AI profile is not allowed for this product.")
        return decision
