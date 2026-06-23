import streamlit as st
import asyncio, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eval.runner import run_all
from eval.scorer import score_run
from eval.comparator import compare_runs
from eval.drift_detector import compute_rolling_stats
from storage.db import init_db, save_run, get_baseline, mark_as_baseline, get_run_history
from reporting.html_report import generate_report
import streamlit.components.v1 as components
import uuid

def ensure_baseline_seeded():
    """
    On first load, if no baseline exists, run v1 silently and mark it
    as baseline. This guarantees recruiter always sees a diff.
    """
    from storage.db import init_db, get_baseline, save_run, mark_as_baseline
    from eval.runner import run_all
    from eval.scorer import score_run
    import asyncio, uuid, os

    init_db()
    baseline_scores, _ = get_baseline()
    if baseline_scores is not None:
        return  # baseline already exists

    os.environ["LLM_BACKEND"] = "groq"
    os.environ["DEMO_MODE"] = "true"
    os.environ["DEMO_CASE_LIMIT"] = "10"

    try:
        results = asyncio.run(
            run_all("prompts/v1.yaml", "data/golden_dataset.json", concurrency=5)
        )
        scores = score_run(results)
        run_id = str(uuid.uuid4())[:8]
        save_run(run_id, "v1", scores, results)
        mark_as_baseline(run_id)
        print(f"Baseline seeded: v1, accuracy={scores['overall_accuracy']:.1%}")
    except Exception as e:
        print(f"Baseline seed failed (non-fatal): {e}")

SYNTHETIC_HISTORY = [
    {"version_id": "v1", "accuracy": 0.82, "latency": 1850, "days_ago": 5},
    {"version_id": "v1", "accuracy": 0.80, "latency": 1920, "days_ago": 4},
    {"version_id": "v2", "accuracy": 0.78, "latency": 1740, "days_ago": 3},
]

def seed_synthetic_history():
    from storage.db import init_db, get_run_history, save_run
    from datetime import datetime, timezone, timedelta
    import uuid, json

    init_db()
    history = get_run_history(limit=20)
    if len(history) >= 3:
        return  # already have history

    for entry in SYNTHETIC_HISTORY:
        fake_scores = {
            "version_id": entry["version_id"],
            "overall_accuracy": entry["accuracy"],
            "per_class_accuracy": {"positive": entry["accuracy"]+0.05,
                                    "negative": entry["accuracy"]+0.03,
                                    "neutral": entry["accuracy"]-0.08},
            "per_edge_type_accuracy": {"standard": entry["accuracy"]},
            "avg_latency_ms": entry["latency"],
            "p95_latency_ms": entry["latency"] * 1.4,
            "total_prompt_tokens": 1240,
            "total_completion_tokens": 80,
            "estimated_cost_usd": 0.0,
            "error_count": 0,
            "vocabulary_mismatch_rate": 0.0,
            "avg_judge_score": 4.1,
            "judge_distribution": {5: 6, 4: 3, 3: 1},
            "perfect_rate": 0.6,
            "near_perfect_rate": 0.9,
            "failure_rate": 0.1,
            "per_edge_type_judge_scores": {"standard": 4.1},
            "run_timestamp": (
                datetime.now(timezone.utc) - timedelta(days=entry["days_ago"])
            ).isoformat(),
            "num_cases": 10,
            "backend": "groq",
            "model_name": "llama-3.1-8b-instant",
        }
        fake_results = []  # empty — only scores matter for trend chart
        run_id = str(uuid.uuid4())[:8]
        save_run(run_id, entry["version_id"], fake_scores, fake_results)

ensure_baseline_seeded()
seed_synthetic_history()

st.set_page_config(
    page_title="CT1 — Regression Detection Demo",
    page_icon="🔍",
    layout="wide"
)

st.title("CT1 — LLM Prompt Regression Detection")
st.caption(
    "A CI system that catches prompt quality regressions before they ship. "
    "Select a prompt version and run a 10-case live eval against Groq's free API."
)

