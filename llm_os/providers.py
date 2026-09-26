"""Local Ollama adapter and an explicitly scripted demonstration."""

import http.client
import json
import re
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


class Runner:
    def __init__(self, kernel, ollama=None):
        self.kernel = kernel
        self.ollama = ollama or Ollama()
        self.pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="llm-os")

    def submit(self, task_id):
        return self.pool.submit(self.drive, task_id)

    def drive(self, task_id):
        while True:
            epoch = self.kernel.claim(task_id)
            if epoch is None:
                return
            try:
                task = self.kernel.task(task_id)
                provider = Demo() if task["mode"] == "demo" else self.ollama
                action = provider.next(task, self.kernel.context(task_id))
                self.kernel.commit_action(task_id, epoch, action)
            except Exception as exc:
                self.kernel.fail(task_id, epoch, str(exc))
                return

    def close(self):
        self.pool.shutdown(wait=True, cancel_futures=True)
