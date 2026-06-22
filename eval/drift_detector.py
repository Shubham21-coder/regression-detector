import json, sqlite3
from datetime import datetime, timezone
from storage.db import get_run_history

DRIFT_WARN_THRESHOLD = -0.02
DRIFT_CRITICAL_THRESHOLD = -0.05
DRIFT_WINDOW_SIZE = 5

def compute_rolling_stats(db_path: str = "storage/runs.db",
                           window: int = DRIFT_WINDOW_SIZE) -> dict:
    """
    Compute rolling statistics over the last `window` runs.
    Returns drift analysis including trend direction and alert status.
    """
    con = sqlite3.connect(db_path)
    rows = con.execute(
        """SELECT run_id, version_id, timestamp, scores_json
           FROM runs ORDER BY timestamp DESC LIMIT ?""",
        (window * 2,)   # fetch double to have room for windowing
    ).fetchall()
    con.close()
    
    if len(rows) < 2:
        return {"status": "insufficient_data", "runs_available": len(rows)}
    
    # Parse scores
    runs = []
    for run_id, version_id, timestamp, scores_json in rows:
        try:
            scores = json.loads(scores_json)
            runs.append({
                "run_id": run_id,
                "version_id": version_id,
                "timestamp": timestamp,
                "overall_accuracy": scores.get("overall_accuracy", 0),
                "avg_judge_score": scores.get("avg_judge_score"),
                "failure_rate": scores.get("failure_rate", 0),
            })
        except Exception:
            continue
    
    if len(runs) < 2:
        return {"status": "insufficient_data", "runs_available": len(runs)}
    
    # Split into current window vs previous window
    current_window = runs[:window]
    current_window.reverse()  # Time flows forward: index 0 is oldest, N-1 is newest
    prev_window    = runs[window:window*2] if len(runs) > window else []
    
    # Rolling averages
    def avg(lst, key):
        vals = [r[key] for r in lst if r.get(key) is not None]
        return sum(vals) / len(vals) if vals else None
    
    current_avg_acc   = avg(current_window, "overall_accuracy")
    prev_avg_acc      = avg(prev_window, "overall_accuracy") if prev_window else None
    current_avg_judge = avg(current_window, "avg_judge_score")
    prev_avg_judge    = avg(prev_window, "avg_judge_score") if prev_window else None
    
    # Trend: linear slope over current window accuracies
    accs = [r["overall_accuracy"] for r in current_window]
    n = len(accs)
    if n >= 3:
        # Simple linear regression slope
        xs = list(range(n))
        x_mean = sum(xs) / n
        y_mean = sum(accs) / n
        numerator   = sum((xs[i] - x_mean) * (accs[i] - y_mean) for i in range(n))
        denominator = sum((xs[i] - x_mean) ** 2 for i in range(n))
        slope = numerator / denominator if denominator != 0 else 0.0
    else:
        slope = accs[-1] - accs[0] if len(accs) >= 2 else 0.0
    
    # Drift detection thresholds
    # slope is per-run change. Over 5 runs, cumulative = slope * 5
    cumulative_drift = slope * n
    
    drift_status = "stable"
    if cumulative_drift < DRIFT_CRITICAL_THRESHOLD:   # >5% cumulative drop over window
        drift_status = "drift_critical"
    elif cumulative_drift < DRIFT_WARN_THRESHOLD: # >2% cumulative drop
        drift_status = "drift_warn"
    elif cumulative_drift > 0.03:  # improving trend
        drift_status = "improving"
    
    # Window delta (current avg vs previous window avg)
    window_delta = None
    if prev_avg_acc is not None and current_avg_acc is not None:
        window_delta = current_avg_acc - prev_avg_acc
    
    return {
        "status": drift_status,
        "window_size": window,
        "runs_analyzed": len(runs),
        "current_window_avg_accuracy": round(current_avg_acc, 4) if current_avg_acc else None,
        "previous_window_avg_accuracy": round(prev_avg_acc, 4) if prev_avg_acc else None,
        "window_delta": round(window_delta, 4) if window_delta is not None else None,
        "current_window_avg_judge": round(current_avg_judge, 3) if current_avg_judge else None,
        "accuracy_slope_per_run": round(slope, 4),
        "cumulative_drift_over_window": round(cumulative_drift, 4),
        "run_accuracies": [round(r["overall_accuracy"], 4) for r in current_window],
        "trend_direction": "declining" if slope < -0.001 else ("improving" if slope > 0.001 else "stable"),
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }

def format_drift_alert(drift: dict) -> str:
    """Format drift results as a human-readable alert string."""
    if drift["status"] == "insufficient_data":
        return f"[DRIFT] Insufficient data ({drift.get('runs_available',0)} runs, need 2+)"
    
    status_icons = {
        "stable": "✓",
        "improving": "↑",
        "drift_warn": "⚠",
        "drift_critical": "🔴"
    }
    icon = status_icons.get(drift["status"], "?")
    
    parts = [
        f"[DRIFT {icon}] {drift['status'].upper()}",
        f"window={drift['window_size']}",
        f"avg={drift['current_window_avg_accuracy']:.1%}" if drift.get('current_window_avg_accuracy') else "",
        f"slope={drift['accuracy_slope_per_run']:+.3f}/run",
        f"cumulative={drift['cumulative_drift_over_window']:+.1%}",
    ]
    if drift.get('window_delta') is not None:
        parts.append(f"vs_prev_window={drift['window_delta']:+.1%}")
    
    return " | ".join(p for p in parts if p)
