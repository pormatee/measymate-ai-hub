from app.auth.registry import ClientRegistry
from app.core.config import Settings
from app.entitlements.registry import EntitlementRegistry, ProductRegistry
from app.entitlements.service import EntitlementService
from app.limits.guard import InMemoryUsageGuard
from app.providers.router import ProviderRouter
from app.services.ai_service import AIService

class HubRuntime:
    def __init__(self, *, registry: ClientRegistry, usage_guard: InMemoryUsageGuard,
                 ai_service: AIService, entitlement_service: EntitlementService):
        self.registry = registry
        self.usage_guard = usage_guard
        self.ai_service = ai_service
        self.entitlement_service = entitlement_service

    @classmethod
    def from_settings(cls, settings: Settings):
        products = ProductRegistry.from_json(settings.products_json)
        entitlements = EntitlementRegistry.from_json(settings.entitlements_json)
        return cls(
            registry=ClientRegistry.from_json(settings.clients_json),
            usage_guard=InMemoryUsageGuard(),
            ai_service=AIService(ProviderRouter(settings)),
            entitlement_service=EntitlementService(products, entitlements),
        )
