"""HTML Report Generator."""
import os
from jinja2 import Template

TEMPLATE = """<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
<meta charset="UTF-8">
<title>CT1 Eval Report — {{ scores.version_id }}</title>
<style>
  /* === THEME VARIABLES === */
  :root {
    --bg-color: #f5f7fa;
    --text-color: #1a1a1a;
    --text-muted: #666;
    --card-bg: #ffffff;
    --card-border: #eee;
    --metric-bg: #f8f9fa;
    --metric-border: #dee2e6;
    --table-th-bg: #f8f9fa;
    --table-td-border: #f0f0f0;
    --table-hover: #fafafa;
    --accent: #3b82f6;
  }
  [data-theme="dark"] {
    --bg-color: #0f172a;
    --text-color: #f8fafc;
    --text-muted: #94a3b8;
    --card-bg: #1e293b;
    --card-border: #334155;
    --metric-bg: #0f172a;
    --metric-border: #475569;
    --table-th-bg: #334155;
    --table-td-border: #334155;
    --table-hover: #0f172a;
    --accent: #60a5fa;
  }

  /* === RESET + BASE === */
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Segoe UI', system-ui, sans-serif;
    font-size: 14px;
    line-height: 1.6;
    color: var(--text-color);
    background: var(--bg-color);
    padding: 32px 16px;
    transition: background-color 0.3s ease, color 0.3s ease;
  }
  .container { max-width: 960px; margin: 0 auto; position: relative; }
  
  .theme-toggle {
    position: absolute;
    top: 0;
    right: 0;
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    color: var(--text-color);
    padding: 6px 12px;
    border-radius: 20px;
    cursor: pointer;
    font-size: 12px;
    font-weight: 600;
    transition: all 0.2s ease;
  }
  .theme-toggle:hover {
    background: var(--metric-bg);
    transform: translateY(-1px);
  }
  
  /* === STATUS BADGE === */
  .badge {
    display: inline-block;
    padding: 4px 14px;
    border-radius: 20px;
    font-weight: 600;
    font-size: 13px;
    letter-spacing: 0.5px;
  }
  .badge.pass    { background: #d4edda; color: #155724; }
  .badge.warn    { background: #fff3cd; color: #856404; }
  .badge.critical{ background: #f8d7da; color: #721c24; }
  .badge.baseline{ background: #e2e3e5; color: #383d41; }

  /* === CARDS === */
  .card {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 12px;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -2px rgba(0,0,0,0.05);
    padding: 24px;
    margin-bottom: 24px;
    transition: transform 0.2s ease, box-shadow 0.2s ease, background-color 0.3s;
  }
  .card:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -4px rgba(0,0,0,0.1);
  }
  .card-title {
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: var(--text-muted);
    margin-bottom: 16px;
    border-bottom: 1px solid var(--card-border);
    padding-bottom: 10px;
  }

  /* === SCORECARD GRID === */
  .metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 12px;
    margin-bottom: 16px;
  }
  .metric-box {
    background: var(--metric-bg);
    border-radius: 8px;
    padding: 14px 16px;
    border-left: 4px solid var(--metric-border);
    transition: background-color 0.3s ease;
  }
  .metric-box:hover {
    background: var(--table-hover);
  }
  .metric-box.positive { border-left-color: #28a745; }
  .metric-box.negative { border-left-color: #dc3545; }
  .metric-box.neutral  { border-left-color: #6c757d; }
  .metric-label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
  .metric-value { font-size: 24px; font-weight: 700; color: var(--text-color); line-height: 1.2; }
  .metric-delta { font-size: 12px; margin-top: 2px; }
  .delta-pos { color: #28a745; }
  .delta-neg { color: #dc3545; }
  .delta-neu { color: var(--text-muted); }

  /* === TABLES === */
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th { background: var(--table-th-bg); color: var(--text-muted); font-weight: 600; text-align: left;
       padding: 10px 12px; border-bottom: 2px solid var(--card-border); transition: background-color 0.3s; }
  td { padding: 9px 12px; border-bottom: 1px solid var(--table-td-border); vertical-align: top; }
  tr { transition: background-color 0.2s; }
  tr:hover td { background: var(--table-hover); }
  .regressed-row td { background: rgba(220, 53, 69, 0.05); }
  .text-cell { max-width: 240px; word-break: break-word; color: var(--text-color); }
  .label-chip {
    display: inline-block; padding: 2px 8px; border-radius: 10px;
    font-size: 11px; font-weight: 600;
  }
  .chip-positive  { background: #d4edda; color: #155724; }
  .chip-negative  { background: #f8d7da; color: #721c24; }
  .chip-neutral   { background: #e2e3e5; color: #383d41; }
  .chip-unknown   { background: #fff3cd; color: #856404; }

  /* === TREND CHART (pure CSS bar chart) === */
  .trend-chart {
    display: flex;
    align-items: flex-end;
    gap: 8px;
    height: 120px;
    padding: 0 0 8px;
    border-bottom: 1px solid #dee2e6;
    margin-bottom: 12px;
  }
  .trend-bar-group { display: flex; flex-direction: column; align-items: center; flex: 1; }
  .trend-bar {
    width: 100%;
    background: #4a90d9;
    border-radius: 3px 3px 0 0;
    min-height: 3px;
    transition: opacity 0.2s;
    position: relative;
  }
  .trend-bar.is-baseline { background: #6c757d; }
  .trend-bar.is-critical { background: #dc3545; }
  .trend-bar.is-warn     { background: #ffc107; }
  .trend-bar.is-current  { background: #28a745; outline: 2px solid #155724; }
  .trend-bar:hover::after {
    content: attr(data-tip);
    position: absolute;
    bottom: 100%; left: 50%;
    transform: translateX(-50%);
    background: #333; color: #fff;
    padding: 3px 8px; border-radius: 4px;
    font-size: 11px; white-space: nowrap;
    pointer-events: none; z-index: 10;
  }
  .trend-label { font-size: 10px; color: #888; margin-top: 4px; text-align: center; }
  .trend-value { font-size: 10px; color: #555; margin-top: 2px; }

  /* === JUDGE SCORE BAR === */
  .judge-bar-row { display: flex; align-items: center; gap: 10px; margin: 6px 0; }
  .judge-bar-label { width: 24px; text-align: right; font-size: 12px; color: #555; }
  .judge-bar-track { flex: 1; height: 14px; background: #f0f0f0; border-radius: 7px; overflow: hidden; }
  .judge-bar-fill  { height: 100%; border-radius: 7px; background: #4a90d9; }
  .judge-bar-count { width: 28px; font-size: 11px; color: #888; }

  /* === EDGE TYPE BREAKDOWN === */
  .edge-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 8px;
  }
  .edge-item {
    background: #f8f9fa; border-radius: 6px; padding: 10px 12px;
    border-top: 3px solid #dee2e6;
  }
  .edge-item.good  { border-top-color: #28a745; }
  .edge-item.mid   { border-top-color: #ffc107; }
  .edge-item.bad   { border-top-color: #dc3545; }
  .edge-name { font-size: 11px; color: #888; }
  .edge-acc  { font-size: 18px; font-weight: 700; }

  /* === MISC === */
  .header-row { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
  .header h1 { font-size: 22px; color: var(--text-color); margin-bottom: 4px; }
  .header p { color: var(--text-muted); font-size: 13px; }
  .meta-info { text-align: right; font-size: 12px; color: var(--text-muted); }
</style>
<script>
  function toggleTheme() {
    const html = document.documentElement;
    if (html.getAttribute('data-theme') === 'dark') {
      html.setAttribute('data-theme', 'light');
    } else {
      html.setAttribute('data-theme', 'dark');
    }
  }
</script>
</head>
<body>
<div class="container">
  <button class="theme-toggle" onclick="toggleTheme()">Toggle Theme</button>

  <!-- HEADER -->
  <div class="header-row">
    <div>
      <h1 style="font-size:22px;font-weight:700;margin-bottom:6px">
        CT1 Regression Report
      </h1>
      <span class="badge {{ comparison.status if comparison else 'baseline' }}">
        {{ (comparison.status | upper) if comparison else 'BASELINE' }}
      </span>
      {% if comparison %}
      &nbsp;
      <span style="font-size:13px;color:#555">
        {{ scores.version_id }} vs baseline {{ comparison.baseline_version }}
      </span>
      {% endif %}
    </div>
    <div class="run-meta">
      <div>Run ID: {{ run_id }}</div>
      <div>{{ scores.run_timestamp[:19] | replace('T',' ') }} UTC</div>
      <div>Model: {{ scores.get('model_name', 'local') }}</div>
      <div>Cases: {{ scores.num_cases }}</div>
    </div>
  </div>

  <!-- SCORECARD -->
  <div class="card">
    <div class="card-title">Scorecard</div>
    <div class="metrics-grid">

      {# Overall accuracy #}
      {% set acc_delta = comparison.overall_accuracy_delta if comparison else None %}
      <div class="metric-box {{ 'positive' if (acc_delta and acc_delta > 0) else ('negative' if (acc_delta and acc_delta < 0) else 'neutral') }}">
        <div class="metric-label">Accuracy</div>
        <div class="metric-value">{{ "%.1f"|format(scores.overall_accuracy * 100) }}%</div>
        {% if acc_delta is not none %}
        <div class="metric-delta {{ 'delta-pos' if acc_delta >= 0 else 'delta-neg' }}">
          {{ "%+.1f"|format(acc_delta * 100) }}% vs baseline
        </div>
        {% endif %}
      </div>

      {# Judge score #}
      {% if scores.avg_judge_score %}
      {% set jdelta = comparison.judge_score_delta if comparison else None %}
      <div class="metric-box {{ 'positive' if (jdelta and jdelta > 0) else ('negative' if (jdelta and jdelta < 0) else 'neutral') }}">
        <div class="metric-label">Judge score (avg)</div>
        <div class="metric-value">{{ "%.1f"|format(scores.avg_judge_score) }}<span style="font-size:14px;color:#888">/5</span></div>
        {% if jdelta is not none %}
        <div class="metric-delta {{ 'delta-pos' if jdelta >= 0 else 'delta-neg' }}">
          {{ "%+.2f"|format(jdelta) }} vs baseline
        </div>
        {% endif %}
      </div>
      {% endif %}

      {# Regressed cases #}
      {% if comparison %}
      <div class="metric-box {{ 'negative' if comparison.regressed_count > 0 else 'positive' }}">
        <div class="metric-label">Regressed cases</div>
        <div class="metric-value">{{ comparison.regressed_count }}</div>
        <div class="metric-delta delta-pos">+{{ comparison.improved_count }} improved</div>
      </div>
      {% endif %}

      {# Latency #}
      {% set lat_delta = comparison.latency_delta_ms if comparison else None %}
      <div class="metric-box {{ 'negative' if (lat_delta and lat_delta > 50) else 'neutral' }}">
        <div class="metric-label">Avg latency</div>
        <div class="metric-value">{{ "%.0f"|format(scores.avg_latency_ms) }}<span style="font-size:14px;color:#888">ms</span></div>
        {% if lat_delta is not none %}
        <div class="metric-delta {{ 'delta-neg' if lat_delta > 0 else 'delta-pos' }}">
          {{ "%+.0f"|format(lat_delta) }}ms vs baseline
        </div>
        {% endif %}
      </div>

      {# Vocab mismatch #}
      {% if scores.vocabulary_mismatch_rate is defined %}
      <div class="metric-box {{ 'negative' if scores.vocabulary_mismatch_rate > 0.1 else 'neutral' }}">
        <div class="metric-label">Vocab mismatch</div>
        <div class="metric-value">{{ "%.1f"|format(scores.vocabulary_mismatch_rate * 100) }}%</div>
        <div class="metric-delta delta-neu">unknown-label predictions</div>
      </div>
      {% endif %}

      {# Cost #}
      <div class="metric-box neutral">
        <div class="metric-label">API cost</div>
        <div class="metric-value" style="font-size:16px">$0.00</div>
        <div class="metric-delta delta-neu">local inference</div>
      </div>

    </div>

    {# Per-class accuracy table #}
    <table style="margin-top:8px">
      <tr>
        <th>Class</th><th>Accuracy</th>
        {% if comparison %}<th>Delta</th>{% endif %}
        <th>Cases</th>
      </tr>
      {% for label in ['positive','negative','neutral'] %}
      {% set acc = scores.per_class_accuracy.get(label, 0) %}
      {% set delta = comparison.per_class_deltas.get(label) if comparison else None %}
      <tr>
        <td><span class="label-chip chip-{{ label }}">{{ label }}</span></td>
        <td>{{ "%.1f"|format(acc * 100) }}%</td>
        {% if comparison %}
        <td class="{{ 'delta-pos' if delta and delta > 0 else ('delta-neg' if delta and delta < 0 else '') }}">
          {{ ("%+.1f"|format(delta * 100) + "%") if delta is not none else "—" }}
        </td>
        {% endif %}
        <td style="color:#888">{{ scores.per_class_counts.get(label, '—') if scores.per_class_counts is defined else '—' }}</td>
      </tr>
      {% endfor %}
    </table>
  </div>

  <!-- TREND CHART -->
  {% if history and history|length > 1 %}
  <div class="card">
    <div class="card-title">Accuracy trend — last {{ history|length }} runs</div>
    {% set max_acc = history | map(attribute='overall_accuracy') | max %}
    {% set min_acc = [((history | map(attribute='overall_accuracy') | min) - 0.05), 0] | max %}
    <div class="trend-chart">
      {% for run in history | reverse %}
      {% set height_pct = ((run.overall_accuracy - min_acc) / ((max_acc - min_acc) or 0.01) * 100) | int %}
      {% set is_current = (run.run_id == run_id) %}
      {% set bar_class = 'is-current' if is_current else ('is-baseline' if run.is_baseline else 'is-pass') %}
      <div class="trend-bar-group">
        <div class="trend-bar {{ bar_class }}"
             style="height: {{ [height_pct, 3]|max }}%"
             data-tip="{{ run.version_id }}: {{ '%.1f'|format(run.overall_accuracy * 100) }}%">
        </div>
        <div class="trend-label">{{ run.version_id }}</div>
        <div class="trend-value">{{ "%.0f"|format(run.overall_accuracy * 100) }}%</div>
      </div>
      {% endfor %}
    </div>
    <div style="font-size:11px;color:#aaa;display:flex;gap:16px">
      <span>■ <span style="color:#28a745">current</span></span>
      <span>■ <span style="color:#6c757d">baseline</span></span>
      <span>■ <span style="color:#dc3545">critical</span></span>
      <span>■ <span style="color:#4a90d9">pass</span></span>
    </div>
  </div>
  {% endif %}
  <!-- DRIFT DETECTION -->
  {% if drift and drift.status != 'insufficient_data' %}
  <div class="card">
    <div class="card-title">Drift detection (rolling {{ drift.window_size }}-run window)</div>
    
    <div style="display:flex;gap:24px;flex-wrap:wrap;margin-bottom:16px">
      <div>
        <div style="font-size:11px;color:#888;text-transform:uppercase">Status</div>
        <div style="font-size:18px;font-weight:700;color:{{'#721c24' if drift.status=='drift_critical' else ('#856404' if drift.status=='drift_warn' else ('#155724' if drift.status=='improving' else '#383d41'))}}">
          {{ drift.status | upper | replace('_',' ') }}
        </div>
      </div>
      <div>
        <div style="font-size:11px;color:#888;text-transform:uppercase">Slope per run</div>
        <div style="font-size:18px;font-weight:700;color:{{'#721c24' if drift.accuracy_slope_per_run < -0.01 else ('#155724' if drift.accuracy_slope_per_run > 0.01 else '#383d41')}}">
          {{ "%+.3f"|format(drift.accuracy_slope_per_run) }}
        </div>
      </div>
      <div>
        <div style="font-size:11px;color:#888;text-transform:uppercase">Cumulative drift</div>
        <div style="font-size:18px;font-weight:700;color:{{'#721c24' if drift.cumulative_drift_over_window < -0.05 else '#383d41'}}">
          {{ "%+.1f"|format(drift.cumulative_drift_over_window * 100) }}%
        </div>
      </div>
      {% if drift.window_delta is not none %}
      <div>
        <div style="font-size:11px;color:#888;text-transform:uppercase">Window delta</div>
        <div style="font-size:18px;font-weight:700;color:{{'#721c24' if drift.window_delta < 0 else '#155724'}}">
          {{ "%+.1f"|format(drift.window_delta * 100) }}%
        </div>
      </div>
      {% endif %}
    </div>
    
    <!-- Mini sparkline of window runs -->
    {% if drift.run_accuracies %}
    <div style="display:flex;align-items:flex-end;gap:6px;height:60px;margin-bottom:8px">
      {% set min_a = drift.run_accuracies | min %}
      {% set max_a = drift.run_accuracies | max %}
      {% for acc in drift.run_accuracies | reverse %}
      {% set h = (((acc - min_a) / ((max_a - min_a) or 0.01)) * 50 + 10) | int %}
      <div style="flex:1;background:{{'#dc3545' if acc < 0.7 else ('#ffc107' if acc < 0.8 else '#28a745')}};height:{{h}}px;border-radius:3px 3px 0 0;min-height:4px" title="{{ '%.1f'|format(acc*100) }}%"></div>
      {% endfor %}
    </div>
    <div style="font-size:11px;color:#aaa">← older runs &nbsp;&nbsp; newer runs →</div>
    {% endif %}
  </div>
  {% endif %}

  <!-- REGRESSED CASES -->
  {% if comparison and comparison.regressed_cases %}
  <div class="card">
    <div class="card-title">
      Regressed cases
      <span style="font-weight:400;color:#888">
        ({{ comparison.regressed_count }} cases correct in baseline, wrong now)
      </span>
    </div>
    <table>
      <tr>
        <th>ID</th><th>Text</th><th>True label</th>
        <th>Baseline predicted</th><th>Now predicted</th>
        <th>Difficulty</th>
        {% if results[0].judge_score is defined %}<th>Judge score</th>{% endif %}
      </tr>
      {% for case in comparison.regressed_cases[:20] %}
      <tr class="regressed-row">
        <td style="color:#888">{{ case.id }}</td>
        <td class="text-cell">{{ case.text }}</td>
        <td><span class="label-chip chip-{{ case.true_label }}">{{ case.true_label }}</span></td>
        <td><span class="label-chip chip-{{ case.baseline_predicted }}">{{ case.baseline_predicted }}</span></td>
        <td><span class="label-chip chip-{{ case.current_predicted }}">{{ case.current_predicted }}</span></td>
        <td style="color:#888;font-size:12px">{{ case.difficulty }}</td>
        {% if case.judge_score is defined %}
        <td>
          <span style="font-weight:600;color:{{ '#28a745' if case.judge_score >= 4 else ('#ffc107' if case.judge_score == 3 else '#dc3545') }}">
            {{ case.judge_score }}/5
          </span>
        </td>
        {% endif %}
      </tr>
      {% endfor %}
    </table>
    {% if comparison.regressed_count > 20 %}
    <p style="font-size:12px;color:#888;margin-top:8px">
      Showing 20 of {{ comparison.regressed_count }} regressed cases.
    </p>
    {% endif %}
  </div>
  {% endif %}

  <!-- EDGE TYPE BREAKDOWN -->
  {% if scores.per_edge_type_accuracy %}
  <div class="card">
    <div class="card-title">Edge type accuracy breakdown</div>
    <div class="edge-grid">
      {% for edge_type, acc in scores.per_edge_type_accuracy.items() | sort(attribute='1') %}
      {% set cls = 'good' if acc >= 0.75 else ('mid' if acc >= 0.5 else 'bad') %}
      <div class="edge-item {{ cls }}">
        <div class="edge-name">{{ edge_type | replace('_', ' ') }}</div>
        <div class="edge-acc" style="color:{{ '#28a745' if acc >= 0.75 else ('#856404' if acc >= 0.5 else '#721c24') }}">
          {{ "%.0f"|format(acc * 100) }}%
        </div>
      </div>
      {% endfor %}
    </div>
  </div>
  {% endif %}

  <!-- LLM-AS-JUDGE DISTRIBUTION -->
  {% if scores.judge_distribution %}
  <div class="card">
    <div class="card-title">LLM-as-judge score distribution</div>
    {% set total_judged = scores.judge_distribution.values() | sum %}
    {% for score_val in [5, 4, 3, 2, 1] %}
    {% set count = scores.judge_distribution.get(score_val|string, 0) %}
    {% set pct = (count / total_judged * 100) | int if total_judged > 0 else 0 %}
    <div class="judge-bar-row">
      <div class="judge-bar-label">{{ score_val }}</div>
      <div class="judge-bar-track">
        <div class="judge-bar-fill" style="width:{{ pct }}%;background:{{ '#28a745' if score_val == 5 else ('#6fbf6f' if score_val == 4 else ('#ffc107' if score_val == 3 else ('#dc3545' if score_val <= 2 else '#dee2e6'))) }}"></div>
      </div>
      <div class="judge-bar-count">{{ count }}</div>
    </div>
    {% endfor %}
    <p style="font-size:12px;color:#888;margin-top:12px">
      Near-perfect (4–5): {{ "%.1f"|format(scores.near_perfect_rate * 100) }}% &nbsp;|&nbsp;
      Failure (1–2): {{ "%.1f"|format(scores.failure_rate * 100) }}%
    </p>
  </div>
  {% endif %}

  <!-- RUN HISTORY TABLE -->
  {% if history %}
  <div class="card">
    <div class="card-title">Run history</div>
    <table>
      <tr>
        <th>Run ID</th><th>Version</th><th>Timestamp</th>
        <th>Accuracy</th><th>Baseline</th>
      </tr>
      {% for run in history %}
      <tr style="{{ 'background:#f0f8ff' if run.run_id == run_id else '' }}">
        <td style="font-family:monospace;font-size:12px">{{ run.run_id }}</td>
        <td>{{ run.version_id }}</td>
        <td style="color:#888;font-size:12px">{{ run.timestamp[:19] | replace('T',' ') }}</td>
        <td>{{ "%.1f"|format(run.overall_accuracy * 100) }}%</td>
        <td>{{ "★" if run.is_baseline else "" }}</td>
      </tr>
      {% endfor %}
    </table>
  </div>
  {% endif %}

</div>
</body>
</html>"""

def generate_report(scores, comparison, results, history, output_path, run_id="unknown", drift=None):
    template = Template(TEMPLATE)
    html_content = template.render(
        scores=scores,
        comparison=comparison,
        results=results,
        history=history,
        run_id=run_id,
        drift=drift
    )
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    return html_content
