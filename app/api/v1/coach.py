import json
from uuid import uuid4

from app.core.errors import HubError, InvalidRequestError, ProfileNotAllowedError, ProviderUnavailableError
from app.core.runtime import HubRuntime
from app.domain.models import GenerateOptions, GenerateRequest, Message

_ALLOWED_STAGES = {"problem", "protect", "evidence", "compare", "hypothesis", "occ", "esc", "root", "action", "verify", "finish", "reflection"}
_ALLOWED_ANSWER_TYPES = {"fact", "evidence_result", "evidence_source", "hypothesis", "cause", "action", "unknown", "other"}
_ALLOWED_INTENTS = {"answer", "clarify", "confirm", "deny", "unknown", "other"}

_COACH_SYSTEM_PROMPT = """You are MEasyMate Coach Understanding Assistant.
Your job is to help the deterministic Core Coach understand a Thai shop-floor user's latest answer.
You are NOT the coach controller and you must NOT decide the root cause, select countermeasures, pass gates, advance stages, score the user, or write the final case record.
Treat prior experience as reference only. Never assume an old cause is the cause of the current case.
Analyze only the supplied context. Return exactly one JSON object, no markdown and no prose outside JSON.
Allowed keys only:
intent: one of answer, clarify, confirm, deny, unknown, other
answerType: one of fact, evidence_result, evidence_source, hypothesis, cause, action, unknown, other
entities: array of short strings
relevance: number 0..1
ambiguities: array of short strings
contradictions: array of short strings
questionCandidates: array of 0..3 short Thai questions that help the user provide missing information without suggesting the answer
reasoningGaps: array of short strings
confidence: number 0..1
Forbidden: rootCause, verifiedCause, recommendedAction, decision, gatePass, stageAdvance, finalCaseRecord, answer, finalAnswer.
If uncertain, lower confidence and propose a focused clarification question. Do not invent facts."""


def _error_body(request_id: str, exc: HubError) -> tuple[int, dict]:
    return exc.http_status, {
        "request_id": request_id,
        "status": "error",
        "error": {"code": exc.code, "message": exc.public_message, "retryable": exc.retryable},
    }


def _text(value, *, max_len: int, required: bool = False) -> str:
    if value is None:
        if required:
            raise InvalidRequestError("Invalid Coach understanding request.")
        return ""
    if not isinstance(value, str):
        raise InvalidRequestError("Invalid Coach understanding request.")
    value = value.strip()
    if required and not value:
        raise InvalidRequestError("Invalid Coach understanding request.")
    return value[:max_len]


def _str_list(value, *, max_items: int, max_len: int) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise InvalidRequestError("Invalid Coach understanding request.")
    out = []
    for item in value[:max_items]:
        if not isinstance(item, str):
            raise InvalidRequestError("Invalid Coach understanding request.")
        item = item.strip()
        if item:
            out.append(item[:max_len])
    return out


def normalize_context(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise InvalidRequestError("Invalid Coach understanding request.")
    stage = _text(payload.get("stage"), max_len=32, required=True)
    if stage not in _ALLOWED_STAGES:
        raise InvalidRequestError("Invalid Coach understanding request.")
    return {
        "stage": stage,
        "goal": _text(payload.get("goal"), max_len=240),
        "process": _text(payload.get("process"), max_len=120),
        "failure_mode": _text(payload.get("failure_mode"), max_len=120),
        "known_facts": _str_list(payload.get("known_facts"), max_items=12, max_len=300),
        "latest_answer": _text(payload.get("latest_answer"), max_len=1200, required=True),
        "experience_refs": _str_list(payload.get("experience_refs"), max_items=3, max_len=350),
    }


def _extract_json(text: str) -> dict:
    raw = (text or "").strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end < start:
        raise ProviderUnavailableError("AI understanding response was invalid.")
    try:
        data = json.loads(raw[start:end + 1])
    except json.JSONDecodeError as exc:
        raise ProviderUnavailableError("AI understanding response was invalid.") from exc
    if not isinstance(data, dict):
        raise ProviderUnavailableError("AI understanding response was invalid.")
    return data


def _score(value, default=0.0) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


def _clean_output_list(value, max_items=6, max_len=240) -> list[str]:
    if not isinstance(value, list):
        return []
    out = []
    for item in value[:max_items]:
        if isinstance(item, str):
            item = item.strip()
            if item:
                out.append(item[:max_len])
    return out


def normalize_proposal(raw: dict) -> dict:
    intent = raw.get("intent") if raw.get("intent") in _ALLOWED_INTENTS else "other"
    answer_type = raw.get("answerType") if raw.get("answerType") in _ALLOWED_ANSWER_TYPES else "other"
    return {
        "intent": intent,
        "answerType": answer_type,
        "entities": _clean_output_list(raw.get("entities"), max_items=10, max_len=120),
        "relevance": _score(raw.get("relevance")),
        "ambiguities": _clean_output_list(raw.get("ambiguities")),
        "contradictions": _clean_output_list(raw.get("contradictions")),
        "questionCandidates": _clean_output_list(raw.get("questionCandidates"), max_items=3, max_len=260),
        "reasoningGaps": _clean_output_list(raw.get("reasoningGaps")),
        "confidence": _score(raw.get("confidence")),
    }


def understand_response(runtime: HubRuntime, payload: dict, authorization_header: str | None,
                        request_id: str | None = None) -> tuple[int, dict]:
    request_id = request_id or f"req_{uuid4().hex}"
    try:
        client = runtime.registry.authenticate(authorization_header)
        if client.product_id != "coach":
            raise ProfileNotAllowedError("Coach understanding is not allowed for this product.")
        context = normalize_context(payload)
        decision = runtime.entitlement_service.require_access(client, "coach-understanding")
        runtime.usage_guard.check_and_consume_request(client, decision.monthly_token_quota)
        request = GenerateRequest(
            profile="coach-understanding",
            messages=[
                Message(role="system", content=_COACH_SYSTEM_PROMPT),
                Message(role="user", content=json.dumps(context, ensure_ascii=False, separators=(",", ":"))),
            ],
            options=GenerateOptions(max_output_tokens=320),
        )
        result = runtime.ai_service.generate(request)
        runtime.usage_guard.record_tokens(client, result.usage.total_tokens)
        proposal = normalize_proposal(_extract_json(result.text))
        return 200, {
            "request_id": request_id,
            "status": "ok",
            "client_id": client.client_id,
            "license_id": client.license_id,
            "product_id": client.product_id,
            "ai_mode": decision.ai_mode,
            "proposal": proposal,
            "usage": result.usage.to_dict(),
            "trusted": False,
        }
    except HubError as exc:
        return _error_body(request_id, exc)
