from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.domain.models import Message, Usage


@dataclass(frozen=True)
class ProviderResult:
    text: str
    usage: Usage
    finish_reason: str | None = None


class ProviderAdapter(ABC):
    @abstractmethod
    def generate(self, messages: list[Message], max_output_tokens: int) -> ProviderResult:
        raise NotImplementedError
