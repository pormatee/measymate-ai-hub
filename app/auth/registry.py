import hashlib
import hmac
import json

from app.auth.models import ClientContext, ClientPolicy
from app.core.errors import AuthenticationConfigurationError, ClientDisabledError, UnauthorizedError


class ClientRegistry:
    def __init__(self, policies: list[ClientPolicy]):
        self.policies = policies

    @classmethod
    def from_json(cls, raw: str):
        try:
            data = json.loads(raw or "[]")
        except json.JSONDecodeError as exc:
            raise AuthenticationConfigurationError("Client authentication is not configured.") from exc

        if not isinstance(data, list):
            raise AuthenticationConfigurationError("Client authentication is not configured.")

        policies = []
        seen_hashes = set()
        for item in data:
            try:
                if not isinstance(item, dict):
                    raise ValueError
                policy = ClientPolicy(
                    client_id=str(item["client_id"]),
                    product_id=str(item["product_id"]),
                    token_sha256=str(item["token_sha256"]).lower(),
                    enabled=bool(item.get("enabled", True)),
                    requests_per_minute=int(item.get("requests_per_minute", 30)),
                    daily_request_quota=int(item.get("daily_request_quota", 1000)),
                )
                if not policy.client_id or not policy.product_id:
                    raise ValueError
                if len(policy.token_sha256) != 64 or any(c not in "0123456789abcdef" for c in policy.token_sha256):
                    raise ValueError
                if policy.requests_per_minute < 1 or policy.daily_request_quota < 1:
                    raise ValueError
                if policy.token_sha256 in seen_hashes:
                    raise ValueError
                seen_hashes.add(policy.token_sha256)
                policies.append(policy)
            except (KeyError, TypeError, ValueError) as exc:
                raise AuthenticationConfigurationError("Client authentication is not configured.") from exc
        return cls(policies)

    def authenticate(self, authorization_header: str | None) -> ClientContext:
        if not self.policies:
            raise AuthenticationConfigurationError("Client authentication is not configured.")

        if not authorization_header or not authorization_header.startswith("Bearer "):
            raise UnauthorizedError("Authentication required.")

        token = authorization_header[7:].strip()
        if not token:
            raise UnauthorizedError("Authentication required.")

        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        matched = None
        for policy in self.policies:
            if hmac.compare_digest(digest, policy.token_sha256):
                matched = policy
                break

        if matched is None:
            raise UnauthorizedError("Invalid access token.")
        if not matched.enabled:
            raise ClientDisabledError("Client is disabled.")

        return ClientContext(
            client_id=matched.client_id,
            product_id=matched.product_id,
            requests_per_minute=matched.requests_per_minute,
            daily_request_quota=matched.daily_request_quota,
        )
