import json
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path

from llm_os import filesystem
from llm_os.kernel import Conflict, Kernel
from llm_os.programs import OS_GOAL, calculate
from llm_os.providers import Runner


class OSTests(unittest.TestCase):
    def test_unknown_and_non_string_apps_are_rejected(self):
        for app in ([], {}, None, "uninstalled"):
            with self.subTest(app=app), self.assertRaises(ValueError):
                self.kernel.create("Inspect documents", mode="ollama", model="local", app_id=app)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.kernel = Kernel(Path(self.temp.name) / "state.sqlite3")
        self.kernel.seed()

    def task(self, app_id="research"):
        return self.kernel.create("Inspect workspace", "ollama", "test-local", app_id=app_id)

    def action(self, task, op, **args):
        epoch = self.kernel.claim(task)
        self.kernel.commit_action(task, epoch, {"op": op, "args": args})
        return self.kernel.task(task)["events"][-1]["payload"]

    def approve(self, task):
        self.kernel.approve(task, self.kernel.task(task)["pending"]["digest"], True)

    def test_os_demo_pages_computes_writes_and_releases(self):
        task = self.kernel.create(OS_GOAL, "os-demo", app_id="research")
        runner = Runner(self.kernel)
        self.addCleanup(runner.close)
        runner.drive(task)
        self.assertEqual(self.kernel.task(task)["state"], "waiting")
        self.assertGreater(self.kernel.task(task)["working_memory"]["used_chars"], 0)
        self.assertEqual(self.kernel.workspace()["files"], [])
        self.approve(task)
        runner.drive(task)
        result = self.kernel.task(task)
        self.assertEqual(result["state"], "succeeded")
        self.assertEqual(result["steps"], 6)
        self.assertEqual(result["working_memory"]["used_chars"], 0)
        self.assertIn("150 units", result["files_written"][0]["content"])

    def test_paging_evicts_and_restores_backing_document(self):
        a = self.kernel.add_document("a", "a" * 7000)
        b = self.kernel.add_document("b", "b" * 7000)
        task = self.task()
        self.action(task, "page_in", document_id=a)
        output = self.action(task, "page_in", document_id=b)["result"]
        self.assertEqual(output["evicted"], [a])
        context = json.loads(self.kernel.context(task)[1]["content"])
        self.assertEqual([p["id"] for p in context["resident_pages"]], [b])
        self.action(task, "page_in", document_id=a)
        context = json.loads(self.kernel.context(task)[1]["content"])
        self.assertEqual(context["resident_pages"][0]["content"], "a" * 7000)

    def test_page_touch_changes_eviction_order(self):
        ids = [self.kernel.add_document(str(i), str(i) * 5000) for i in range(3)]
        task = self.task()
        for index in [0, 1, 0]:
            self.action(task, "page_in", document_id=ids[index])
        result = self.action(task, "page_in", document_id=ids[2])["result"]
        self.assertEqual(result["evicted"], [ids[1]])

    def test_page_out_does_not_delete_disk_source(self):
        task = self.task()
        self.action(task, "page_in", document_id="release-notes")
        self.action(task, "page_out", document_id="release-notes")
        self.assertEqual(self.kernel.task(task)["working_memory"]["pages"], [])
        result = self.action(task, "page_in", document_id="release-notes")["result"]
        self.assertEqual(result["loaded"], "release-notes")

    def test_reviewer_cannot_escalate_to_write(self):
        task = self.task("reviewer")
        result = self.action(task, "fs_write", path="/reports/forbidden.md", content="x")
        self.assertIn("capability", result["error"])
        self.assertIsNone(self.kernel.task(task)["pending"])

    def test_research_app_cannot_write_other_namespace(self):
        task = self.task()
        result = self.action(task, "fs_write", path="/notes/private.md", content="x")
        self.assertIn("capability", result["error"])
        self.assertEqual(self.kernel.workspace()["files"], [])

    def test_files_are_visible_to_later_tasks(self):
        writer = self.task()
        self.action(writer, "fs_write", path="/reports/a.md", content="approved evidence")
        self.approve(writer)
        reader = self.task("reviewer")
        result = self.action(reader, "fs_read", path="/reports/a.md")["result"]
        self.assertEqual(result["content"], "approved evidence")
        self.assertEqual(result["version"], 1)

    def test_stale_file_approval_cannot_overwrite_newer_version(self):
        a, b = self.task(), self.task()
        self.action(a, "fs_write", path="/reports/a.md", content="a")
        self.action(b, "fs_write", path="/reports/a.md", content="b")
        self.approve(a)
        with self.assertRaises(Conflict):
            self.approve(b)
        self.assertEqual(self.kernel.workspace()["files"][0]["content"], "a")

    def test_history_preserves_previous_file_content(self):
        a, b = self.task(), self.task()
        self.action(a, "fs_write", path="/reports/a.md", content="v1")
        self.approve(a)
        self.action(b, "fs_write", path="/reports/a.md", content="v2")
        self.approve(b)
        self.assertEqual(self.kernel.task(a)["files_written"][0]["content"], "v1")
        self.assertEqual(self.kernel.workspace()["files"][0]["version"], 2)

    def test_failed_event_append_rolls_back_file_write(self):
        task = self.task()
        self.action(task, "fs_write", path="/reports/a.md", content="x")
        original = self.kernel.event
        def fail_observation(db, task_id, kind, payload):
            if kind == "observation":
                raise RuntimeError("injected journal failure")
            original(db, task_id, kind, payload)
        self.kernel.event = fail_observation
        with self.assertRaises(RuntimeError):
            self.approve(task)
        self.assertEqual(self.kernel.workspace()["files"], [])
        self.assertEqual(self.kernel.task(task)["state"], "waiting")

    def test_virtual_paths_reject_traversal_and_host_paths(self):
        for value in ["../x", "/reports/../notes/x", "/reports//x", "C:\\x", "/reports/a\x00b", "/reports/./x", "file:///tmp/x"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                filesystem.path(value)

    def test_calculator_rejects_execution_and_unbounded_math(self):
        self.assertEqual(calculate("18 * 7 + 24")["value"], 150)
        for expression in ["__import__('os')", "2**10000", "1/0", "1e999", "True", "x.y", "[1]", "9*999999999999"]:
            with self.subTest(expression=expression), self.assertRaises(ValueError):
                calculate(expression)

    def test_scheduler_yields_after_one_model_turn(self):
        entered, release, finished = threading.Event(), threading.Event(), threading.Event()
        calls = []
        class Model:
            def next(self, task, messages):
                calls.append(task["id"])
                if len(calls) == 1:
                    entered.set()
                    if not release.wait(3):
                        raise RuntimeError("test release timeout")
                if len(calls) == 4:
                    finished.set()
                return {"op": "calculate", "args": {"expression": "1+1"}} if task["steps"] == 1 else {"op": "finish", "args": {"text": "done"}}
        a, b = self.task(), self.task()
        runner = Runner(self.kernel, Model(), workers=1)
        self.addCleanup(runner.close)
        runner.submit(a)
        self.assertTrue(entered.wait(3))
        runner.submit(b)
        release.set()
        self.assertTrue(finished.wait(3))
        runner.close()
        self.assertEqual(calls, [a, b, a, b])
        self.assertEqual(self.kernel.task(b)["state"], "succeeded")

    def test_additive_migration_preserves_existing_task(self):
        task = self.task("workspace")
        with self.kernel.transaction() as db:
            db.execute("ALTER TABLE tasks DROP COLUMN app_spec")
        migrated = Kernel(self.kernel.path)
        self.assertEqual(migrated.task(task)["goal"], "Inspect workspace")
        self.assertEqual(migrated.task(task)["app"]["id"], "workspace")


if __name__ == "__main__":
    unittest.main()
