"""Local Ollama adapter and an explicitly scripted demonstration."""

import http.client
import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor

from .kernel import action_schema, validate_action


class Ollama:
    def __init__(self, port=11434, timeout=60):
        self.port = port
        self.timeout = timeout

    def request(self, method, path, body=None, timeout=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=self.timeout if timeout is None else timeout)
        try:
            connection.request(method, path, body=json.dumps(body).encode() if body else None,
                               headers={"Content-Type": "application/json"})
            response = connection.getresponse()
            raw = response.read(131073)
            if len(raw) > 131072:
                raise ValueError("Local model response exceeded 128 KiB")
            if response.status != 200:
                raise ValueError(f"Local model returned HTTP {response.status}; check that the model is installed")
            return json.loads(raw)
        except (OSError, http.client.HTTPException, json.JSONDecodeError) as exc:
            raise ValueError("Local Ollama is unavailable or returned an invalid response") from exc
        finally:
            connection.close()

    def models(self):
        try:
            payload = self.request("GET", "/api/tags", timeout=2)
            return {"available": True, "models": [item["name"] for item in payload.get("models", [])
                    if isinstance(item.get("name"), str) and "cloud" not in item["name"].casefold()]}
        except (ValueError, TypeError, KeyError, AttributeError):
            return {"available": False, "models": []}

    def next(self, task, messages):
        if "cloud" in task["model"].casefold():
            raise ValueError("Cloud model names are disabled; select an installed local model")
        response = self.request("POST", "/api/chat", {
            "model": task["model"], "messages": messages, "stream": False,
            "format": action_schema(), "options": {"temperature": 0, "num_predict": 2400}})
        try:
            return validate_action(json.loads(response["message"]["content"]))
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError("Model did not return a valid JSON action") from exc


class Demo:
    def next(self, task, messages):
        observations = [event["payload"] for event in task["events"] if event["kind"] == "observation"]
        denied = any(event["kind"] == "denied" for event in task["events"])
        if denied or any(isinstance(item["result"], dict) and "error" in item["result"] for item in observations):
            return {"op": "finish", "args": {"text": "The scripted demo stopped after a denied action. No further writes were requested."}}
        by_op = {item["op"]: item for item in observations}
        if "search" not in by_op:
            return {"op": "search", "args": {"query": "release"}}
        if "read" not in by_op:
            matches = by_op["search"]["result"]
            if not matches:
                return {"op": "finish", "args": {"text": "No release document was found in this task's snapshot."}}
            return {"op": "read", "args": {"document_id": matches[0]["id"]}}
        source = by_op["read"]["result"]
        if "write" not in by_op:
            return {"op": "write", "args": {"title": "Release brief", "content":
                "# Release brief\n\n" + source["content"] + "\n\nSource: " + source["title"] +
                "\n\nPrepared by the scripted demo; no language model was called."}}
        if "remember" not in by_op:
            owner = re.search(r"Owner:\s*([^\n]+)", source["content"])
            if owner:
                return {"op": "remember", "args": {"key": "release-owner", "value": owner.group(1)}}
        return {"op": "finish", "args": {"text": "The release brief is saved. Approved workspace memory is available to future tasks. This was the scripted demo."}}


class OSDemo:
    """A fixed, labeled program that exercises actual kernel operations."""
    def next(self, task, messages):
        observations = [event["payload"] for event in task["events"] if event["kind"] == "observation"]
        if any(event["kind"] == "denied" for event in task["events"]) or any(
            isinstance(item["result"], dict) and "error" in item["result"] for item in observations
        ):
            return {"op": "finish", "args": {"text": "The OS demo stopped after a denied or unsuccessful action."}}
        by_op = {item["op"]: item for item in observations}
        if "search" not in by_op:
            return {"op": "search", "args": {"query": "release"}}
        if "page_in" not in by_op:
            matches = by_op["search"]["result"]
            if not matches:
                return {"op": "finish", "args": {"text": "No release source was found."}}
            return {"op": "page_in", "args": {"document_id": matches[0]["id"]}}
        if "calculate" not in by_op:
            return {"op": "calculate", "args": {"expression": "18 * 7 + 24"}}
        if "fs_write" not in by_op:
            context = json.loads(messages[1]["content"])
            pages = context["resident_pages"]
            if not pages:
                return {"op": "finish", "args": {"text": "The source page is no longer resident."}}
            content = ("# Release brief\n\n" + pages[0]["content"] +
                       "\n\nPlanning estimate: " + str(by_op["calculate"]["result"]["value"]) +
                       " units (18 × 7 + 24).\n\nPrepared by the scripted OS demo.")
            return {"op": "fs_write", "args": {"path": "/reports/release-brief.md", "content": content}}
        if "page_out" not in by_op:
            return {"op": "page_out", "args": {"document_id": by_op["page_in"]["args"]["document_id"]}}
        return {"op": "finish", "args": {"text": "The reviewed report is on the virtual disk. Its source page was released from working memory. This was the scripted OS demo."}}


class Runner:
    def __init__(self, kernel, ollama=None, workers=2):
        self.kernel = kernel
        self.ollama = ollama or Ollama()
        self.pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="llm-os")
        self.lock = threading.Lock()
        self.scheduled = set()
        self.closing = False

    def submit(self, task_id):
        with self.lock:
            if self.closing or task_id in self.scheduled:
                return None
            self.scheduled.add(task_id)
            return self.pool.submit(self._tick, task_id)

    def _step(self, task_id):
        epoch = self.kernel.claim(task_id)
        if epoch is None:
            return False
        try:
            task = self.kernel.task(task_id)
            provider = {"demo": Demo(), "os-demo": OSDemo()}.get(task["mode"], self.ollama)
            action = provider.next(task, self.kernel.context(task_id))
            self.kernel.commit_action(task_id, epoch, action)
        except Exception as exc:
            self.kernel.fail(task_id, epoch, str(exc))
        return True

    def _tick(self, task_id):
        try:
            self._step(task_id)
        finally:
            with self.lock:
                self.scheduled.discard(task_id)
            if self.kernel.task(task_id)["state"] == "ready":
                self.submit(task_id)  # Yield to already queued tasks after one model turn.

    def drive(self, task_id):
        """Synchronous driver for deterministic tests and embedded use."""
        while self._step(task_id):
            pass

    def close(self):
        with self.lock:
            self.closing = True
        self.pool.shutdown(wait=True, cancel_futures=True)
