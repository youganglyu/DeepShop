#!/bin/bash

echo "Running auto_eval_attribute.py..."
python src/data_process/auto_eval_attribute.py

echo "Running auto_eval_filter.py..."
python src/data_process/auto_eval_filter.py

echo "Running auto_eval_sort.py..."
python src/data_process/auto_eval_sort.py

echo "Running strict_rule_eval_overall.py..."
python src/data_process/strict_rule_eval_overall.py

echo "All evaluation scripts executed successfully."
