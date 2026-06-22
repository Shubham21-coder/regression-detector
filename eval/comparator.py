"""Regression comparator — compares current run against baseline."""


WARN_THRESHOLD = -0.03
CRITICAL_THRESHOLD = -0.08
VOCAB_MISMATCH_CRITICAL = 0.5

def compare_runs(
    current_scores: dict,
    baseline_scores: dict,
    current_results: list,
    baseline_results: list,
) -> dict:
    """Compare current eval run against baseline and detect regressions."""

    # Build lookup dicts for regression case detection
    baseline_by_id = {r["id"]: r for r in baseline_results}
    current_by_id = {r["id"]: r for r in current_results}

    # Overall accuracy delta
    acc_delta = current_scores["overall_accuracy"] - baseline_scores["overall_accuracy"]

    # Status thresholds
    if acc_delta >= 0:
        status = "pass"
    elif acc_delta > WARN_THRESHOLD:
        status = "warn"
    elif acc_delta > CRITICAL_THRESHOLD:
        status = "warn"  # Fallback just in case, though logically it's between -0.03 and -0.08
    else:
        status = "critical"

    # Per-class deltas
    per_class_deltas = {}
    for label in ["positive", "negative", "neutral"]:
        curr = current_scores["per_class_accuracy"].get(label, 0)
        base = baseline_scores["per_class_accuracy"].get(label, 0)
        per_class_deltas[label] = round(curr - base, 4)

    # Regressed cases: baseline correct, current wrong
    regressed_cases = []
    for case_id, base_r in baseline_by_id.items():
        curr_r = current_by_id.get(case_id)
        if curr_r and base_r.get("correct") and not curr_r.get("correct"):
            regressed_cases.append({
                "id": case_id,
                "text": base_r["text"][:80] + "..." if len(base_r["text"]) > 80 else base_r["text"],
                "true_label": base_r["true_label"],
                "baseline_predicted": base_r["predicted_label"],
                "current_predicted": curr_r["predicted_label"],
                "difficulty": base_r["difficulty"],
            })

    # Improved cases: baseline wrong, current correct
    improved_cases_count = sum(
        1 for cid, curr_r in current_by_id.items()
        if baseline_by_id.get(cid)
        and not baseline_by_id[cid].get("correct")
        and curr_r.get("correct")
    )

    # Vocabulary mismatch override
    vocab_mismatch = current_scores.get("vocabulary_mismatch_rate", 0.0)
    failure_reason = None
    if vocab_mismatch > VOCAB_MISMATCH_CRITICAL:
        status = "critical"
        failure_reason = "vocabulary_mismatch"

    result = {
        "status": status,
        "current_version": current_scores["version_id"],
        "baseline_version": baseline_scores["version_id"],
        "overall_accuracy_delta": round(acc_delta, 4),
        "per_class_deltas": per_class_deltas,
        "latency_delta_ms": round(
            current_scores["avg_latency_ms"] - baseline_scores["avg_latency_ms"], 1
        ),
        "regressed_cases": regressed_cases,
        "regressed_count": len(regressed_cases),
        "improved_count": improved_cases_count,
        "current_accuracy": current_scores["overall_accuracy"],
        "baseline_accuracy": baseline_scores["overall_accuracy"],
        "vocabulary_mismatch_rate": vocab_mismatch,
        "judge_score_delta": round(
            current_scores.get('avg_judge_score', 0) - 
            baseline_scores.get('avg_judge_score', 0), 3
        ) if current_scores.get('avg_judge_score') and baseline_scores.get('avg_judge_score') else None,
        "failure_rate_delta": round(
            current_scores.get('failure_rate', 0) -
            baseline_scores.get('failure_rate', 0), 4
        ),
    }

    if failure_reason:
        result["failure_reason"] = failure_reason

    return result

