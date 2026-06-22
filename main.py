"""CT1 Model Regression Detection System — Main Entry Point.

Usage:
    python main.py --yaml prompts/v1.yaml --set-baseline
    python main.py --yaml prompts/v2.yaml --dataset data/golden_dataset.json
"""

import asyncio
import sys
import io

# Fix Windows console encoding for emoji/unicode
if sys.stdout.encoding and sys.stdout.encoding.lower().startswith('cp'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import argparse
import json
import uuid
import sys
import os

from eval.runner import run_all
from eval.scorer import score_run
from eval.comparator import compare_runs
from storage.db import init_db, save_run, get_baseline, mark_as_baseline, get_run_history
from reporting.html_report import generate_report
from reporting.slack_alert import send_slack_alert
from dotenv import load_dotenv

load_dotenv(override=True)


def main():
    parser = argparse.ArgumentParser(
        description="CT1 Model Regression Detection System"
    )
    parser.add_argument("--yaml", required=True, help="Path to prompt YAML")
    parser.add_argument("--dataset", default="data/golden_dataset.json")
    parser.add_argument(
        "--set-baseline", action="store_true",
        help="Mark this run as the new baseline after running",
    )
    parser.add_argument("--concurrency", type=int, default=3)
    args = parser.parse_args()

    # Init DB
    os.makedirs("storage", exist_ok=True)
    init_db()

    # Run eval
    print(f"\n{'='*60}")
    print(f"🔍 CT1 Model Regression Detection System")
    print(f"{'='*60}")
    print(f"  Prompt: {args.yaml}")
    print(f"  Dataset: {args.dataset}")
    print(f"  Concurrency: {args.concurrency}")
    print(f"{'='*60}\n")

    results = asyncio.run(run_all(args.yaml, args.dataset, args.concurrency))
    scores = score_run(results)
    run_id = str(uuid.uuid4())[:8]

    # Save to DB
    save_run(run_id, scores["version_id"], scores, results)
    print(f"\n💾 Saved run {run_id} | accuracy: {scores['overall_accuracy']:.1%}")

    # Compare vs baseline
    baseline_scores, baseline_results = get_baseline()
    if baseline_scores is None or baseline_scores["version_id"] == scores["version_id"]:
        # First run or same version — just set as baseline
        mark_as_baseline(run_id)
        print(f"No prior baseline found. This run ({scores['version_id']}) is now the baseline.")
        print(
            f"\nRESULT: BASELINE SET | accuracy {scores['overall_accuracy']:.1%} "
            f"| run_id {run_id}"
        )
        sys.exit(0)

    comparison = compare_runs(scores, baseline_scores, results, baseline_results)
    history = get_run_history()

    # Generate report
    os.makedirs("reports", exist_ok=True)
    report_path = f"reports/report_{run_id}.html"
    generate_report(scores, comparison, results, history, report_path)
    print(f"📊 Report saved: {report_path}")

    # Slack alert (stdout fallback if no webhook)
    send_slack_alert(comparison, report_path)

    # One-line summary
    delta_pct = comparison["overall_accuracy_delta"] * 100
    sign = "+" if delta_pct >= 0 else ""
    failure_str = f" | {comparison['failure_reason']}" if "failure_reason" in comparison else ""
    
    print(
        f"\nRESULT: {comparison['status'].upper()} | "
        f"{scores['version_id']} vs {baseline_scores['version_id']} | "
        f"accuracy {sign}{delta_pct:.1f}%{failure_str} | "
        f"{comparison['regressed_count']} regressed cases | "
        f"avg latency {scores['avg_latency_ms']:.0f}ms"
    )

    # Exit codes for CI
    exit_codes = {"pass": 0, "warn": 1, "critical": 2}
    sys.exit(exit_codes[comparison["status"]])


if __name__ == "__main__":
    main()
