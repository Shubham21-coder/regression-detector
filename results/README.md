# Eval Results

These results were produced locally using Qwen2.5-3B-Instruct via LM Studio
on the full 100-case tweet_eval golden dataset.

| Version | Accuracy | vs Baseline | Status | Regressed cases |
|---------|----------|-------------|--------|-----------------|
| v1 (baseline) | 63.0% | — | BASELINE | — |
| v2 (minimal prompt) | 63.0% | +0.0% | PASS | 20 |
| v3 (wrong vocabulary) | 0.0% | -63.0% | CRITICAL | 63 |

## Key finding
v3 demonstrates a vocabulary mismatch regression: changing output labels from
positive/negative/neutral to happy/sad/okay causes near-complete eval failure.
This is a real production failure mode caught by the regression detector.