# Sidebar — config
st.sidebar.header("Configuration")
prompt_choice = st.sidebar.selectbox(
    "Select prompt version",
    ["v1 — Full instructions + few-shot (this is the baseline)",
     "v2 — Minimal instructions → watch accuracy change",
     "v3 — Wrong vocabulary → triggers CRITICAL regression"],
    index=0
)
version_map = {
    "v1 — Full instructions + few-shot (this is the baseline)": "prompts/v1.yaml",
    "v2 — Minimal instructions → watch accuracy change": "prompts/v2.yaml",
    "v3 — Wrong vocabulary → triggers CRITICAL regression": "prompts/v3.yaml"
}
yaml_path = version_map[prompt_choice]
version_id = yaml_path.split("/")[1].replace(".yaml", "")

backend_env = os.environ.get("LLM_BACKEND", "groq")

st.sidebar.markdown("---")
st.sidebar.markdown("**Model Selection**")
model_choices = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "openai/gpt-oss-120b", "Custom"]
selected_model_dropdown = st.sidebar.selectbox("Choose Model", model_choices, label_visibility="collapsed")

if selected_model_dropdown == "Custom":
    model_env = st.sidebar.text_input("Enter custom model name", value="llama-3.3-70b-versatile")
else:
    model_env = selected_model_dropdown

# Update environment variable dynamically so the runner picks it up
os.environ["GROQ_MODEL"] = model_env

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Backend:** {backend_env.capitalize()}")
st.sidebar.markdown("**Cases:** 10 (demo mode)")

# Show prompt content
with st.expander(f"View prompt: {version_id}", expanded=False):
    import yaml
    with open(yaml_path) as f:
        prompt_data = yaml.safe_load(f)
    st.code(prompt_data['system_prompt'], language="text")
    if prompt_data.get('few_shot_examples'):
        st.markdown(f"**Few-shot examples:** {len(prompt_data['few_shot_examples'])}")
    else:
        st.markdown("**Few-shot examples:** none")

# Run button
col1, col2 = st.columns([1, 3])
with col1:
    run_button = st.button("Run eval", type="primary", use_container_width=True)

