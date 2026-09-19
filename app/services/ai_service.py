from app.domain.models import GenerateRequest
from app.providers.base import ProviderResult
from app.providers.router import ProviderRouter


class AIService:
    def __init__(self, router: ProviderRouter):
        self.router = router

    def generate(self, request: GenerateRequest) -> ProviderResult:
        provider = self.router.for_profile(request.profile)
        return provider.generate(request.messages, request.options.max_output_tokens)
