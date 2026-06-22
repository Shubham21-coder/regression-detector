"""HTML report generator using Jinja2 with inline CSS."""

import os
from jinja2 import Environment

TEMPLATE_STR = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>CT1 Regression Report — {{ scores.version_id }}</title>
    <style>
        body { font-family: monospace; max-width: 860px; margin: 40px auto; padding: 20px; background: #f9f9f9; color: #1a1a1a; }
        .pass { color: #1a7a1a; } .warn { color: #b86f00; } .critical { color: #b30000; font-weight: bold; }
        table { border-collapse: collapse; width: 100%; margin: 16px 0; }
        th, td { border: 1px solid #ccc; padding: 8px 12px; text-align: left; }
        th { background: #e8e8e8; }
        .regressed { background: #fff0f0; }
        .improved { background: #f0fff0; }
        .badge { padding: 2px 8px; border-radius: 3px; font-size: 0.85em; }
        h1 { margin-bottom: 8px; }
        h2 { margin-top: 28px; margin-bottom: 8px; }
        .delta-pos { color: #1a7a1a; }
        .delta-neg { color: #b30000; }
    </style>
</head>
<body>

    <!-- Section 1: Header -->
    <h1>Regression Detection Report</h1>
    {% if comparison %}
    <p>Run: {{ scores.version_id }} vs baseline {{ comparison.baseline_version }}</p>
    {% else %}
    <p>Run: {{ scores.version_id }} (baseline — no comparison)</p>
    {% endif %}
    <p>Timestamp: {{ scores.run_timestamp }}</p>
    {% if comparison %}
    <p>Status: <span class="{{ comparison.status }}">{{ comparison.status | upper }}</span></p>
    {% endif %}

    <!-- Section 2: Scorecard -->
    <h2>Scorecard</h2>
    <table>
        <tr>
            <th>Metric</th>
            <th>Current</th>
            <th>Baseline</th>
            <th>Delta</th>
        </tr>
        {% if comparison %}
        <tr>
            <td>Overall accuracy</td>
            <td>{{ "%.2f" | format(scores.overall_accuracy) }}</td>
            <td>{{ "%.2f" | format(comparison.baseline_accuracy) }}</td>
            {% set d = comparison.overall_accuracy_delta %}
            <td class="{{ 'delta-pos' if d >= 0 else 'delta-neg' }}">{{ "%+.4f" | format(d) }}</td>
        </tr>
        {% for label in ["positive", "negative", "neutral"] %}
        <tr>
            <td>{{ label }} accuracy</td>
            <td>{{ "%.2f" | format(scores.per_class_accuracy[label]) }}</td>
            <td>—</td>
            {% set cd = comparison.per_class_deltas[label] %}
            <td class="{{ 'delta-pos' if cd >= 0 else 'delta-neg' }}">{{ "%+.4f" | format(cd) }}</td>
        </tr>
        {% endfor %}
        <tr>
            <td>Avg latency ms</td>
            <td>{{ "%.1f" | format(scores.avg_latency_ms) }}</td>
            <td>—</td>
            {% set ld = comparison.latency_delta_ms %}
            <td class="{{ 'delta-pos' if ld <= 0 else 'delta-neg' }}">{{ "%+.1f" | format(ld) }}</td>
        </tr>
        <tr>
            <td>P95 latency ms</td>
            <td>{{ "%.1f" | format(scores.p95_latency_ms) }}</td>
            <td>—</td>
            <td>—</td>
        </tr>
        <tr>
            <td>Total prompt tokens</td>
            <td>{{ scores.total_prompt_tokens }}</td>
            <td>—</td>
            <td>—</td>
        </tr>
        <tr>
            <td>Error count</td>
            <td>{{ scores.error_count }}</td>
            <td>—</td>
            <td>—</td>
        </tr>
        {% else %}
        <tr>
            <td>Overall accuracy</td>
            <td>{{ "%.2f" | format(scores.overall_accuracy) }}</td>
            <td>—</td>
            <td>—</td>
        </tr>
        {% for label in ["positive", "negative", "neutral"] %}
        <tr>
            <td>{{ label }} accuracy</td>
            <td>{{ "%.2f" | format(scores.per_class_accuracy[label]) }}</td>
            <td>—</td>
            <td>—</td>
        </tr>
        {% endfor %}
        <tr>
            <td>Avg latency ms</td>
            <td>{{ "%.1f" | format(scores.avg_latency_ms) }}</td>
            <td>—</td>
            <td>—</td>
        </tr>
        <tr>
            <td>P95 latency ms</td>
            <td>{{ "%.1f" | format(scores.p95_latency_ms) }}</td>
            <td>—</td>
            <td>—</td>
        </tr>
        <tr>
            <td>Total prompt tokens</td>
            <td>{{ scores.total_prompt_tokens }}</td>
            <td>—</td>
            <td>—</td>
        </tr>
        <tr>
            <td>Error count</td>
            <td>{{ scores.error_count }}</td>
            <td>—</td>
            <td>—</td>
        </tr>
        {% endif %}
    </table>

    <!-- Section 3: Regressed cases -->
    {% if comparison and comparison.regressed_count > 0 %}
    <h2>Regressed Cases ({{ comparison.regressed_count }})</h2>
    <table>
        <tr>
            <th>ID</th>
            <th>Text</th>
            <th>True label</th>
            <th>Baseline pred</th>
            <th>Current pred</th>
            <th>Difficulty</th>
        </tr>
        {% for r in comparison.regressed_cases[:20] %}
        <tr class="regressed">
            <td>{{ r.id }}</td>
            <td>{{ r.text }}</td>
            <td>{{ r.true_label }}</td>
            <td>{{ r.baseline_predicted }}</td>
            <td>{{ r.current_predicted }}</td>
            <td>{{ r.difficulty }}</td>
        </tr>
        {% endfor %}
    </table>
    {% if comparison.regressed_count > 20 %}
    <p><em>... and {{ comparison.regressed_count - 20 }} more regressed cases</em></p>
    {% endif %}
    {% endif %}

    <!-- Section 4: Run history -->
    {% if history %}
    <h2>Run History</h2>
    <table>
        <tr>
            <th>Run ID</th>
            <th>Version</th>
            <th>Timestamp</th>
            <th>Accuracy</th>
            <th>Baseline?</th>
        </tr>
        {% for h in history[:10] %}
        <tr>
            <td>{{ h.run_id }}</td>
            <td>{{ h.version_id }}</td>
            <td>{{ h.timestamp }}</td>
            <td>{{ "%.2f" | format(h.overall_accuracy) }}</td>
            <td>{{ "\u2605" if h.is_baseline else "" }}</td>
        </tr>
        {% endfor %}
    </table>
    {% endif %}

</body>
</html>
"""


def generate_report(
    scores: dict,
    comparison: dict | None,
    results: list,
    history: list,
    output_path: str = "reports/report.html",
) -> str:
    """Generate a self-contained HTML report and save to disk."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    env = Environment(autoescape=True)
    template = env.from_string(TEMPLATE_STR)
    html = template.render(
        scores=scores,
        comparison=comparison,
        results=results,
        history=history,
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Report saved to: {output_path}")
    return output_path
