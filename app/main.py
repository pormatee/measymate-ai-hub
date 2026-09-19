import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os

from app.api.v1.ai import generate_response

VERSION = "0.1.1-termux"


def health_body() -> dict:
    return {"status": "ok", "service": "MEasyMate AI Hub", "version": VERSION, "phase": "phase-1-in-progress"}


class HubHandler(BaseHTTPRequestHandler):
    server_version = "MEasyMateAIHub/0.1.1"

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
        else:
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

        status, body = generate_response(payload, self.headers.get("X-Request-ID"))
        self._send_json(status, body)

    def log_message(self, fmt, *args):
        return


def run():
    host = os.getenv("AI_HUB_HOST", "127.0.0.1")
    port = int(os.getenv("AI_HUB_PORT", "8000"))
    server = ThreadingHTTPServer((host, port), HubHandler)
    print(f"MEasyMate AI Hub {VERSION} listening on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
