import concurrent.futures
import json
import tempfile
import unittest
from pathlib import Path

from llm_os.kernel import Conflict, DEMO_GOAL, Kernel, validate_action
from llm_os.providers import Runner


class KernelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.kernel = Kernel(Path(self.temp.name) / "state.sqlite3")
        self.kernel.seed()

    def task(self, **kwargs):
        return self.kernel.create(DEMO_GOAL, **kwargs)

    def action(self, task_id, op, **args):
        epoch = self.kernel.claim(task_id)
        return self.kernel.commit_action(task_id, epoch, {"op": op, "args": args})

    def approve(self, task_id, yes=True):
        pending = self.kernel.task(task_id)["pending"]
        self.kernel.approve(task_id, pending["digest"], yes)

    def test_demo_requires_two_reviews_and_saves_once(self):
        task_id = self.task()
        runner = Runner(self.kernel)
        self.addCleanup(runner.close)
        runner.drive(task_id)
        task = self.kernel.task(task_id)
        self.assertEqual(task["state"], "waiting")
        self.assertEqual(task["artifacts"], [])
        digest = task["pending"]["digest"]
        self.approve(task_id)
        with self.assertRaises(Conflict):
            self.kernel.approve(task_id, digest, True)
        runner.drive(task_id)
        self.assertEqual(self.kernel.task(task_id)["pending"]["action"]["op"], "remember")
        self.assertEqual(self.kernel.workspace()["memory"], [])
        self.approve(task_id)
        runner.drive(task_id)
        task = self.kernel.task(task_id)
        self.assertEqual(task["state"], "succeeded")
        self.assertEqual(task["steps"], 5)
        self.assertEqual(len(task["artifacts"]), 1)
        self.assertEqual(self.kernel.workspace()["memory"][0]["value"], "Mina")

    def test_cancellation_fences_late_model_response(self):
        task_id = self.task()
        epoch = self.kernel.claim(task_id)
        self.kernel.cancel(task_id)
        self.assertFalse(self.kernel.commit_action(task_id, epoch, {"op": "write", "args": {"title": "Late", "content": "Ignore cancellation"}}))
        self.assertEqual(self.kernel.task(task_id)["state"], "cancelled")
        self.assertIsNone(self.kernel.task(task_id)["pending"])

    def test_read_only_task_cannot_request_persistence(self):
        task_id = self.task(writes=False)
        self.action(task_id, "remember", key="x", value="y")
        self.assertIsNone(self.kernel.task(task_id)["pending"])
        self.assertEqual(self.kernel.workspace()["memory"], [])
        self.assertEqual(self.kernel.task(task_id)["events"][-1]["kind"], "denied")

    def test_read_uses_creation_snapshot(self):
        task_id = self.task()
        with self.kernel.transaction() as db:
            db.execute("UPDATE documents SET content='changed after submission' WHERE id='release-notes'")
        self.action(task_id, "read", document_id="release-notes")
        result = self.kernel.task(task_id)["events"][-1]["payload"]["result"]
        self.assertIn("Owner: Mina", result["content"])

    def test_document_outside_snapshot_is_unavailable(self):
        task_id = self.task()
        doc_id = self.kernel.add_document("Later", "Created later")
        self.action(task_id, "read", document_id=doc_id)
        self.assertIn("error", self.kernel.task(task_id)["events"][-1]["payload"]["result"])

    def test_stale_memory_review_is_rejected(self):
        first, second = self.task(), self.task()
        self.action(first, "remember", key="owner", value="A")
        self.action(second, "remember", key="owner", value="B")
        self.approve(first)
        with self.assertRaises(Conflict):
            self.approve(second)
        self.assertEqual(self.kernel.workspace()["memory"][0]["value"], "A")
        self.approve(second, False)
        self.assertEqual(self.kernel.task(second)["state"], "ready")

    def test_rejection_produces_no_artifact(self):
        task_id = self.task()
        self.action(task_id, "write", title="Review", content="Not yet saved")
        self.approve(task_id, False)
        self.assertEqual(self.kernel.task(task_id)["artifacts"], [])

    def test_step_budget_terminates_repeating_actions(self):
        task_id = self.task(max_steps=2)
        self.action(task_id, "search", query="missing")
        self.action(task_id, "search", query="missing")
        self.assertIsNone(self.kernel.claim(task_id))
        self.assertEqual(self.kernel.task(task_id)["state"], "failed")
        self.assertEqual(self.kernel.task(task_id)["steps"], 2)

    def test_restart_fences_old_epoch_and_preserves_budget(self):
        task_id = self.task()
        epoch = self.kernel.claim(task_id)
        restarted = Kernel(self.kernel.path)
        self.assertIn(task_id, restarted.recover())
        self.assertFalse(restarted.commit_action(task_id, epoch, {"op": "finish", "args": {"text": "old response"}}))
        self.assertEqual(restarted.task(task_id)["steps"], 1)

    def test_concurrent_claim_has_one_owner(self):
        task_id = self.task()
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            claims = list(pool.map(lambda _: self.kernel.claim(task_id), range(8)))
        self.assertEqual(sum(claim is not None for claim in claims), 1)

    def test_unknown_tool_and_extra_fields_rejected(self):
        for action in [{"op": "shell", "args": {"command": "id"}},
                       {"op": "read", "args": {"document_id": "release-notes", "path": "/etc/passwd"}},
                       {"op": "finish", "args": {"text": "yes"}, "approved": True}]:
            with self.assertRaises(ValueError):
                validate_action(action)

    def test_bad_provider_action_fails_without_effect(self):
        class BadModel:
            def next(self, task, messages):
                return {"op": "shell", "args": {"command": "ignored"}}
        task_id = self.kernel.create("Do a task", "ollama", "local-test")
        runner = Runner(self.kernel, BadModel())
        self.addCleanup(runner.close)
        runner.drive(task_id)
        self.assertEqual(self.kernel.task(task_id)["state"], "failed")
        self.assertEqual(self.kernel.task(task_id)["artifacts"], [])

    def test_context_labels_omitted_history(self):
        task_id = self.task(max_steps=20)
        for _ in range(5):
            self.action(task_id, "read", document_id="release-notes")
        context = json.loads(self.kernel.context(task_id)[1]["content"])
        self.assertEqual(context["omitted_observations"], 0)
        self.assertEqual(len(context["observations"]), 5)
        self.assertIn("write_capability", context)

    def test_context_evicts_old_observations_at_character_budget(self):
        doc_id = self.kernel.add_document("Large source", "a" * 12000)
        task_id = self.task()
        self.action(task_id, "read", document_id=doc_id)
        self.action(task_id, "read", document_id=doc_id)
        context = json.loads(self.kernel.context(task_id)[1]["content"])
        self.assertEqual(len(context["observations"]), 1)
        self.assertEqual(context["omitted_observations"], 1)

    def test_memory_is_recalled_with_approved_version(self):
        writer = self.task()
        self.action(writer, "remember", key="owner", value="Mina")
        self.approve(writer)
        reader = self.task()
        self.action(reader, "recall", query="owner")
        result = self.kernel.task(reader)["events"][-1]["payload"]["result"]
        self.assertEqual(result, [{"key": "owner", "value": "Mina", "version": 1}])

    def test_cancelled_review_cannot_be_approved(self):
        task_id = self.task()
        self.action(task_id, "write", title="x", content="y")
        approval = self.kernel.task(task_id)["pending"]["digest"]
        self.kernel.cancel(task_id)
        with self.assertRaises(Conflict):
            self.kernel.approve(task_id, approval, True)
        self.assertEqual(self.kernel.task(task_id)["artifacts"], [])

    def test_document_limits_and_fixed_demo(self):
        with self.assertRaises(ValueError):
            self.kernel.add_document("x", "a" * 12001)
        with self.assertRaises(ValueError):
            self.kernel.create("Pretend arbitrary demo generation")


if __name__ == "__main__":
    unittest.main()
