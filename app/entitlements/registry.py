import json
from app.core.errors import EntitlementConfigurationError
from app.entitlements.models import EntitlementPolicy, ProductPolicy

_ALLOWED_MODES = {"OFF", "AUTO", "ON"}

class ProductRegistry:
    def __init__(self, policies: list[ProductPolicy]):
        self._by_product = {p.product_id: p for p in policies}

    @classmethod
    def from_json(cls, raw: str):
        try:
            data = json.loads(raw or "[]")
        except json.JSONDecodeError as exc:
            raise EntitlementConfigurationError("Product AI policy is not configured.") from exc
        if not isinstance(data, list):
            raise EntitlementConfigurationError("Product AI policy is not configured.")
        policies = []
        seen = set()
        for item in data:
            try:
                if not isinstance(item, dict):
                    raise ValueError
                product_id = str(item["product_id"])
                ai_mode = str(item.get("ai_mode", "AUTO")).upper()
                raw_profiles = item.get("allowed_profiles", [])
                if not product_id or product_id in seen or ai_mode not in _ALLOWED_MODES:
                    raise ValueError
                if not isinstance(raw_profiles, list) or not raw_profiles:
                    raise ValueError
                profiles = tuple(str(x) for x in raw_profiles if isinstance(x, str) and x)
                if len(profiles) != len(raw_profiles):
                    raise ValueError
                seen.add(product_id)
                policies.append(ProductPolicy(
                    product_id=product_id,
                    ai_enabled=bool(item.get("ai_enabled", True)),
                    ai_mode=ai_mode,
                    allowed_profiles=profiles,
                ))
            except (KeyError, TypeError, ValueError) as exc:
                raise EntitlementConfigurationError("Product AI policy is not configured.") from exc
        return cls(policies)

    def get(self, product_id: str) -> ProductPolicy | None:
        return self._by_product.get(product_id)

class EntitlementRegistry:
    def __init__(self, policies: list[EntitlementPolicy]):
        self._by_key = {(p.license_id, p.product_id): p for p in policies}

    @classmethod
    def from_json(cls, raw: str):
        try:
            data = json.loads(raw or "[]")
        except json.JSONDecodeError as exc:
            raise EntitlementConfigurationError("AI entitlement is not configured.") from exc
        if not isinstance(data, list):
            raise EntitlementConfigurationError("AI entitlement is not configured.")
        policies = []
        seen = set()
        for item in data:
            try:
                if not isinstance(item, dict):
                    raise ValueError
                license_id = str(item["license_id"])
                product_id = str(item["product_id"])
                plan = str(item.get("plan", ""))
                expires_at = item.get("expires_at")
                if expires_at is not None:
                    expires_at = str(expires_at)
                monthly = int(item.get("monthly_token_quota", 0))
                key = (license_id, product_id)
                if not license_id or not product_id or not plan or key in seen or monthly < 1:
                    raise ValueError
                seen.add(key)
                policies.append(EntitlementPolicy(
                    license_id=license_id,
                    product_id=product_id,
                    plan=plan,
                    ai_enabled=bool(item.get("ai_enabled", True)),
                    expires_at=expires_at,
                    monthly_token_quota=monthly,
                ))
            except (KeyError, TypeError, ValueError) as exc:
                raise EntitlementConfigurationError("AI entitlement is not configured.") from exc
        return cls(policies)

    def get(self, license_id: str, product_id: str) -> EntitlementPolicy | None:
        return self._by_key.get((license_id, product_id))
