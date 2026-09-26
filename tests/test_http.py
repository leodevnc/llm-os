import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path

from llm_os.kernel import Kernel, DEMO_GOAL
from llm_os.providers import Runner
from llm_os.server import make_server


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.kernel = Kernel(Path(self.temp.name) / "workspace.sqlite3")
        self.kernel.seed()
        self.runner = Runner(self.kernel)
        self.server = make_server(self.kernel, self.runner, 0)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(self.runner.close)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def request(self, method, path, payload=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port)
        connection.request(method, path, body=json.dumps(payload) if payload is not None else None, headers=headers or {})
        response = connection.getresponse()
        result = (response.status, response.read(), dict(response.getheaders()))
        connection.close()
        return result

    def test_ui_and_workspace_load(self):
        status, content, headers = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b"LLM OS", content)
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        status, body, _ = self.request("GET", "/api/workspace")
        self.assertEqual(len(json.loads(body)["documents"]), 2)

    def test_cross_origin_and_missing_header_writes_denied(self):
        payload = {"title": "x", "content": "y"}
        self.assertEqual(self.request("POST", "/api/documents", payload)[0], 403)
        self.assertEqual(self.request("POST", "/api/documents", payload,
            {"Content-Type": "application/json", "X-LLM-OS": "workspace", "Origin": "https://outside.example"})[0], 403)

    def test_unknown_host_and_static_traversal_denied(self):
        self.assertEqual(self.request("GET", "/", headers={"Host": "outside.example"})[0], 403)
        self.assertEqual(self.request("GET", "/../kernel.py")[0], 404)

    def test_document_input_validation(self):
        headers = {"Content-Type": "application/json", "X-LLM-OS": "workspace"}
        self.assertEqual(self.request("POST", "/api/documents", {"title": "New", "content": "Evidence"}, headers)[0], 201)
        self.assertEqual(self.request("POST", "/api/documents", {"title": "New", "content": "Evidence", "path": "/tmp/x"}, headers)[0], 400)


if __name__ == "__main__":
    unittest.main()
