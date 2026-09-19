from uuid import uuid4

from app.core.config import get_settings
from app.core.errors import HubError, InvalidRequestError
from app.domain.models import GenerateRequest
from app.providers.router import ProviderRouter
from app.services.ai_service import AIService


def generate_response(payload: dict, request_id: str | None = None) -> tuple[int, dict]:
    request_id = request_id or f"req_{uuid4().hex}"
    try:
        try:
            normalized = GenerateRequest.from_dict(payload)
        except (TypeError, ValueError) as exc:
            raise InvalidRequestError("Invalid request.") from exc

        result = AIService(ProviderRouter(get_settings())).generate(normalized)
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
