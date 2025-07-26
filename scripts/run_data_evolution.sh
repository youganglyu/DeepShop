#!/bin/bash

echo "Running query_evolution.py..."
python ../src/data_process/query_evolution.py

echo "Running break_subquery.py..."
python ../src/data_process/break_subquery.py

echo "Running filter_data.py..."
python ../src/data_process/filter_data.py

echo "All scripts executed successfully."}
