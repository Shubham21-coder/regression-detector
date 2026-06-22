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

backend_env = os.environ.get("LLM_BACKEND", "groq")
model_env = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile") if backend_env == "groq" else "local-model"

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Backend:** {backend_env.capitalize()} ({model_env})")
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

# Footer
st.markdown("---")
st.markdown(
    "Built by Shubham · "
    "[GitHub repo](https://github.com/YOUR_USERNAME/regression-detector) · "
    f"Model: {model_env} via {backend_env.capitalize()} · Dataset: tweet_eval sentiment"
)
