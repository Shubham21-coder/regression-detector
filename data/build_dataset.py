"""Build the golden evaluation dataset from tweet_eval.

Downloads the first 100 test samples from the tweet_eval sentiment dataset,
maps integer labels to strings, tags difficulty, and saves as JSON.
"""

import json
import os
from collections import Counter
from datasets import load_dataset


LABEL_MAP = {0: "negative", 1: "neutral", 2: "positive"}


def build_dataset(num_samples: int = 100, output_path: str = None):
    """Build and save the golden dataset."""
    if output_path is None:
        # Compute path relative to this script's location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(script_dir, "golden_dataset.json")

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
        })

    # Save to JSON
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(samples, f, indent=2, ensure_ascii=False)

    # Print summary
    label_counts = Counter(s["label"] for s in samples)
    print(
        f"Saved {len(samples)} samples. "
        f"Label distribution: "
        f"positive={label_counts.get('positive', 0)}, "
        f"negative={label_counts.get('negative', 0)}, "
        f"neutral={label_counts.get('neutral', 0)}"
    )
    print(f"Output: {output_path}")

    return samples


if __name__ == "__main__":
    build_dataset()
