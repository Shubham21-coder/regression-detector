"""Dataset loader for golden evaluation datasets."""

import json
from typing import List
from pydantic import BaseModel


class EvalSample(BaseModel):
    id: int
    text: str
    label: str
    expected_difficulty: str


def load_golden_dataset(path: str = "data/golden_dataset.json") -> List[EvalSample]:
    """Load the golden dataset from a JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [EvalSample(**item) for item in raw]


def dataset_summary(samples: List[EvalSample]) -> dict:
    """Return summary statistics for the dataset."""
    labels = {}
    difficulties = {}
    for s in samples:
        labels[s.label] = labels.get(s.label, 0) + 1
        difficulties[s.expected_difficulty] = difficulties.get(s.expected_difficulty, 0) + 1
    return {
        "total": len(samples),
        "label_distribution": labels,
        "difficulty_distribution": difficulties,
    }
