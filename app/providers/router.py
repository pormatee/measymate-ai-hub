from app.core.config import Settings
from app.core.errors import InvalidRequestError
from app.providers.base import ProviderAdapter
from app.providers.deepseek import DeepSeekAdapter


class ProviderRouter:
    def __init__(self, settings: Settings):
        self.settings = settings

    def for_profile(self, profile: str) -> ProviderAdapter:
        if profile != "standard":
            raise InvalidRequestError("Unsupported AI profile.")

        return DeepSeekAdapter(
            api_key=self.settings.deepseek_api_key,
            base_url=self.settings.deepseek_base_url,
            model=self.settings.deepseek_model,
            timeout_seconds=self.settings.provider_timeout_seconds,
        )
