"""Regroup saved, non-provisional outcomes; no agent or judge is rerun.

Requires NumPy and SciPy. Prints two-sided, unadjusted paired t-tests and
pointwise 95% paired-t confidence intervals for the four included original runs.
"""
import itertools
import json
from pathlib import Path

import numpy as np
from scipy import stats

SOURCE = Path(__file__).with_name("original_task_results.json")


def summarize():
    data = json.loads(SOURCE.read_text())
    tasks, models = data["tasks"], data["models"]
    assert len(tasks) == len({t["id"] for t in tasks}) == 150
    values = {m: np.array([t["success"][m] for t in tasks]) for m in models}
    assert all(np.isin(v, [0, 1]).all() for v in values.values())
    result = {"n_tasks": len(tasks), "overall": {}, "groups": {}, "paired_tests": []}
    for m, v in values.items():
        result["overall"][m] = {"successes": int(v.sum()), "rate_percent": float(v.mean()*100)}
    for field, labels, expected_n in [
        ("category", ["Books", "Electronics", "Home", "Fashion", "Sports"], 30),
        ("difficulty", ["easy", "medium", "hard"], 50),
    ]:
        result["groups"][field] = {}
        for label in labels:
            mask = np.array([t[field] == label for t in tasks])
            assert int(mask.sum()) == expected_n
            result["groups"][field][label] = {
                "n": expected_n,
                "models": {m: {"successes": int(v[mask].sum()),
                                "rate_percent": float(v[mask].mean()*100)}
                           for m, v in values.items()},
            }
        for m in models:
            assert sum(result["groups"][field][g]["models"][m]["successes"]
                       for g in labels) == result["overall"][m]["successes"]
    # Orient each difference from higher to lower observed success rate.
    ranked = sorted(models, key=lambda m: values[m].sum(), reverse=True)
    for a, b in itertools.combinations(ranked, 2):
        diff = values[a] - values[b]
        se = float(stats.sem(diff))
        half_width = float(stats.t.ppf(.975, len(diff)-1))*se
        test = stats.ttest_rel(values[a], values[b])
        result["paired_tests"].append({
            "a": a, "b": b, "n": len(diff), "df": len(diff)-1,
            "difference_pp": float(diff.mean()*100),
            "t": float(test.statistic), "p_two_sided_unadjusted": float(test.pvalue),
            "pointwise_95_ci_pp": [float((diff.mean()-half_width)*100),
                                    float((diff.mean()+half_width)*100)],
        })
    return result


if __name__ == "__main__":
    print(json.dumps(summarize(), indent=2))
