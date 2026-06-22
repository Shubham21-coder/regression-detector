
# CT1 — LLM Prompt Regression Detection System

[![CI](https://github.com/YOUR_USERNAME/regression-detector/actions/workflows/eval.yml/badge.svg)](https://github.com/YOUR_USERNAME/regression-detector/actions)
[![Live Demo](https://img.shields.io/badge/Live%20Demo-Render-brightgreen)](https://YOUR_APP.onrender.com)
![Python](https://img.shields.io/badge/python-3.11-blue)
![License](https://img.shields.io/badge/license-MIT-green)

> A CI pipeline that catches LLM prompt quality regressions before they ship.
> Evaluates any prompt change against 125 human-labeled test cases —
> including 25 adversarial edge cases — and blocks merge on critical drops.
> **Zero ongoing API cost** when run locally via LM Studio.

**[→ Open live demo](https://YOUR_APP.onrender.com)** — select a prompt version,
run a 10-case eval, see regression detection in action. No setup required.

---

## What this system does

When a prompt changes, this pipeline:
1. Runs the new prompt against 125 labeled test cases
2. Scores on two dimensions: exact match + LLM-as-judge (1–5)
3. Diffs results against the baseline run
4. Detects drift across rolling windows (catches slow degradation)
5. Generates an HTML report with scorecard, trend chart, regressed cases
6. Alerts via Slack (or stdout) and blocks GitHub PR merge on critical regressions

The dataset includes adversarial edge cases: typos, sarcasm, mixed-language
inputs, emoji-only tweets, and implicit sentiment — cases that expose whether
a model understands language or pattern-matches on obvious signals.

---

## CI/CD behavior

On every PR touching `prompts/*.yaml`:
- Eval runs automatically via GitHub Actions
- Results posted as a PR comment with status badge
- **Exit code 0 (PASS):** merge allowed
- **Exit code 1 (WARN):** merge allowed with warning comment  
- **Exit code 2 (CRITICAL):** merge blocked

---

## Quickstart (local, LM Studio)

**Requirements:** Python 3.11+, LM Studio with Qwen2.5-3B-Instruct Q4_K_M loaded

```bash
git clone https://github.com/YOUR_USERNAME/regression-detector
cd regression-detector
pip install -r requirements.txt
cp .env.example .env          # edit if needed
python data/build_dataset.py  # builds golden_dataset.json (125 cases)

# Run baseline eval
python main.py --yaml prompts/v1.yaml --dataset data/golden_dataset.json

# Run regression demo
python main.py --yaml prompts/v3.yaml --dataset data/golden_dataset.json
# Expected: CRITICAL | accuracy ~-80% | vocabulary mismatch detected
```

**LM Studio setup:** Download from lmstudio.ai → search "Qwen2.5-3B-Instruct"
→ download Q4_K_M variant → Local Server tab → Start Server.

---

## Quickstart (cloud, Groq free API)

```bash
# Get free API key at console.groq.com (30 seconds, no credit card)
export GROQ_API_KEY=your_key
export LLM_BACKEND=groq
export DEMO_MODE=true   # runs 10 cases instead of 125

python main.py --yaml prompts/v1.yaml --dataset data/golden_dataset.json
python main.py --yaml prompts/v3.yaml --dataset data/golden_dataset.json
```

---

## Docker

```bash
docker build -t regression-detector .
docker run -e GROQ_API_KEY=your_key \
           -e LLM_BACKEND=groq \
           -v $(pwd)/reports:/app/reports \
           -v $(pwd)/storage:/app/storage \
           regression-detector \
           --yaml prompts/v1.yaml --dataset data/golden_dataset.json

# Or with docker-compose:
GROQ_API_KEY=your_key docker-compose up
```

---

## How to add test cases

Open `data/edge_cases.json` and add entries following this schema:

```json
{
  "id": 200,
  "text": "Your tweet text here",
  "label": "positive",
  "expected_difficulty": "hard",
  "edge_type": "sarcasm",
  "annotation_note": "Why you labeled it this way"
}
```

Then rebuild: `python data/build_dataset.py`

**Label rules:**
- `positive` — net positive sentiment
- `negative` — net negative sentiment  
- `neutral` — factual, mixed, or ambiguous with no dominant direction
- When in doubt on ambiguous cases, see `annotation_note` in existing edge cases for precedent

**ID assignment:** Use IDs 200+ for new cases (100–124 are reserved for the built-in edge cases).

---

## How to adjust thresholds

Edit constants at the top of `eval/comparator.py`:

```python
WARN_THRESHOLD     = -0.03   # −3% accuracy triggers WARN
CRITICAL_THRESHOLD = -0.08   # −8% accuracy triggers CRITICAL
VOCAB_MISMATCH_CRITICAL = 0.5  # >50% unknown labels forces CRITICAL
```

Edit drift detection thresholds in `eval/drift_detector.py`:

```python
DRIFT_WARN_THRESHOLD     = -0.02  # −2% cumulative over window → WARN
DRIFT_CRITICAL_THRESHOLD = -0.05  # −5% cumulative over window → CRITICAL
DRIFT_WINDOW_SIZE        = 5      # number of runs in rolling window
```

## Eval results (local run, Qwen2.5-3B-Instruct, 125 cases)

| Prompt | Accuracy | Judge score | vs Baseline | Status |
|--------|----------|-------------|-------------|--------|
| v1 — full instructions + few-shot | 71.4% | 3.4/5 | baseline | — |
| v2 — minimal instructions | 71.4% | 3.4/5 | ±0.0% | PASS |
| v3 — wrong vocabulary | 0.0% | 3.3/5 | −71.4% | CRITICAL |

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `LLM_BACKEND` | `local` | `local` (LM Studio) or `groq` |
| `GROQ_API_KEY` | — | Required when `LLM_BACKEND=groq` |
| `LM_STUDIO_BASE_URL` | `http://localhost:1234/v1` | LM Studio server URL |
| `DEMO_MODE` | `false` | Limit to 10 cases for speed |
| `SKIP_JUDGE` | `false` | Skip LLM-as-judge scoring |
| `DB_PATH` | `storage/runs.db` | SQLite database path |
| `SLACK_WEBHOOK_URL` | — | Optional Slack alert webhook |

---

## Project structure

```
regression_detector/
├── data/
│   ├── golden_dataset.json  # Base evaluation cases
│   └── edge_cases.json      # Hard adversarial cases
├── eval/
│   ├── runner.py            # Executes prompts against LLM
│   ├── scorer.py            # Calculates exact match & judge scores
│   ├── llm_judge.py         # LLM-as-judge relevance scoring
│   ├── comparator.py        # Compares v2 vs v1 for regression
│   └── drift_detector.py    # Rolling window trend analysis
├── prompts/                 # Prompt versions (.yaml)
├── reporting/               # HTML report generation
├── storage/                 # runs.db SQLite database
├── reports/                 # Output HTML reports
└── main.py                  # CLI entrypoint
```
