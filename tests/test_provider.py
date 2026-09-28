import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from llm_os.providers import Ollama


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.requests = []
        owner = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_POST(self):
                owner.requests.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                result = {"message": {"content": json.dumps({"op": "finish", "args": {"text": "Local stub response"}})}}
                body = json.dumps(result).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def test_real_http_adapter_sends_schema_and_validates_reply(self):
        model = Ollama(self.server.server_port)
        result = model.next({"model": "installed-local"}, [{"role": "user", "content": "hello"}])
        self.assertEqual(result["op"], "finish")
        request = self.requests[0]
        self.assertFalse(request["stream"])
        self.assertEqual(len(request["format"]["oneOf"]), 12)
        self.assertEqual(request["options"]["temperature"], 0)

    def test_cloud_name_rejected_before_request(self):
        with self.assertRaises(ValueError):
            Ollama(self.server.server_port).next({"model": "example:cloud"}, [])
        self.assertEqual(self.requests, [])


if __name__ == "__main__":
    unittest.main()
