"""POST /run (task 23): the system's entry point over HTTP.

The manager's question goes in, the structured result of one run comes out
(agent/orchestrator.py: RunRequest and RunResult). Standard library only:
one endpoint does not justify a web framework dependency.

    python -m agent.api [--host 127.0.0.1] [--port 8080]

    POST /run     body: RunRequest as JSON  -> 200 RunResult as JSON
                  invalid body               -> 400 {"error": ..., "details": [...]}
    GET  /health                             -> 200 {"ok": true, "sample_mode": ...}
"""
import argparse
import json
import sys
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from pydantic import ValidationError

from agent.orchestrator import RunRequest, run
from agent.zetaris import sample_mode

MAX_BODY = 64 * 1024


class Handler(BaseHTTPRequestHandler):
    run_options = {}  # keyword arguments passed to run(), for tests

    def _send(self, status, payload):
        data = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/health":
            self._send(200, {"ok": True, "sample_mode": sample_mode()})
        else:
            self._send(404, {"error": f"no route GET {self.path}"})

    def do_POST(self):
        if self.path != "/run":
            self._send(404, {"error": f"no route POST {self.path}"})
            return
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            self._send(413, {"error": f"body larger than {MAX_BODY} bytes"})
            return
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(body, dict):
                raise ValueError("the body must be a JSON object")
            # The date is explicit in the result; by default it is the server's day.
            body.setdefault("today", date.today().isoformat())
            request = RunRequest.model_validate(body)
        except ValidationError as invalid:
            self._send(400, {"error": "invalid RunRequest",
                             "details": json.loads(invalid.json(include_url=False))})
            return
        except ValueError as error:
            self._send(400, {"error": f"invalid JSON body: {error}"})
            return
        try:
            result = run(request, **self.run_options)
        except ValueError as error:  # e.g. an unknown scenario
            self._send(400, {"error": str(error)})
            return
        self._send(200, json.loads(result.model_dump_json()))

    def log_message(self, format, *args):
        sys.stderr.write(f"api: {format % args}\n")


def serve(host="127.0.0.1", port=8080):
    server = ThreadingHTTPServer((host, port), Handler)
    sys.stderr.write(f"api: listening on http://{host}:{port} (POST /run, GET /health)\n")
    server.serve_forever()


def main(argv):
    parser = argparse.ArgumentParser(description="Serve POST /run.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args(argv)
    serve(args.host, args.port)


if __name__ == "__main__":
    main(sys.argv[1:])
