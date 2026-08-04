import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    model = "idm-vton"

    def _json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._json(200, {"ok": True, "provider": "local_vton_stub", "model": self.model})
            return
        self._json(404, {"error": "not_found"})

    def do_POST(self):
        if self.path == "/v1/try-on":
            self._json(501, {
                "error": "stub_only",
                "message": "Install an approved local VTON model before using this provider for evaluation.",
                "model": self.model,
            })
            return
        self._json(404, {"error": "not_found"})

    def log_message(self, fmt, *args):
        print("[local-vton]", fmt % args)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8788)
    parser.add_argument("--model", default="idm-vton")
    args = parser.parse_args()
    Handler.model = args.model
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"[local-vton] listening on http://{args.host}:{args.port} model={args.model}")
    server.serve_forever()


if __name__ == "__main__":
    main()
