import json
import re
import random
from collections import defaultdict

# ---------------------------
# Step 1. Read and process the JSONL file.
# ---------------------------
samples=[]
with open('../../data/deepshop_evol_600_subquery.jsonl', 'r', encoding="utf-8") as f:
    for line in f:
        temp = json.loads(line)
        samples.append(temp)

# ---------------------------
# Step 2. Group samples by domain (using "category").
# ---------------------------
domain_samples = defaultdict(list)
for s in samples:
    domain = s.get("category")
    if domain:
        domain_samples[domain].append(s)

if len(domain_samples) < 5:
    raise ValueError("Not enough distinct domains in the dataset.")

# Select exactly 5 domains (modify the selection as needed).
domains = list(domain_samples.keys())[:5]

# For each chosen domain, group the samples by difficulty.
domain_diff_samples = {}
for d in domains:
    domain_diff_samples[d] = defaultdict(list)
    for s in domain_samples[d]:
        diff = s["difficulty"]
        domain_diff_samples[d][diff].append(s)

# ---------------------------
# Step 3. For each domain, select 10 easy, 10 medium, and 10 hard samples.
# ---------------------------
final_samples = []
for d in domains:
    for diff in ["easy", "medium", "hard"]:
        if len(domain_diff_samples[d][diff]) < 10:
            raise ValueError(f"Not enough samples for domain '{d}' with difficulty '{diff}'.")
    chosen_easy = random.sample(domain_diff_samples[d]["easy"], 10)
    chosen_medium = random.sample(domain_diff_samples[d]["medium"], 10)
    chosen_hard = random.sample(domain_diff_samples[d]["hard"], 10)
    final_samples.extend(chosen_easy)
    final_samples.extend(chosen_medium)
    final_samples.extend(chosen_hard)
    print(f"Domain '{d}': selected 10 easy, 10 medium, and 10 hard samples.")

print(f"\nTotal samples selected: {len(final_samples)} (should be 150)")

# ---------------------------
# Step 4. Write the selected samples to a new JSONL file.
# ---------------------------
output_filename = "deepshop_filterd_150.jsonl"
with open(output_filename, "w") as f_out:
    for sample in final_samples:
        f_out.write(json.dumps(sample) + "\n")

print(f"Filtered samples written to {output_filename}")