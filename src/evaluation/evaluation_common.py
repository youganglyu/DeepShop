"""Evaluate saved traces and join new results by task ID.

Dry runs and aggregation use only the standard library. Historical position-based
.npy outputs are never read or written by these entry points.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
DIMENSIONS = ("attribute", "filter", "sort")

# The released evaluation prompt is preserved verbatim.
SYSTEM_PROMPT = """As an evaluator, you will be presented with three primary components to assist you in your role:

1. Web Task Instruction: A clear and precise natural language directive that specifies an online shopping activity to be executed. The instruction may involve locating products that meet certain attribute requirements (e.g., color, size, brand), applying specific search filters (e.g., price range, customer ratings, availability), or fulfilling user-defined sorting preferences (e.g., lowest price, newest arrivals, best sellers). Tasks may also include verifying product details, comparing offers, or checking for shipping and return policies, depending on the scenario.

2. Result Screenshots: This is a visual representation of the screen showing the result or intermediate state of performing a web task. It serves as visual proof of the actions taken in response to the instruction.

3. Result Response: This is a textual response obtained after the execution of the web task. It serves as textual result in response to the instruction.

-- You DO NOT NEED to interact with web pages or perform actions such as booking flights or conducting searches on websites.
-- You SHOULD NOT make assumptions based on information not presented in the screenshot when comparing it to the instructions.
-- Your primary responsibility is to conduct a thorough assessment of the web task instruction against the outcome depicted in the screenshot and in the response, evaluating whether the actions taken align with the given instructions.
-- NOTE that the instruction may involve more than one task, for example, locating the garage and summarizing the review. Failing to complete either task, such as not providing a summary, should be considered unsuccessful.
-- NOTE that the screenshot is authentic, but the response provided by LLM is generated at the end of web browsing, and there may be discrepancies between the text and the screenshots.
-- Note the difference: 1) Result response may contradict the screenshot, then the content of the screenshot prevails, 2) The content in the Result response is not mentioned on the screenshot, choose to believe the content.

