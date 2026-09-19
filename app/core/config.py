import os
from dataclasses import dataclass, field
from pathlib import Path

def load_local_env(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ.setdefault(key, value)

load_local_env()

@dataclass(frozen=True)
class Settings:
    deepseek_api_key: str | None = field(default_factory=lambda: os.getenv("DEEPSEEK_API_KEY") or None)
    deepseek_base_url: str = field(default_factory=lambda: os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/"))
    deepseek_model: str = field(default_factory=lambda: os.getenv("DEEPSEEK_MODEL", "deepseek-chat"))
    provider_timeout_seconds: float = field(default_factory=lambda: float(os.getenv("AI_HUB_PROVIDER_TIMEOUT_SECONDS", "30")))
    clients_json: str = field(default_factory=lambda: os.getenv("AI_HUB_CLIENTS_JSON", "[]"))
    products_json: str = field(default_factory=lambda: os.getenv("AI_HUB_PRODUCTS_JSON", "[]"))
    entitlements_json: str = field(default_factory=lambda: os.getenv("AI_HUB_ENTITLEMENTS_JSON", "[]"))
    cors_origins_json: str = field(default_factory=lambda: os.getenv("AI_HUB_CORS_ORIGINS_JSON", '["null"]'))

def get_settings() -> Settings:
    return Settings()
