"""Offline regression tests; no agent or model API is invoked."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/evaluation"))
import evaluation_common as evaluation


class EvaluationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.dataset = self.directory / "tasks.jsonl"
        self.tasks = [
            {"id": "A", "attribute": "A attribute", "filter": "None", "sort": "A sort"},
            {"id": "B", "attribute": "B attribute", "filter": "B filter", "sort": None},
            {"id": "C", "attribute": "C attribute", "filter": "C filter", "sort": "C sort"},
        ]
        self.dataset.write_text("".join(json.dumps(t) + "\n" for t in self.tasks))
        self.args = evaluation.parse_args([
            "--dataset", str(self.dataset), "--run-name", "custom-run",
            "--results-dir", str(self.directory / "traces"),
            "--output-dir", str(self.directory / "new-results"),
        ])
        for task in self.tasks:
            path = self.args.results_dir / self.args.run_name / ("task" + task["id"])
            path.mkdir(parents=True)
            final = "Action: ANSWER; [a product]" if task["id"] != "C" else "Action: Click [1]"
            (path / "interact_messages.json").write_text(json.dumps([
                {"role": "system", "content": "instructions"},
                {"role": "assistant", "content": final},
            ]))
            # A PNG signature suffices for the validator's file/header check.
            (path / "screenshot1.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    def evaluate_fixture(self):
        def fake_judge(client, args, subquery, trace):
            score = 0 if subquery == "B attribute" else 1
            return score, "SUCCESS" if score else "NOT SUCCESS", "recorded-test-model"
        with mock.patch.object(evaluation, "create_client", return_value=object()), \
             mock.patch.object(evaluation, "judge", side_effect=fake_judge), \
             contextlib.redirect_stdout(io.StringIO()):
            for dimension in evaluation.DIMENSIONS:
                evaluation.evaluate_dimension(self.args, dimension)

    def test_real_example_dry_run_needs_no_third_party_packages_or_outputs(self):
        result = subprocess.run(
            [sys.executable, "-S", str(ROOT / "src/evaluation/evaluation_common.py"),
             "--dry-run", "--output-dir", str(self.directory / "must-not-exist")],
            cwd=self.directory, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["tasks"], 10)
        self.assertEqual(report["applicable_tasks"], {"attribute": 10, "filter": 8, "sort": 1})
        self.assertEqual(report["api_calls"], 0)
        self.assertEqual(report["attached_screenshots"], 61)
        self.assertFalse((self.directory / "must-not-exist").exists())

    def test_odd_task_count_absent_dimensions_and_id_join_ignore_record_order(self):
        self.evaluate_fixture()
        for dimension in evaluation.DIMENSIONS:
            path = self.args.output_dir / (dimension + ".json")
            payload = json.loads(path.read_text())
            self.assertEqual(len(payload["tasks"]), 3)
            self.assertEqual(payload["tasks"][2]["reason"], "no_final_answer")
            self.assertEqual(payload["judge"]["requested_model"], "gpt-4o")
            payload["tasks"].reverse()
            path.write_text(json.dumps(payload))
        with contextlib.redirect_stdout(io.StringIO()):
            evaluation.aggregate(self.args)
        overall = json.loads((self.args.output_dir / "overall.json").read_text())
        self.assertEqual(overall["tasks"], [
            {"id": "A", "success": 1}, {"id": "B", "success": 0}, {"id": "C", "success": 0},
        ])
        filtering = json.loads((self.args.output_dir / "filter.json").read_text())
        self.assertEqual(filtering["summary"]["n_applicable"], 2)
        self.assertEqual(filtering["summary"]["rate_percent"], 50)
        self.assertEqual(next(t for t in filtering["tasks"] if t["id"] == "A")["success"], None)
        self.assertEqual(next(t for t in filtering["tasks"] if t["id"] == "B")["response_model"],
                         "recorded-test-model")
        self.assertEqual(list(self.directory.rglob("*.npy")), [])

    def test_no_applicable_dimension_has_no_api_call_and_no_zero_division(self):
        for task in self.tasks:
            task["filter"] = "None"
        self.dataset.write_text("".join(json.dumps(t) + "\n" for t in self.tasks))
        with mock.patch.object(evaluation, "create_client", side_effect=AssertionError("No API")), \
             contextlib.redirect_stdout(io.StringIO()):
            evaluation.evaluate_dimension(self.args, "filter")
        payload = json.loads((self.args.output_dir / "filter.json").read_text())
        self.assertEqual(payload["summary"], {"n_applicable": 0, "successes": 0, "rate_percent": None})

    def test_aggregation_rejects_missing_duplicate_mismatched_and_invalid_records(self):
        self.evaluate_fixture()
        path = self.args.output_dir / "filter.json"
        original = path.read_text()
        changes = {
            "missing ID": lambda p: p["tasks"].pop(),
            "duplicate ID": lambda p: p["tasks"].append(p["tasks"][0]),
            "wrong applicability": lambda p: p["tasks"][0].update(applicable=True, success=1),
            "invalid label": lambda p: p["tasks"][1].update(success=2),
            "wrong dataset": lambda p: p.update(dataset_sha256="incorrect"),
            "wrong run": lambda p: p.update(run_name="other"),
            "wrong judge model": lambda p: p["judge"].update(requested_model="different-model"),
            "wrong judge temperature": lambda p: p["judge"].update(temperature=1),
            "wrong judge seed": lambda p: p["judge"].update(seed=99),
            "wrong screenshot budget": lambda p: p["judge"].update(max_attached_imgs=1),
            "missing judge configuration": lambda p: p.pop("judge"),
        }
        for name, mutate in changes.items():
            with self.subTest(name=name):
                payload = json.loads(original)
                mutate(payload)
                path.write_text(json.dumps(payload))
                with self.assertRaises(ValueError):
                    evaluation.aggregate(self.args)
                self.assertFalse((self.args.output_dir / "overall.json").exists())

    def test_duplicate_dataset_ids_fail_before_api(self):
        self.dataset.write_text(json.dumps(self.tasks[0]) + "\n" + json.dumps(self.tasks[0]))
        with self.assertRaisesRegex(ValueError, "Duplicate task ID"):
            evaluation.validate_inputs(self.args)

    def test_missing_trace_makes_shell_fail_without_success_message(self):
        result = subprocess.run([
            "sh", str(ROOT / "scripts/run_evaluation.sh"),
            "--dataset", str(self.dataset), "--run-name", "missing",
            "--results-dir", str(self.args.results_dir), "--dry-run",
        ], cwd=self.directory, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Missing trajectory", result.stderr)
        self.assertNotIn("completed", result.stdout)
        self.assertFalse(self.args.output_dir.exists())

    def test_api_failure_is_nonzero_and_does_not_save_or_echo_details(self):
        argv = ["--dataset", str(self.dataset), "--run-name", self.args.run_name,
                "--results-dir", str(self.args.results_dir),
                "--output-dir", str(self.args.output_dir)]
        stderr = io.StringIO()
        with mock.patch.object(evaluation, "create_client", return_value=object()), \
             mock.patch.object(evaluation, "judge", side_effect=RuntimeError("private-request-detail")), \
             contextlib.redirect_stderr(stderr):
            self.assertEqual(evaluation.main("attribute", argv), 1)
        self.assertNotIn("private-request-detail", stderr.getvalue())
        self.assertFalse(self.args.output_dir.exists())

    def test_existing_output_is_not_overwritten_or_sent_to_api(self):
        self.evaluate_fixture()
        path = self.args.output_dir / "attribute.json"
        before = path.read_bytes()
        with mock.patch.object(evaluation, "create_client", side_effect=AssertionError("No API")):
            with self.assertRaisesRegex(ValueError, "Output exists"):
                evaluation.evaluate_dimension(self.args, "attribute")
        self.assertEqual(path.read_bytes(), before)

    def test_request_preserves_prompt_and_records_returned_model_without_network(self):
        response = SimpleNamespace(model="returned-snapshot", choices=[
            SimpleNamespace(message=SimpleNamespace(content="Verdict: NOT SUCCESS"))])
        request = mock.Mock(return_value=response)
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=request)))
        trace = evaluation.load_trace(self.args, self.tasks[0])
        self.assertEqual(evaluation.judge(client, self.args, "A attribute", trace),
                         (0, "Verdict: NOT SUCCESS", "returned-snapshot"))
        arguments = request.call_args.kwargs
        self.assertEqual(arguments["messages"][0]["content"], evaluation.SYSTEM_PROMPT)
        self.assertEqual(arguments["temperature"], 0)
        self.assertEqual(arguments["seed"], 42)
        self.assertIn("1 screenshots", arguments["messages"][1]["content"][0]["text"])
        response.choices[0].message.content = "No verdict provided"
        with self.assertRaisesRegex(ValueError, "lacks"):
            evaluation.judge(client, self.args, "A attribute", trace)


if __name__ == "__main__":
    unittest.main()