You should elaborate on how you arrived at your final evaluation and then provide a definitive verdict on whether the task has been successfully accomplished, either as 'SUCCESS' or 'NOT SUCCESS'."""


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Evaluate saved trajectories by task ID; no agent execution.")
    p.add_argument("--dataset", type=Path, default=ROOT / "data/deepshop_example.jsonl")
    p.add_argument("--run-name", "--test_name", dest="run_name", default="example")
    p.add_argument("--results-dir", "--process_dir", dest="results_dir", type=Path,
                   default=ROOT / "results", help="Contains <run-name>/task<ID>/ traces")
    p.add_argument("--output-dir", type=Path,
                   help="New JSON results; default: results-dir/evaluations/run-name")
    p.add_argument("--api-model", "--api_model", dest="api_model", default="gpt-4o")
    p.add_argument("--max-attached-imgs", "--max_attached_imgs", dest="max_attached_imgs",
                   type=int, default=15)
    p.add_argument("--dry-run", action="store_true",
                   help="Validate local inputs without API calls or writing result files")
    args = p.parse_args(argv)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", args.run_name):
        p.error("run-name must be a single safe directory name")
    if args.max_attached_imgs < 1:
        p.error("max-attached-imgs must be positive")
    if args.output_dir is None:
        args.output_dir = args.results_dir / "evaluations" / args.run_name
    return args


def applicable(value):
    return value is not None and value.strip() not in ("", "None")


def load_dataset(path):
    tasks, seen = [], set()
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            task = json.loads(line)
        except json.JSONDecodeError:
            raise ValueError(f"Invalid dataset JSON at line {lineno}") from None
        if not isinstance(task, dict):
            raise ValueError(f"Dataset line {lineno} must be an object")
        task_id = task.get("id")
        if not isinstance(task_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", task_id):
            raise ValueError(f"Invalid task ID at line {lineno}")
        if task_id in seen:
            raise ValueError(f"Duplicate task ID: {task_id}")
        for dim in DIMENSIONS:
            if dim not in task or (task[dim] is not None and not isinstance(task[dim], str)):
                raise ValueError(f"Task {task_id}: {dim} must be a string or null")
        seen.add(task_id)
        tasks.append(task)
    if not tasks:
        raise ValueError("Dataset is empty")
    return tasks


def content_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(part["text"] for part in content
                         if isinstance(part, dict) and isinstance(part.get("text"), str))
    raise ValueError("Trace content must be text or a content-block list")


def load_trace(args, task):
    directory = args.results_dir / args.run_name / ("task" + task["id"])
    path = directory / "interact_messages.json"
    if not path.is_file():
        raise ValueError(f"Missing trajectory: {path}")
    try:
        messages = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raise ValueError(f"Invalid trajectory JSON for {task['id']}") from None
    if not isinstance(messages, list) or not messages:
        raise ValueError(f"Empty or invalid trajectory for {task['id']}")
    if any(not isinstance(m, dict) or "content" not in m for m in messages):
        raise ValueError(f"Invalid trajectory message for {task['id']}")
    final = content_text(messages[-1]["content"])
    match = re.search(r"Action:\s*ANSWER[;\s]+(.+)", final, flags=re.DOTALL)
    answer = match.group(1).strip().strip("[]").strip() if match else None
    screenshots = sorted(
        (p for p in directory.iterdir() if re.fullmatch(r"screenshot\d+\.png", p.name)),
        key=lambda p: int(re.search(r"\d+", p.stem).group()),
    )[-args.max_attached_imgs:]
    if answer and not screenshots:
        raise ValueError(f"No screenshots for answered task {task['id']}")
    for image in screenshots:
        with image.open("rb") as stream:
            if stream.read(8) != b"\x89PNG\r\n\x1a\n":
                raise ValueError(f"Invalid PNG screenshot for {task['id']}: {image.name}")
    return {"answer": answer, "screenshots": screenshots}


def validate_inputs(args):
    tasks = load_dataset(args.dataset)
    return tasks, {t["id"]: load_trace(args, t) for t in tasks}


def dry_run(args, tasks, traces):
    print(json.dumps({
        "status": "dry-run", "run_name": args.run_name,
        "dataset": str(args.dataset.resolve()), "tasks": len(tasks),
        "applicable_tasks": {d: sum(applicable(t[d]) for t in tasks) for d in DIMENSIONS},
        "trajectories": len(traces),
        "with_final_answer": sum(bool(t["answer"]) for t in traces.values()),
        "attached_screenshots": sum(len(t["screenshots"]) for t in traces.values()),
        "api_calls": 0, "writes_results": False,
    }, indent=2))


def metadata(args):
    return {"schema_version": 1, "run_name": args.run_name,
            "dataset_sha256": hashlib.sha256(args.dataset.read_bytes()).hexdigest()}


def save_new(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents replacing previous evaluations.
    with path.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def create_client():
    # Lazy imports keep validation and saved-result aggregation API-free.
    from dotenv import load_dotenv
    from openai import OpenAI
    load_dotenv(ROOT / ".env", override=False)
    if not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("Set OPENAI_API_KEY in the environment or repository .env")
    return OpenAI(api_key=os.environ["OPENAI_API_KEY"],
                  base_url=os.environ.get("OPENAI_BASE_URL") or None,
                  timeout=90.0, max_retries=2)


def judge(client, args, subquery, trace):
    images = [{"type": "image_url", "image_url": {"url": "data:image/png;base64," +
               base64.b64encode(p.read_bytes()).decode("ascii")}}
              for p in trace["screenshots"]]
    prompt = (f"TASK: {subquery}\nResult Response: {trace['answer']}\n"
              f"{len(images)} screenshots at the end: ")
    response = client.chat.completions.create(
        model=args.api_model, max_tokens=1000, seed=42, temperature=0,
        messages=[{"role": "system", "content": SYSTEM_PROMPT},
                  {"role": "user", "content": [{"type": "text", "text": prompt}]
                   + images + [{"type": "text", "text": "Your verdict:\n"}]}],
    )
    verdict = response.choices[0].message.content
    if not isinstance(verdict, str) or "SUCCESS" not in verdict:
        raise ValueError("Judge response lacks a SUCCESS/NOT SUCCESS verdict")
    # Preserve the released evaluator's binary verdict convention.
    return (0 if "NOT SUCCESS" in verdict else 1), verdict, getattr(response, "model", None)


def evaluate_dimension(args, dimension):
    tasks, traces = validate_inputs(args)
    if args.dry_run:
        dry_run(args, tasks, traces)
        return
    output = args.output_dir / (dimension + ".json")
    if output.exists():
        raise ValueError(f"Output exists; select a new --output-dir: {output}")
    records, client = [], None
    for task in tasks:
        record = {"id": task["id"], "applicable": applicable(task[dimension]), "success": None}
        trace = traces[task["id"]]
        if record["applicable"]:
            if not trace["answer"]:
                record.update(success=0, reason="no_final_answer")
            else:
                if client is None:
                    client = create_client()
                score, verdict, response_model = judge(client, args, task[dimension], trace)
                record.update(success=score, judge_response=verdict, response_model=response_model)
        records.append(record)
    scores = [r["success"] for r in records if r["applicable"]]
    summary = {"n_applicable": len(scores), "successes": sum(scores),
               "rate_percent": 100 * sum(scores) / len(scores) if scores else None}
    payload = dict(metadata(args), dimension=dimension,
                   judge={"requested_model": args.api_model, "temperature": 0, "seed": 42,
                          "max_attached_imgs": args.max_attached_imgs},
                   tasks=records, summary=summary)
    save_new(output, payload)
    print(json.dumps({"dimension": dimension, "output": str(output), **summary}))


def aggregate(args):
    if args.dry_run:
        tasks, traces = validate_inputs(args)
        dry_run(args, tasks, traces)
        return
    tasks = load_dataset(args.dataset)
    expected = {t["id"]: t for t in tasks}
    provenance = metadata(args)
    by_dimension = {}
    reference_judge = None
    judge_keys = ("requested_model", "temperature", "seed", "max_attached_imgs")
    for dimension in DIMENSIONS:
        path = args.output_dir / (dimension + ".json")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if any(payload.get(k) != v for k, v in provenance.items()) or payload.get("dimension") != dimension:
            raise ValueError(f"Dataset/run/dimension mismatch in {path}")
        configuration = payload.get("judge")
        if not isinstance(configuration, dict) or any(k not in configuration for k in judge_keys):
            raise ValueError(f"Missing judge configuration in {path}")
        configuration = {k: configuration[k] for k in judge_keys}
        if reference_judge is None:
            reference_judge = configuration
        elif configuration != reference_judge:
            raise ValueError(f"Judge configuration mismatch in {path}")
        records = payload.get("tasks")
        if not isinstance(records, list):
            raise ValueError(f"Missing task records in {path}")
        indexed = {}
        for record in records:
            if not isinstance(record, dict) or record.get("id") not in expected:
                raise ValueError(f"Unexpected task in {path}")
            task_id = record["id"]
            if task_id in indexed:
                raise ValueError(f"Duplicate task ID in {path}: {task_id}")
            is_applicable = applicable(expected[task_id][dimension])
            score = record.get("success")
            if record.get("applicable") is not is_applicable:
                raise ValueError(f"Applicability mismatch for {task_id}/{dimension}")
            if (is_applicable and (type(score) is not int or score not in (0, 1))) or (not is_applicable and score is not None):
                raise ValueError(f"Invalid score for {task_id}/{dimension}")
            indexed[task_id] = score
        if set(indexed) != set(expected):
            raise ValueError(f"Missing task IDs in {path}")
        by_dimension[dimension] = indexed
    records = [{"id": t["id"], "success": int(all(
        by_dimension[d][t["id"]] in (None, 1) for d in DIMENSIONS))} for t in tasks]
    successes = sum(r["success"] for r in records)
    summary = {"n_tasks": len(tasks), "successes": successes,
               "rate_percent": 100 * successes / len(tasks)}
    output = args.output_dir / "overall.json"
    save_new(output, dict(provenance, dimension="overall", judge=reference_judge,
                          tasks=records, summary=summary))
    print(json.dumps({"dimension": "overall", "output": str(output), **summary}))


def main(dimension, argv=None):
    args = parse_args(argv)
    try:
        if dimension == "all":
            if args.dry_run:
                tasks, traces = validate_inputs(args)
                dry_run(args, tasks, traces)
                return 0
            for dim in (*DIMENSIONS, "overall"):
                if (args.output_dir / (dim + ".json")).exists():
                    raise ValueError(f"Output exists; select a new --output-dir: {args.output_dir}")
            for dim in DIMENSIONS:
                evaluate_dimension(args, dim)
            aggregate(args)
        elif dimension == "overall":
            aggregate(args)
        else:
            evaluate_dimension(args, dimension)
        return 0
    except (ValueError, OSError) as exc:
        print(f"Evaluation failed: {exc}", file=sys.stderr)
    except Exception as exc:
        # SDK errors can include endpoint/request details; never echo credentials.
        print(f"Evaluation failed ({type(exc).__name__}); no complete result was saved.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main("all"))

