from dataclasses import dataclass, field


_ALLOWED_ROLES = {"system", "user", "assistant"}


@dataclass(frozen=True)
class Message:
    role: str
    content: str

    def __post_init__(self):
        if self.role not in _ALLOWED_ROLES:
            raise ValueError("invalid role")
        if not isinstance(self.content, str) or not (1 <= len(self.content) <= 20000):
            raise ValueError("invalid content")

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}


@dataclass(frozen=True)
class GenerateOptions:
    max_output_tokens: int = 800

    def __post_init__(self):
        if not isinstance(self.max_output_tokens, int) or not (1 <= self.max_output_tokens <= 4000):
            raise ValueError("invalid max_output_tokens")


@dataclass(frozen=True)
class GenerateRequest:
    profile: str
    messages: list[Message]
    options: GenerateOptions = field(default_factory=GenerateOptions)

    @classmethod
    def from_dict(cls, data: dict):
        if not isinstance(data, dict):
            raise ValueError("request must be an object")
        profile = data.get("profile", "standard")
        if not isinstance(profile, str) or not (1 <= len(profile) <= 50):
            raise ValueError("invalid profile")
        raw_messages = data.get("messages")
        if not isinstance(raw_messages, list) or not (1 <= len(raw_messages) <= 50):
            raise ValueError("invalid messages")
        messages = [Message(role=m.get("role"), content=m.get("content")) for m in raw_messages if isinstance(m, dict)]
        if len(messages) != len(raw_messages):
            raise ValueError("invalid message")
        raw_options = data.get("options") or {}
        if not isinstance(raw_options, dict):
            raise ValueError("invalid options")
        options = GenerateOptions(max_output_tokens=raw_options.get("max_output_tokens", 800))
        return cls(profile=profile, messages=messages, options=options)


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    def to_dict(self) -> dict:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
        }