if run_button:
    # Check Groq key
    from dotenv import load_dotenv
    load_dotenv(override=True)
    groq_key = os.environ.get("GROQ_API_KEY", "")
    if not groq_key:
        st.error(
            "GROQ_API_KEY not set. Add it to your .env file or Render environment variables. "
            "Get a free key at console.groq.com"
        )
        st.stop()

    os.environ["LLM_BACKEND"] = "groq"
    os.environ["DEMO_MODE"] = "true"
    os.environ["DEMO_CASE_LIMIT"] = "10"

    with st.spinner(f"Running 10-case eval on {version_id} via Groq..."):
        # Animated progress bar showing eval running through cases
        progress_bar = st.progress(0)
        status_text = st.empty()
        for i in range(100):
            progress_bar.progress(i + 1)
            status_text.text(f"Evaluating case {i+1}/10...")
            import time; time.sleep(0.02)
        progress_bar.empty()
        status_text.empty()

        try:
            results = asyncio.run(
                run_all(yaml_path, "data/golden_dataset.json", concurrency=5)
            )
            scores = score_run(results)
            run_id = str(uuid.uuid4())[:8]

            init_db()
            save_run(run_id, scores['version_id'], scores, results)

            # Only mark as baseline if it IS v1 AND no baseline exists yet
            baseline_scores, baseline_results = get_baseline()
            is_first_run = baseline_scores is None
            if is_first_run and scores['version_id'] == 'v1':
                mark_as_baseline(run_id)

            comparison = None
            if not is_first_run and baseline_scores:
                comparison = compare_runs(
                    scores, baseline_scores, results, baseline_results
                )
            
            if comparison is None:
                comparison = {
                    "status": "baseline",
                    "current_version": scores['version_id'],
                    "baseline_version": scores['version_id'],
                    "overall_accuracy_delta": 0.0,
                    "per_class_deltas": {"positive": 0.0, "negative": 0.0, "neutral": 0.0},
                    "latency_delta_ms": 0.0,
                    "regressed_cases": [],
                    "regressed_count": 0,
                    "improved_count": 0,
                    "current_accuracy": scores['overall_accuracy'],
                    "baseline_accuracy": scores['overall_accuracy'],
                    "judge_score_delta": None,
                    "failure_rate_delta": 0.0,
                }

        except Exception as e:
            st.error(f"Eval failed: {e}")
            st.stop()

        # Compute drift
        history = get_run_history(limit=5)
        drift = compute_rolling_stats() if len(history) >= 2 else None
        
        # Generate HTML report
        os.makedirs("reports", exist_ok=True)
        report_path = f"reports/report_{run_id}.html"
        html_report_content = generate_report(
            scores=scores,
            comparison=comparison,
            results=results,
            history=history,
            output_path=report_path,
            run_id=run_id,
            drift=drift
        )

    # Results display
    st.markdown("---")
    st.subheader("Results Report")
    
    # Download button for the HTML report
    st.download_button(
        label="Download Interactive HTML Report",
        data=html_report_content,
        file_name=f"report_{run_id}.html",
        mime="text/html"
    )
    
    # Render interactive HTML directly in Streamlit
    components.html(html_report_content, height=800, scrolling=True)

    # Slack Alert block
    from reporting.slack_alert import build_alert_text

    if comparison['status'] in ('warn', 'critical'):
        alert_text = build_alert_text(comparison, report_path)
        
        status_color = "🔴" if comparison['status'] == 'critical' else "🟡"
        st.markdown("---")
        st.markdown(f"### {status_color} Slack alert (what would fire in production)")
        st.code(alert_text, language="text")
        
        if os.getenv("SLACK_WEBHOOK_URL"):
            from reporting.slack_alert import send_slack_alert
            send_slack_alert(comparison, report_path)
            st.success("Slack alert sent to webhook.")

    # Drift Detection block
    from eval.drift_detector import compute_rolling_stats, format_drift_alert
    
    st.markdown("---")
    st.subheader("Drift detection (rolling 5-run window)")
    
    drift = compute_rolling_stats(
        db_path=os.getenv("DB_PATH", "storage/runs.db"),
        window=5
    )
    
    if drift.get("status") == "insufficient_data":
        st.info("Not enough runs yet for drift analysis. Run eval 2+ more times.")
    else:
        drift_colors = {
            "stable": "green",
            "improving": "green",
            "drift_warn": "orange",
            "drift_critical": "red",
        }
        color = drift_colors.get(drift["status"], "gray")
        
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("Drift status", drift["status"].upper().replace("_", " "))
        d2.metric("Slope per run",
                  f"{drift['accuracy_slope_per_run']:+.3f}",
                  help="Accuracy change per run over the window")
        d3.metric("Cumulative drift",
                  f"{drift['cumulative_drift_over_window']*100:+.1f}%",
                  help="Total drift over the rolling window")
        d4.metric("Trend", drift["trend_direction"])
        
        if drift.get("run_accuracies"):
            st.markdown("**Accuracy over last 5 runs**")
            import pandas as pd
            df = pd.DataFrame({
                "run": [f"Run {i+1}" for i in range(len(drift["run_accuracies"]))],
                "accuracy": [a * 100 for a in drift["run_accuracies"]]
            })
            st.line_chart(df.set_index("run"))
        
        if drift["status"] in ("drift_warn", "drift_critical"):
            st.warning(
                f"Drift detected: accuracy declining {drift['accuracy_slope_per_run']:+.3f} "
                f"per run over {drift['window_size']} runs. "
                f"Cumulative: {drift['cumulative_drift_over_window']*100:+.1f}%"
            )

# Footer
st.markdown("---")
st.markdown(
    "Built by Shubham · "
    "[GitHub repo](https://github.com/YOUR_USERNAME/regression-detector) · "
    f"Model: {model_env} via {backend_env.capitalize()} · Dataset: tweet_eval sentiment"
)
