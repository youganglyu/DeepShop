# ECIR 2027 original-run analysis

`original_task_results.json` contains saved task-success labels for Simple RAG, Agent-E, SeeAct, and Browser Use on the published 150 tasks, with task IDs, categories, difficulty labels, and source-array hashes. Grouping these labels reproduces the corresponding main-table totals and both Figure 3 panels. These files regroup existing judgments; they do not rerun agents or judges.

With NumPy and SciPy installed:

```sh
python recompute_result_statistics.py
```

The script reports overall and grouped success counts and six two-sided paired t-tests. P-values are unadjusted; confidence intervals are pointwise 95% paired-t intervals in percentage points. `original_run_statistics.json` is its saved output. The included records cover only the four listed original runs.
