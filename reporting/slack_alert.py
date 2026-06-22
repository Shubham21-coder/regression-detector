"""Slack alerting — webhook with stdout fallback. Only alerts on warn/critical."""

import os
import requests


def send_slack_alert(comparison: dict, report_path: str):
    """Send Slack alert on regression. No alert on pass."""
    status = comparison["status"]
    if status == "pass":
        return  # no alert on pass

    emoji = "\U0001f534" if status == "critical" else "\U0001f7e1"
    delta_pct = comparison["overall_accuracy_delta"] * 100
    sign = "+" if delta_pct >= 0 else ""

    text = (
        f"{emoji} *[CT1 Eval]* {status.upper()} regression detected\n"
        f"Version: {comparison['current_version']} vs baseline {comparison['baseline_version']}\n"
        f"Accuracy delta: {sign}{delta_pct:.1f}% "
        f"(was {comparison['baseline_accuracy']:.1%}, now {comparison['current_accuracy']:.1%})\n"
        f"Regressed cases: {comparison['regressed_count']}\n"
        f"Report: {report_path}"
    )

    webhook = os.getenv("SLACK_WEBHOOK_URL", "")
    if webhook:
        try:
            requests.post(webhook, json={"text": text}, timeout=5)
        except Exception as e:
            print(f"Slack post failed: {e}")
    else:
        print("\n-- SLACK ALERT (stdout fallback) --")
        print(text)
        print("------------------------------------\n")
