from uuid import uuid4

from app.core.errors import HubError, IdentityMismatchError, InvalidRequestError
from app.core.runtime import HubRuntime
from app.domain.models import GenerateRequest


def generate_response(
    runtime: HubRuntime,
    payload: dict,
    authorization_header: str | None,
    request_id: str | None = None,
) -> tuple[int, dict]:
    request_id = request_id or f"req_{uuid4().hex}"

    try:
        client = runtime.registry.authenticate(authorization_header)

        if isinstance(payload, dict) and ("product_id" in payload or "client_id" in payload):
            raise IdentityMismatchError("Client identity is determined by authentication.")

        try:
            normalized = GenerateRequest.from_dict(payload)
        except (TypeError, ValueError) as exc:
            raise InvalidRequestError("Invalid request.") from exc

        runtime.usage_guard.check_and_consume(client)
        result = runtime.ai_service.generate(normalized)

        return 200, {
            "request_id": request_id,
            "status": "ok",
            "output": {"type": "text", "text": result.text},
            "usage": result.usage.to_dict(),
            "finish_reason": result.finish_reason,
        }
    except HubError as exc:
        return exc.http_status, {
            "request_id": request_id,
            "status": "error",
            "error": {"code": exc.code, "message": exc.public_message, "retryable": exc.retryable},
        }
