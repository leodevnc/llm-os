"""Loopback operator interface. Local host access is the trust boundary."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .kernel import Conflict


def make_server(kernel, runner, port=8787):
    assets = Path(__file__).parent / "static"

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, status, payload, content_type="application/json"):
            raw = json.dumps(payload).encode() if content_type == "application/json" else payload
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            try:
                self.wfile.write(raw)
            except (BrokenPipeError, ConnectionResetError):
                pass  # The browser closed after the operation completed.

        def trusted(self, write=False):
            valid = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
            host = self.headers.get("Host", "")
            origin = self.headers.get("Origin")
            if host not in valid or (origin and origin != f"http://{host}"):
                self.send(403, {"error": "Local origin required"})
                return False
            if write and (self.headers.get("X-LLM-OS") != "workspace" or self.headers.get_content_type() != "application/json"):
                self.send(403, {"error": "Workspace JSON request required"})
                return False
            return True

        def do_GET(self):
            if not self.trusted():
                return
            path = urlsplit(self.path).path
            try:
                if path == "/api/workspace":
                    self.send(200, kernel.workspace())
                elif path == "/api/models":
                    self.send(200, runner.ollama.models())
                elif path.startswith("/api/tasks/"):
                    self.send(200, kernel.task(path.removeprefix("/api/tasks/")))
                elif path in {"/", "/app.js", "/os.js", "/style.css"}:
                    name = "index.html" if path == "/" else path[1:]
                    mime = {"index.html": "text/html; charset=utf-8", "app.js": "text/javascript; charset=utf-8", "os.js": "text/javascript; charset=utf-8", "style.css": "text/css; charset=utf-8"}[name]
                    self.send(200, (assets / name).read_bytes(), mime)
                else:
                    self.send(404, {"error": "Not found"})
            except KeyError:
                self.send(404, {"error": "Task not found"})

        def do_POST(self):
            if not self.trusted(write=True):
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 65536:
                    raise ValueError("Request body must be 1–65536 bytes")
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError("Expected a JSON object")
                path = urlsplit(self.path).path
                if path == "/api/tasks":
                    if not {"goal", "mode", "model", "writes", "max_steps"} <= set(data) or set(data) - {"goal", "mode", "model", "writes", "max_steps", "app_id"}:
                        raise ValueError("Invalid task fields")
                    task_id = kernel.create(**data)
                    runner.submit(task_id)
                    self.send(201, {"id": task_id})
                elif path == "/api/documents":
                    if set(data) != {"title", "content"}:
                        raise ValueError("Invalid document fields")
                    self.send(201, {"id": kernel.add_document(**data)})
                elif path.endswith("/approve") and path.startswith("/api/tasks/"):
                    task_id = path.split("/")[3]
                    if set(data) != {"digest", "approved"}:
                        raise ValueError("Invalid approval fields")
                    kernel.approve(task_id, data["digest"], data["approved"])
                    runner.submit(task_id)
                    self.send(200, {"ok": True})
                elif path.endswith("/cancel") and path.startswith("/api/tasks/"):
                    kernel.cancel(path.split("/")[3])
                    self.send(200, {"ok": True})
                else:
                    self.send(404, {"error": "Not found"})
            except Conflict as exc:
                self.send(409, {"error": str(exc)})
            except KeyError:
                self.send(404, {"error": "Task not found"})
            except (ValueError, UnicodeDecodeError) as exc:
                self.send(400, {"error": str(exc)})

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)
