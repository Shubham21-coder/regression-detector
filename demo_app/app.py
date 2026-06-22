import streamlit as st
import asyncio, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eval.runner import run_all
from eval.scorer import score_run
from eval.comparator import compare_runs
from storage.db import init_db, save_run, get_baseline, mark_as_baseline, get_run_history
import uuid

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
    ["v1 — Full instructions + few-shot (baseline)",
     "v2 — Minimal instructions (no few-shot)",
     "v3 — Wrong output vocabulary (critical regression)"],
    index=0
)
version_map = {
    "v1 — Full instructions + few-shot (baseline)": "prompts/v1.yaml",
    "v2 — Minimal instructions (no few-shot)": "prompts/v2.yaml",
    "v3 — Wrong output vocabulary (critical regression)": "prompts/v3.yaml"
}
yaml_path = version_map[prompt_choice]
version_id = yaml_path.split("/")[1].replace(".yaml", "")

st.sidebar.markdown("---")
st.sidebar.markdown("**Backend:** Groq (Llama-3.1-8B-Instant)")
st.sidebar.markdown("**Cases:** 10 (demo mode)")
st.sidebar.markdown("**Cost:** $0.00 (free tier)")

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
        try:
            results = asyncio.run(
                run_all(yaml_path, "data/golden_dataset.json", concurrency=5)
            )
            scores = score_run(results)
            run_id = str(uuid.uuid4())[:8]

            init_db()
            save_run(run_id, scores['version_id'], scores, results)

            baseline_scores, baseline_results = get_baseline()
            is_baseline_run = (
                baseline_scores is None or
                baseline_scores['version_id'] == scores['version_id']
            )

            if is_baseline_run and version_id == "v1":
                mark_as_baseline(run_id)

            comparison = None
            if not is_baseline_run and baseline_scores:
                comparison = compare_runs(
                    scores, baseline_scores, results, baseline_results
                )

        except Exception as e:
            st.error(f"Eval failed: {e}")
            st.stop()

    # Results display
    st.markdown("---")
    st.subheader("Results")

    # Status badge
    if comparison:
        status = comparison['status']
        color = {"pass": "green", "warn": "orange", "critical": "red"}[status]
        st.markdown(
            f"**Status:** :{color}[{status.upper()}] &nbsp;|&nbsp; "
            f"**{version_id}** vs baseline **{comparison['baseline_version']}**"
        )

    # Metric columns
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Accuracy", f"{scores['overall_accuracy']:.1%}",
               delta=f"{comparison['overall_accuracy_delta']*100:+.1f}%" if comparison else None)
    m2.metric("Avg latency", f"{scores['avg_latency_ms']:.0f}ms")
    m3.metric("Vocab mismatch",
               f"{scores.get('vocabulary_mismatch_rate', 0):.1%}")
    m4.metric("Regressed cases",
               comparison['regressed_count'] if comparison else "N/A")

    # Per-class accuracy
    st.markdown("**Per-class accuracy**")
    pc = scores['per_class_accuracy']
    c1, c2, c3 = st.columns(3)
    c1.metric("Positive", f"{pc.get('positive', 0):.1%}")
    c2.metric("Negative", f"{pc.get('negative', 0):.1%}")
    c3.metric("Neutral",  f"{pc.get('neutral', 0):.1%}")

    # Case results table
    st.markdown("**Case-by-case results (10 cases)**")
    table_data = []
    for r in results:
        table_data.append({
            "ID": r['id'],
            "Text": r['text'][:60] + "..." if len(r['text']) > 60 else r['text'],
            "True label": r['true_label'],
            "Predicted": r['predicted_label'],
            "Correct": "✓" if r['correct'] else "✗",
            "Latency ms": r['latency_ms']
        })
    st.dataframe(table_data, use_container_width=True)

    # Regressed cases
    if comparison and comparison['regressed_cases']:
        st.markdown("**Regressed cases (correct in baseline, wrong now)**")
        st.dataframe(comparison['regressed_cases'], use_container_width=True)

# Footer
st.markdown("---")
st.markdown(
    "Built by Sneha · "
    "[GitHub repo](https://github.com/YOUR_USERNAME/regression-detector) · "
    "Model: llama-3.3-70b-versatile via Groq · Dataset: tweet_eval sentiment"
)
