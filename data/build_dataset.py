"""Build the golden evaluation dataset.

Downloads the first 100 test samples from tweet_eval, adds 25 curated edge cases,
and saves the combined 125 samples to golden_dataset.json.
"""

import json
import os
from collections import Counter
from datasets import load_dataset

LABEL_MAP = {0: "negative", 1: "neutral", 2: "positive"}

def load_tweet_eval_samples(num_samples: int = 100):
    print(f"Loading tweet_eval sentiment dataset...")
    ds = load_dataset("cardiffnlp/tweet_eval", "sentiment", split="test")
    samples = []
    for i in range(min(num_samples, len(ds))):
        row = ds[i]
        text = row["text"]
        label = LABEL_MAP[row["label"]]
        difficulty = "hard" if len(text) > 80 else "easy"
        samples.append({
            "id": i,
            "text": text,
            "label": label,
            "expected_difficulty": difficulty,
            "edge_type": "standard"
        })
    return samples

def build_combined_dataset():
    # Load base tweet_eval samples (first 100)
    base = load_tweet_eval_samples(100)
    
    # Load edge cases
    script_dir = os.path.dirname(os.path.abspath(__file__))
    edge_cases_path = os.path.join(script_dir, "edge_cases.json")
    with open(edge_cases_path, "r", encoding="utf-8") as f:
        edge_cases = json.load(f)
    
    # Merge and save
    combined = base + edge_cases
    
    output_path = os.path.join(script_dir, "golden_dataset.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)
    
    # Print distribution report
    labels = Counter(r['label'] for r in combined)
    difficulties = Counter(r['expected_difficulty'] for r in combined)
    edge_types = Counter(r.get('edge_type', 'standard') for r in combined)
    
    print(f"Total cases: {len(combined)}")
    print(f"Label distribution: {dict(labels)}")
    print(f"Difficulty distribution: {dict(difficulties)}")
    print(f"Edge type distribution: {dict(edge_types)}")

if __name__ == "__main__":
    build_combined_dataset()
