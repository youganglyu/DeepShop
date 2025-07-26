#!/bin/bash

echo "Running auto_eval_attribute.py..."
python ./src/evaluation/auto_eval_attribute.py --test_name example

echo "Running auto_eval_filter.py..."
python ./src/evaluation/auto_eval_filter.py --test_name example

echo "Running auto_eval_sort.py..."
python ./src/evaluation/auto_eval_sort.py --test_name example

echo "Running strict_rule_eval_overall.py..."
python ./src/evaluation/strict_rule_eval_overall.py

echo "All evaluation scripts executed successfully."
