"""Multi-dimension scorer for evaluation results."""

import statistics
import json
from datetime import datetime, timezone


def score_run(results: list) -> dict:
    """Generate a comprehensive scorecard from evaluation results.

    Computes overall accuracy, per-class accuracy, per-difficulty accuracy,
    latency stats, token usage, and error counts.
    """
    # Filter out error results for accuracy calculations
    valid_results = [r for r in results if r["predicted_label"] != "error"]

    # --- Overall accuracy ---
    overall_accuracy = (
        sum(r["correct"] for r in valid_results) / len(valid_results)
        if valid_results else 0.0
    )

    # --- Per-class accuracy ---
    per_class_accuracy = {}
    for label in ["positive", "negative", "neutral"]:
        cases = [r for r in valid_results if r["true_label"] == label]
        per_class_accuracy[label] = (
            sum(r["correct"] for r in cases) / len(cases)
            if cases else 0.0
        )

    # --- Per-difficulty accuracy ---
    per_difficulty_accuracy = {}
    for difficulty in ["easy", "hard"]:
        cases = [r for r in valid_results if r["difficulty"] == difficulty]
        per_difficulty_accuracy[difficulty] = (
            sum(r["correct"] for r in cases) / len(cases)
            if cases else 0.0
        )

    # --- Latency statistics ---
    latencies = [r["latency_ms"] for r in valid_results if r["latency_ms"] > 0]
    if latencies:
        avg_latency_ms = statistics.mean(latencies)
        sorted_latencies = sorted(latencies)
        p95_latency_ms = sorted_latencies[int(len(sorted_latencies) * 0.95)]
    else:
        avg_latency_ms = 0.0
        p95_latency_ms = 0.0

    # --- Token usage ---
    total_prompt_tokens = sum(r["prompt_tokens"] for r in valid_results)
    total_completion_tokens = sum(r["completion_tokens"] for r in valid_results)

    # --- Error count ---
    error_count = len([r for r in results if r["predicted_label"] == "error"])

    # --- Vocabulary mismatch ---
    expected_vocab = {"positive", "negative", "neutral"}
    mismatch_count = sum(
        1 for r in valid_results
        if r["predicted_label"] not in expected_vocab
    )
    vocabulary_mismatch_rate = (
        round(mismatch_count / len(valid_results), 4)
        if valid_results else 0.0
    )

    return {
        "overall_accuracy": round(overall_accuracy, 4),
        "per_class_accuracy": {k: round(v, 4) for k, v in per_class_accuracy.items()},
        "per_difficulty_accuracy": {k: round(v, 4) for k, v in per_difficulty_accuracy.items()},
        "avg_latency_ms": round(avg_latency_ms, 1),
        "p95_latency_ms": round(p95_latency_ms, 1),
        "total_prompt_tokens": total_prompt_tokens,
        "total_completion_tokens": total_completion_tokens,
        "estimated_cost_usd": 0.0,  # Local model, no API cost
        "error_count": error_count,
        "vocabulary_mismatch_rate": vocabulary_mismatch_rate,
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
        "num_cases": len(results),
        "version_id": results[0]["version_id"] if results else "unknown",
        "backend": results[0].get("backend", "unknown") if results else "unknown",
        "model_name": results[0].get("model_name", "unknown") if results else "unknown",
    }

