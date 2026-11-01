#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo_dir"
python_bin=${PYTHON:-python3}

echo "Running query_evolution.py..."
"$python_bin" ./src/data_process/query_evolution.py

echo "Running break_subquery.py..."
"$python_bin" ./src/data_process/break_subquery.py

echo "Running filter_data.py..."
"$python_bin" ./src/data_process/filter_data.py

echo "All construction stages completed."
