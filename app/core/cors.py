import json

from app.core.errors import EntitlementConfigurationError


def parse_cors_origins(raw: str) -> tuple[str, ...]:
    try:
        data = json.loads(raw or "[]")
    except json.JSONDecodeError as exc:
        raise EntitlementConfigurationError("CORS origin policy is not configured.") from exc
    if not isinstance(data, list):
        raise EntitlementConfigurationError("CORS origin policy is not configured.")
    out = []
    for item in data:
        if not isinstance(item, str) or not item.strip():
            raise EntitlementConfigurationError("CORS origin policy is not configured.")
        origin = item.strip()
        if origin not in out:
            out.append(origin)
    return tuple(out)


def allowed_cors_origin(origin: str | None, allowed: tuple[str, ...]) -> str | None:
    if not origin:
        return None
    if origin in allowed:
        return origin
    return None
