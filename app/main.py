import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from app.api.v1.ai import generate_response, status_response
from app.core.config import get_settings
from app.core.errors import HubError
from app.core.runtime import HubRuntime

VERSION = "0.3.0-termux"

def health_body() -> dict:
    return {"status": "ok", "service": "MEasyMate AI Hub", "version": VERSION, "phase": "coach-entitlement-v1"}

class HubHandler(BaseHTTPRequestHandler):
    server_version = "MEasyMateAIHub/0.3.0"

    def _send_json(self, status: int, body: dict):
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

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

    def do_POST(self):
        if self.path != "/v1/ai/generate":
            self._send_json(404, {"status": "error", "error": {"code": "NOT_FOUND", "message": "Not found.", "retryable": False}})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 1_000_000:
                raise ValueError
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(400, {"status": "error", "error": {"code": "INVALID_REQUEST", "message": "Invalid request.", "retryable": False}})
            return
        status, body = generate_response(
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
    try:
        runtime = HubRuntime.from_settings(get_settings())
    except HubError as exc:
        raise SystemExit(f"Startup failed: {exc.code}: {exc.public_message}") from exc
    server = ThreadingHTTPServer((host, port), HubHandler)
    server.hub_runtime = runtime
    print(f"MEasyMate AI Hub {VERSION} listening on http://{host}:{port}")
    server.serve_forever()

if __name__ == "__main__":
    run()
