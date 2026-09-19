import json
import socket
import urllib.error
import urllib.request

from app.core.errors import (
    ProviderConfigurationError,
    ProviderRateLimitedError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.domain.models import Message, Usage
from app.providers.base import ProviderAdapter, ProviderResult


class DeepSeekAdapter(ProviderAdapter):
    def __init__(self, *, api_key: str | None, base_url: str, model: str, timeout_seconds: float, opener=None):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self._opener = opener or urllib.request.urlopen

    def generate(self, messages: list[Message], max_output_tokens: int) -> ProviderResult:
        if not self.api_key:
            raise ProviderConfigurationError("AI provider is not configured.")

        payload = json.dumps({
            "model": self.model,
            "messages": [message.to_dict() for message in messages],
            "max_tokens": max_output_tokens,
            "stream": False,
        }).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=payload,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )

        try:
            with self._opener(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                raise ProviderRateLimitedError("AI provider is temporarily busy.") from exc
            raise ProviderUnavailableError("AI provider is unavailable.") from exc
        except (TimeoutError, socket.timeout) as exc:
            raise ProviderTimeoutError("AI provider timed out.") from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, (TimeoutError, socket.timeout)):
                raise ProviderTimeoutError("AI provider timed out.") from exc
            raise ProviderUnavailableError("AI provider is unavailable.") from exc

        try:
            data = json.loads(raw)
            choice = data["choices"][0]
            usage_raw = data.get("usage") or {}
            usage = Usage(
                input_tokens=int(usage_raw.get("prompt_tokens") or 0),
                output_tokens=int(usage_raw.get("completion_tokens") or 0),
                total_tokens=int(usage_raw.get("total_tokens") or 0),
            )
            return ProviderResult(
                text=choice["message"].get("content") or "",
                usage=usage,
                finish_reason=choice.get("finish_reason"),
            )
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ProviderUnavailableError("AI provider returned an invalid response.") from exc
