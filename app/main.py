import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from app.api.v1.ai import generate_response, status_response
from app.api.v1.coach import understand_response
from app.core.config import get_settings
from app.core.cors import allowed_cors_origin, parse_cors_origins
from app.core.errors import HubError
from app.core.runtime import HubRuntime

VERSION = "0.4.0-termux"


def health_body() -> dict:
    return {"status": "ok", "service": "MEasyMate AI Hub", "version": VERSION, "phase": "coach-browser-bridge-v1"}


class HubHandler(BaseHTTPRequestHandler):
    server_version = "MEasyMateAIHub/0.4.0"

    def _cors_origin(self):
        return allowed_cors_origin(self.headers.get("Origin"), self.server.cors_origins)

    def _send_cors_headers(self):
        origin = self._cors_origin()
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type, X-Request-ID")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Max-Age", "600")

    def _send_json(self, status: int, body: dict):
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        if self.path not in {"/v1/ai/status", "/v1/ai/generate", "/v1/coach/understand"}:
            self._send_json(404, {"status": "error", "error": {"code": "NOT_FOUND", "message": "Not found.", "retryable": False}})
            return
        if self.headers.get("Origin") and not self._cors_origin():
            self._send_json(403, {"status": "error", "error": {"code": "ORIGIN_NOT_ALLOWED", "message": "Origin not allowed.", "retryable": False}})
            return
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            self._send_json(200, health_body())
            return
        if self.path == "/v1/ai/status":
            status, body = status_response(
                self.server.hub_runtime,
                self.headers.get("Authorization"),
                self.headers.get("X-Request-ID"),
            )
            self._send_json(status, body)
            return
        self._send_json(404, {"status": "error", "error": {"code": "NOT_FOUND", "message": "Not found.", "retryable": False}})

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 1_000_000:
            raise ValueError
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_POST(self):
        if self.path not in {"/v1/ai/generate", "/v1/coach/understand"}:
            self._send_json(404, {"status": "error", "error": {"code": "NOT_FOUND", "message": "Not found.", "retryable": False}})
            return
        try:
            payload = self._read_json()
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(400, {"status": "error", "error": {"code": "INVALID_REQUEST", "message": "Invalid request.", "retryable": False}})
            return
        fn = understand_response if self.path == "/v1/coach/understand" else generate_response
        status, body = fn(
            self.server.hub_runtime,
            payload,
            self.headers.get("Authorization"),
            self.headers.get("X-Request-ID"),
        )
        self._send_json(status, body)

    def log_message(self, fmt, *args):
        return


def run():
    host = os.getenv("AI_HUB_HOST", "127.0.0.1")
    port = int(os.getenv("AI_HUB_PORT", "8000"))
    settings = get_settings()
    try:
        runtime = HubRuntime.from_settings(settings)
        cors_origins = parse_cors_origins(settings.cors_origins_json)
    except HubError as exc:
        raise SystemExit(f"Startup failed: {exc.code}: {exc.public_message}") from exc
    server = ThreadingHTTPServer((host, port), HubHandler)
    server.hub_runtime = runtime
    server.cors_origins = cors_origins
    print(f"MEasyMate AI Hub {VERSION} listening on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
