from uuid import uuid4

from app.core.errors import HubError, IdentityMismatchError, InvalidRequestError
from app.core.runtime import HubRuntime
from app.domain.models import GenerateRequest

def _error_body(request_id: str, exc: HubError) -> tuple[int, dict]:
    return exc.http_status, {
        "request_id": request_id,
        "status": "error",
        "error": {"code": exc.code, "message": exc.public_message, "retryable": exc.retryable},
    }

def status_response(runtime: HubRuntime, authorization_header: str | None, request_id: str | None = None) -> tuple[int, dict]:
    request_id = request_id or f"req_{uuid4().hex}"
    try:
        client = runtime.registry.authenticate(authorization_header)
        decision = runtime.entitlement_service.evaluate(client)
        usage = runtime.usage_guard.monthly_usage(client, decision.monthly_token_quota) if decision.monthly_token_quota > 0 else {
            "month": None, "used_tokens": 0, "quota_tokens": 0, "remaining_tokens": 0
        }
        if usage["remaining_tokens"] <= 0 and decision.available:
            available = False
            reason = "MONTHLY_TOKEN_QUOTA_EXCEEDED"
        else:
            available = decision.available
            reason = decision.reason
        return 200, {
            "request_id": request_id,
            "status": "ok",
            "client_id": client.client_id,
            "license_id": client.license_id,
            "product_id": client.product_id,
            "ai": {
                "available": available,
                "reason": reason,
                "mode": decision.ai_mode,
                "plan": decision.plan,
                "expires_at": decision.expires_at,
                "usage": usage,
            },
        }
    except HubError as exc:
        return _error_body(request_id, exc)

def generate_response(runtime: HubRuntime, payload: dict, authorization_header: str | None,
                      request_id: str | None = None) -> tuple[int, dict]:
    request_id = request_id or f"req_{uuid4().hex}"
    try:
        client = runtime.registry.authenticate(authorization_header)
        if isinstance(payload, dict) and ("product_id" in payload or "client_id" in payload or "license_id" in payload):
            raise IdentityMismatchError("Client identity is determined by authentication.")
        try:
            normalized = GenerateRequest.from_dict(payload)
        except (TypeError, ValueError) as exc:
            raise InvalidRequestError("Invalid request.") from exc
        decision = runtime.entitlement_service.require_access(client, normalized.profile)
        runtime.usage_guard.check_and_consume_request(client, decision.monthly_token_quota)
        result = runtime.ai_service.generate(normalized)
        runtime.usage_guard.record_tokens(client, result.usage.total_tokens)
        return 200, {
            "request_id": request_id,
            "status": "ok",
            "client_id": client.client_id,
            "license_id": client.license_id,
            "product_id": client.product_id,
            "ai_mode": decision.ai_mode,
            "output": {"type": "text", "text": result.text},
            "usage": result.usage.to_dict(),
            "finish_reason": result.finish_reason,
        }
    except HubError as exc:
        return _error_body(request_id, exc)
