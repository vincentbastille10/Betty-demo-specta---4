import json
from http.server import BaseHTTPRequestHandler


class handler(BaseHTTPRequestHandler):
    def _send_json(self, status_code: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length) if content_length > 0 else b"{}"

        try:
            data = json.loads(raw_body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Invalid JSON"})
            return

        message = str(data.get("message", "")).strip()
        if not message:
            self._send_json(400, {"error": "Message is required"})
            return

        self._send_json(200, {"response": f"Betty: {message}"})

    def do_GET(self) -> None:
        self._send_json(405, {"error": "Method not allowed"})
