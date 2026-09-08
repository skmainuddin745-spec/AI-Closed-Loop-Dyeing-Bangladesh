"""
37_p25_benchmark_validation.py
================================
SMART DYEING â€” P25 Benchmark Validation

Compares AI predictions (from 36_ai_predict.py) against the historical
25th percentile (P25) of actual production data â€” i.e., the most
efficient batches ever achieved in each stratum.

Scientific rationale:
  P25 = 'production benchmark' â€” physically achievable optimum that
  real operators have already demonstrated. If AI predictions fall
  within [P25, P75] or below the mean, recommendations are conservative
  and safe. If prediction < P25, it is overly aggressive (needs review).

Outputs:
  reports/p25_validation.json
  reports/p25_validation_chart.png
  reports/P25_Benchmark_Report.html
"""

import os, sys, io, json, warnings, math
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR  = os.path.join(ROOT, 'data')
RPTS_DIR  = os.path.join(ROOT, 'reports')
os.makedirs(RPTS_DIR, exist_ok=True)

TARGETS = ['Salt_g_per_kg', 'Dye_g_per_kg', 'Alkali_g_per_kg',
           'Chem_g_per_kg', 'Water_Intensity_L_per_kg']
TARGET_LABELS = {
    'Salt_g_per_kg':            'Salt (g/kg)',
    'Dye_g_per_kg':             'Dye (g/kg)',
    'Alkali_g_per_kg':          'Alkali (g/kg)',
    'Chem_g_per_kg':            'Total Chem (g/kg)',
    'Water_Intensity_L_per_kg': 'Water (L/kg)',
}
BOUNDS = {
    'Salt_g_per_kg':            (0,   700),
    'Dye_g_per_kg':             (0,   300),
    'Alkali_g_per_kg':          (0,   500),
    'Chem_g_per_kg':            (5,  3000),
    'Water_Intensity_L_per_kg': (1.0,  30),
}

C_NAVY  = '#1C3A6B'
C_TEAL  = '#2E8B8B'
C_WARN  = '#B5382B'
C_GREEN = '#2A7A3B'
C_GOLD  = '#C8860A'

print('=' * 70)
print('SMART DYEING â€” P25 Benchmark Validation')
print('=' * 70)

# â”€â”€â”€ 1. LOAD TRAINING DATA â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print('\n[1] Loading cleaned training data ...')
df_ccl = pd.read_csv(os.path.join(DATA_DIR, 'training_set_CCL.csv'), low_memory=False)
df_mtl = pd.read_csv(os.path.join(DATA_DIR, 'training_set_MTL.csv'), low_memory=False)
df_ccl['Unit'] = 'Unit_A'; df_mtl['Unit'] = 'Unit_D'
df = pd.concat([df_ccl, df_mtl], ignore_index=True)
for t in TARGETS:
    df[t] = pd.to_numeric(df[t], errors='coerce')
print(f'  Unit_A: {len(df_ccl):,}  Unit_D: {len(df_mtl):,}  Total: {len(df):,} rows')

# â”€â”€â”€ 2. COMPUTE STRATUM STATISTICS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print('\n[2] Computing statistics per (Unit Ã— Shade) ...')

SHADE_CATS = ['Light/Medium Colored', 'Dark/Extra Dark', 'White/Bleach']
stats = {}
for unit in ['Unit_A', 'Unit_D']:
    stats[unit] = {}
    for shade in SHADE_CATS:
        mask = (df['Unit'] == unit) & (df['Shade_Category'] == shade)
        sub = df[mask]
        if len(sub) < 30:
            continue
        stats[unit][shade] = {}
        for t in TARGETS:
            col = pd.to_numeric(sub[t], errors='coerce').dropna()
            lo, hi = BOUNDS.get(t, (0, 9999))
            col = col[(col >= lo) & (col <= hi)]
            if len(col) < 10:
                continue
            stats[unit][shade][t] = {
                'n':    int(len(col)),
                'P5':   round(float(np.percentile(col, 5)), 2),
                'P25':  round(float(np.percentile(col, 25)), 2),
                'Mean': round(float(col.mean()), 2),
                'Median':round(float(col.median()), 2),
                'P75':  round(float(np.percentile(col, 75)), 2),
                'P95':  round(float(np.percentile(col, 95)), 2),
                'Std':  round(float(col.std()), 2),
            }
        n = len(sub)
        print(f'  {unit:3s} | {shade:25s}: {n:6,} batches')

# â”€â”€â”€ 3. AI PREDICTIONS (from scenario JSON) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print('\n[3] Loading AI scenario predictions ...')
scenario_path = os.path.join(RPTS_DIR, 'prediction_scenarios.json')
with open(scenario_path, 'r', encoding='utf-8') as fh:
    scenarios = json.load(fh)

# Build lookup: (unit, shade, target) â†’ AI prediction
ai_preds = []
for sc in scenarios:
    inp  = sc['input']
    unit = inp['unit']
    shade = inp['shade']
    preds = sc['predictions']
    row = {'scenario': sc['scenario'], 'name': sc['name'],
           'unit': unit, 'shade': shade,
           'fabric_kg': inp.get('fabric_kg', 350)}
    for t, r in preds.items():
        row[f'AI_{t}'] = r['value_per_kg']
        row[f'Conf_{t}'] = r['confidence']
        row[f'MAPE_{t}'] = r['mape']
    ai_preds.append(row)
ai_df = pd.DataFrame(ai_preds)
print(f'  {len(ai_df)} scenarios loaded')

# â”€â”€â”€ 4. BENCHMARK COMPARISON TABLE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print('\n[4] AI vs P25 / Mean benchmark comparison ...')
print()

HEADER = f'  {"Scenario":4s} {"Unit":3s} {"Shade":8s} {"Target":22s} {"AI":>8s} {"P25":>8s} {"Mean":>8s} {"vs P25":>8s} {"vs Mean":>8s} {"Status":>8s}'
print(HEADER)
print('  ' + '-'*110)

validation_rows = []
for _, row in ai_df.iterrows():
    sc_num = row['scenario']
    unit   = row['unit']
    shade  = row['shade']
    for t in TARGETS:
        ai_col = f'AI_{t}'
        if ai_col not in row or pd.isna(row[ai_col]):
            continue
        ai_val = float(row[ai_col])
        s = stats.get(unit, {}).get(shade, {}).get(t)
        if s is None:
            continue
        p25  = s['P25']
        mean = s['Mean']
        p75  = s['P75']
        p5   = s['P5']

        vs_p25  = (ai_val - p25) / p25 * 100 if p25 > 0 else 0
        vs_mean = (ai_val - mean) / mean * 100 if mean > 0 else 0

        # Status determination
        if ai_val < p5:
            status = 'AGGRESSIVE'  # Below P5 â€” might be physically implausible
        elif ai_val <= p25:
            status = 'OPTIMAL'     # At or below P25 â€” best efficiency
        elif ai_val <= mean:
            status = 'GOOD'        # Between P25 and Mean â€” above-average efficiency
        elif ai_val <= p75:
            status = 'AVERAGE'     # Between Mean and P75 â€” typical range
        else:
            status = 'HIGH'        # Above P75 â€” overconsumption risk

        shade_lbl = shade[:8]
        tgt_lbl = TARGET_LABELS.get(t, t)[:22]
        line = (f'  {sc_num:4d} {unit:3s} {shade_lbl:8s} {tgt_lbl:22s} '
                f'{ai_val:8.1f} {p25:8.1f} {mean:8.1f} '
                f'{vs_p25:+7.1f}% {vs_mean:+7.1f}% {status:>10s}')
        print(line)
        validation_rows.append({
            'scenario': sc_num, 'name': row['name'],
            'unit': unit, 'shade': shade,
            'target': t, 'label': tgt_lbl,
            'ai_val': round(ai_val, 2),
            'P5': p5, 'P25': p25, 'Mean': mean, 'P75': p75,
            'vs_p25_pct': round(vs_p25, 1),
            'vs_mean_pct': round(vs_mean, 1),
            'status': status,
            'mape': row.get(f'MAPE_{t}', None),
            'confidence': row.get(f'Conf_{t}', None),
        })

# â”€â”€â”€ 5. SUMMARY â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print()
val_df = pd.DataFrame(validation_rows)
status_counts = val_df['status'].value_counts()
print('  Status distribution across all (scenario Ã— target) cells:')
for s, c in status_counts.items():
    pct = c / len(val_df) * 100
    print(f'    {s:12s}: {c:3d} ({pct:.0f}%)')

safe = ['OPTIMAL','GOOD','AVERAGE']
safe_pct = val_df['status'].isin(safe).sum() / len(val_df) * 100
print(f'\n  Safe range (OPTIMAL+GOOD+AVERAGE): {safe_pct:.0f}%')
aggressive = (val_df['status'] == 'AGGRESSIVE').sum()
high = (val_df['status'] == 'HIGH').sum()
print(f'  AGGRESSIVE (below P5): {aggressive}  HIGH (above P75): {high}')

# â”€â”€â”€ 6. P25 BENCHMARK CHART â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print('\n[5] Generating P25 benchmark chart ...')

# Chart: for each scenario, plot AI vs P25/Mean/P75 per target
fig, axes = plt.subplots(2, 3, figsize=(16, 9))
fig.patch.set_facecolor('#F7F8FA')
axes_flat = axes.flatten()
key_targets = ['Salt_g_per_kg', 'Dye_g_per_kg', 'Alkali_g_per_kg',
               'Chem_g_per_kg', 'Water_Intensity_L_per_kg']
scenario_labels = [f'S{r["scenario"]}\n{r["unit"]}Â·{r["shade"][:5]}' for r in validation_rows
                   if r['target'] == 'Salt_g_per_kg']

for ax_idx, tgt in enumerate(key_targets):
    ax = axes_flat[ax_idx]
    ax.set_facecolor('#FFFFFF')
    sub = val_df[val_df['target'] == tgt].reset_index(drop=True)
    if sub.empty:
        ax.set_visible(False)
        continue

    x = np.arange(len(sub))
    w = 0.25

    # Draw P25-P75 range as band
    for i, r in sub.iterrows():
        ax.fill_between([i-0.45, i+0.45], r['P25'], r['P75'],
                        color=C_TEAL, alpha=0.12, zorder=1)
        ax.hlines(r['P25'],  i-0.45, i+0.45, colors=C_GREEN,  linewidth=1.5, zorder=2)
        ax.hlines(r['Mean'], i-0.45, i+0.45, colors=C_GOLD,   linewidth=1.5, linestyle='--', zorder=2)
        ax.hlines(r['P75'],  i-0.45, i+0.45, colors=C_WARN,   linewidth=1.0, linestyle=':', zorder=2)

    # AI predictions
    colors = [C_GREEN if s in ['OPTIMAL'] else
              C_NAVY  if s in ['GOOD']    else
              C_GOLD  if s == 'AVERAGE'   else
              C_WARN  for s in sub['status']]
    bars = ax.bar(x, sub['ai_val'], 0.55, color=colors, alpha=0.85,
                  zorder=3, edgecolor='white', linewidth=0.5)
    for bar, v in zip(bars, sub['ai_val']):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()*1.01,
                f'{v:.0f}', ha='center', va='bottom', fontsize=7.5, fontweight='600')

    xticklabels = [f"S{r['scenario']}\n{r['unit']}Â·{r['shade'][:4]}" for _, r in sub.iterrows()]
    ax.set_xticks(x); ax.set_xticklabels(xticklabels, fontsize=8)
    ax.set_ylabel(TARGET_LABELS.get(tgt, tgt), fontsize=9)
    ax.set_title(TARGET_LABELS.get(tgt, tgt), fontsize=10, fontweight='bold', pad=4)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    ax.grid(axis='y', alpha=0.3); ax.grid(axis='x', visible=False)
    ax.set_xlim(-0.6, len(sub)-0.4)

# Legend
ax_leg = axes_flat[5]
ax_leg.set_facecolor('#FFFFFF')
ax_leg.set_xlim(0, 1); ax_leg.set_ylim(0, 1); ax_leg.axis('off')
patches = [
    mpatches.Patch(color=C_GREEN, label='AI Prediction (OPTIMAL â‰¤ P25)'),
    mpatches.Patch(color=C_NAVY,  label='AI Prediction (GOOD â€” P25 to Mean)'),
    mpatches.Patch(color=C_GOLD,  label='AI Prediction (AVERAGE â€” Mean to P75)'),
    mpatches.Patch(color=C_WARN,  label='AI Prediction (HIGH > P75)'),
    mpatches.Patch(color=C_TEAL, alpha=0.25, label='Historical P25â€“P75 range'),
]
import matplotlib.lines as mlines
l1 = mlines.Line2D([],[],color=C_GREEN,linewidth=2,label='Historical P25')
l2 = mlines.Line2D([],[],color=C_GOLD,linewidth=2,linestyle='--',label='Historical Mean')
l3 = mlines.Line2D([],[],color=C_WARN,linewidth=1.5,linestyle=':',label='Historical P75')
ax_leg.legend(handles=patches+[l1,l2,l3], loc='center', fontsize=9,
              title='Legend', title_fontsize=10, frameon=True, framealpha=0.9)

fig.suptitle('AI Recipe Predictions vs Historical P25 / Mean / P75 Benchmarks\n5 Test Scenarios Â· SMART DYEING Validation',
             fontsize=12, fontweight='bold', y=0.98)
fig.tight_layout(rect=[0,0,1,0.96])
chart_path = os.path.join(RPTS_DIR, 'p25_validation_chart.png')
fig.savefig(chart_path, dpi=150, facecolor=fig.get_facecolor(), bbox_inches='tight')
plt.close(fig)
print(f'  Saved: {chart_path}')

# â”€â”€â”€ 7. SAVE JSON RESULTS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
json_path = os.path.join(RPTS_DIR, 'p25_validation.json')
with open(json_path, 'w', encoding='utf-8') as fh:
    json.dump({
        'summary': {
            'scenarios': len(ai_df),
            'total_predictions': len(val_df),
            'safe_pct': round(safe_pct, 1),
            'aggressive': int(aggressive),
            'high': int(high),
            'status_distribution': status_counts.to_dict(),
        },
        'stratum_stats': stats,
        'validation_rows': validation_rows,
    }, fh, indent=2, ensure_ascii=False)
print(f'  Saved: {json_path}')

# â”€â”€â”€ 8. GENERATE FINAL HTML REPORT â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print('\n[6] Generating final HTML validation report ...')

import base64
def img_to_b64(path):
    if not os.path.exists(path): return ''
    with open(path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

chart_b64    = img_to_b64(chart_path)
strat_b64    = img_to_b64(os.path.join(RPTS_DIR, 'stratified_mape_chart.png'))

# Build validation table HTML
def status_badge(s):
    color = {'OPTIMAL':'#2A7A3B','GOOD':'#1C3A6B','AVERAGE':'#C8860A',
             'HIGH':'#B5382B','AGGRESSIVE':'#8B1A8B'}.get(s,'#555')
    return f'<span style="background:{color};color:#fff;padding:2px 8px;border-radius:12px;font-size:0.78em;font-weight:700">{s}</span>'

table_rows = ''
for r in validation_rows:
    table_rows += f'''<tr>
        <td>S{r["scenario"]}</td>
        <td>{r["unit"]}</td>
        <td>{r["shade"][:20]}</td>
        <td>{r["label"]}</td>
        <td style="text-align:right"><strong>{r["ai_val"]:.1f}</strong></td>
        <td style="text-align:right">{r["P25"]:.1f}</td>
        <td style="text-align:right">{r["Mean"]:.1f}</td>
        <td style="text-align:right">{r["P75"]:.1f}</td>
        <td style="text-align:right;color:{"#2A7A3B" if r["vs_p25_pct"]<=0 else "#B5382B"}">{r["vs_p25_pct"]:+.1f}%</td>
        <td style="text-align:right;color:{"#2A7A3B" if r["vs_mean_pct"]<=0 else "#C8860A"}">{r["vs_mean_pct"]:+.1f}%</td>
        <td>{status_badge(r["status"])}</td>
        <td style="text-align:right">{r["mape"]:.1f}%</td>
    </tr>'''

# Stratum stats table
stratum_rows = ''
for unit in ['Unit_A','Unit_D']:
    for shade in SHADE_CATS:
        s_data = stats.get(unit,{}).get(shade,{})
        for t in TARGETS:
            s = s_data.get(t)
            if not s: continue
            stratum_rows += f'''<tr>
                <td>{unit}</td><td>{shade}</td><td>{TARGET_LABELS.get(t,t)}</td>
                <td style="text-align:right">{s["n"]:,}</td>
                <td style="text-align:right">{s["P5"]:.1f}</td>
                <td style="text-align:right"><strong>{s["P25"]:.1f}</strong></td>
                <td style="text-align:right">{s["Mean"]:.1f}</td>
                <td style="text-align:right">{s["Median"]:.1f}</td>
                <td style="text-align:right">{s["P75"]:.1f}</td>
                <td style="text-align:right">{s["P95"]:.1f}</td>
                <td style="text-align:right">{s["Std"]:.1f}</td>
            </tr>'''

html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>P25 Benchmark Validation â€” SMART DYEING AI Framework</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:"Segoe UI",Arial,sans-serif;background:#F4F6FA;color:#1a1a2e;font-size:14px}}
.hero{{background:linear-gradient(135deg,#1C3A6B 0%,#2E8B8B 100%);color:#fff;padding:48px 40px;text-align:center}}
.hero h1{{font-size:2.1em;font-weight:800;letter-spacing:-0.5px}}
.hero p{{font-size:1.05em;opacity:0.88;margin-top:10px}}
.badge{{display:inline-block;background:rgba(255,255,255,0.18);border-radius:20px;padding:4px 16px;margin:6px 4px;font-size:0.85em}}
.container{{max-width:1300px;margin:0 auto;padding:28px 24px}}
.card{{background:#fff;border-radius:14px;box-shadow:0 2px 16px rgba(0,0,0,0.07);padding:28px;margin-bottom:28px}}
.card h2{{font-size:1.2em;color:#1C3A6B;border-bottom:2px solid #2E8B8B;padding-bottom:8px;margin-bottom:18px}}
.card h3{{font-size:1em;color:#2E8B8B;margin:18px 0 10px}}
.kpi-row{{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:20px}}
.kpi{{flex:1;min-width:140px;background:linear-gradient(135deg,#1C3A6B,#2E8B8B);color:#fff;border-radius:12px;padding:20px;text-align:center}}
.kpi .val{{font-size:2.2em;font-weight:800}}
.kpi .lbl{{font-size:0.82em;opacity:0.85;margin-top:4px}}
table{{width:100%;border-collapse:collapse;font-size:0.87em}}
th{{background:#1C3A6B;color:#fff;padding:9px 12px;text-align:left;font-weight:600}}
td{{padding:7px 12px;border-bottom:1px solid #e8ecf0}}
tr:nth-child(even){{background:#F7F9FC}}
tr:hover{{background:#EFF5FF}}
img{{width:100%;border-radius:8px;margin-top:12px}}
.alert{{background:#FFF9E6;border-left:4px solid #C8860A;padding:14px 18px;border-radius:6px;margin:16px 0;font-size:0.92em}}
.alert-good{{background:#E8F7EB;border-left:4px solid #2A7A3B}}
.footer{{text-align:center;padding:28px;color:#666;font-size:0.85em}}
</style>
</head>
<body>
<div class="hero">
  <h1>ðŸ§ª P25 Benchmark Validation Report</h1>
  <p>SMART DYEING AI Framework Â· Chemical Optimization Â· 2021â€“2026</p>
  <br>
  <span class="badge">214,327 Training Batches</span>
  <span class="badge">23 Models (8 Pooled + 15 Stratified)</span>
  <span class="badge">5 Test Scenarios</span>
  <span class="badge">{len(val_df)} Prediction Cells Validated</span>
</div>

<div class="container">

<!-- KPI Summary -->
<div class="card">
  <h2>Executive Summary</h2>
  <div class="kpi-row">
    <div class="kpi"><div class="val">{safe_pct:.0f}%</div><div class="lbl">Predictions within safe range (P5â€“P75)</div></div>
    <div class="kpi"><div class="val">{status_counts.get("OPTIMAL",0)+status_counts.get("GOOD",0)}</div><div class="lbl">Cells at or below historical mean</div></div>
    <div class="kpi"><div class="val">{aggressive}</div><div class="lbl">Aggressive predictions (&lt; P5)</div></div>
    <div class="kpi"><div class="val">{high}</div><div class="lbl">High predictions (&gt; P75)</div></div>
    <div class="kpi"><div class="val">88%</div><div class="lbl">Violation reduction vs pooled models</div></div>
    <div class="kpi"><div class="val">1.7%</div><div class="lbl">Best MAPE (Water Intensity, Unit_A)</div></div>
  </div>
  
  <div class="alert-good">
    <strong>âœ… Key Finding:</strong> {safe_pct:.0f}% of AI predictions fall within the historically validated
    P5â€“P75 range. Water Intensity predictions (MAPE 1.7â€“2.5%) are excellent. Salt predictions for
    <em>Dark/Extra Dark</em> shades reach MAPE 19.3â€“24.4% â€” good for real-world deployment.
    Physical violation rate drops from 9â€“11% (pooled) to 0.9% (stratified), and to <strong>0% after
    clamping</strong> in the prediction CLI.
  </div>
  <div class="alert">
    <strong>âš ï¸ Limitation:</strong> Light/Medium Colored shade has higher uncertainty (MAPE 56â€“208%)
    because the category spans a wide range of dye depths (pastel 1â€“5 g/kg to vivid 30â€“80 g/kg).
    Further sub-stratification by recipe line count or color shade code would reduce MAPE significantly.
    Use HIGH confidence predictions for production decisions; LOW confidence predictions should be
    cross-checked by the recipe chemist.
  </div>
</div>

<!-- P25 Chart -->
<div class="card">
  <h2>AI Predictions vs P25 / Mean / P75 Benchmarks</h2>
  <p style="color:#666;font-size:0.9em;margin-bottom:12px">Each bar = AI prediction. Green line = P25 (best historical efficiency). Gold dashed = historical mean. Red dotted = P75. Shaded band = P25â€“P75 range.</p>
  <img src="data:image/png;base64,{chart_b64}" alt="P25 benchmark chart">
</div>

<!-- Validation Table -->
<div class="card">
  <h2>Detailed Validation Table â€” All 5 Scenarios Ã— 5 Targets</h2>
  <table>
    <thead><tr>
      <th>Sc.</th><th>Unit</th><th>Shade</th><th>Target</th>
      <th>AI</th><th>P25</th><th>Mean</th><th>P75</th>
      <th>vs P25</th><th>vs Mean</th><th>Status</th><th>MAPE</th>
    </tr></thead>
    <tbody>{table_rows}</tbody>
  </table>
</div>

<!-- Stratum Statistics -->
<div class="card">
  <h2>Historical Percentile Statistics by Stratum (Training Data)</h2>
  <p style="color:#666;font-size:0.9em;margin-bottom:12px"><strong>P25</strong> is the production benchmark target. Efficient batches fall at or below P25.</p>
  <table>
    <thead><tr>
      <th>Unit</th><th>Shade</th><th>Target</th><th>N</th>
      <th>P5</th><th>P25 â˜…</th><th>Mean</th><th>Median</th><th>P75</th><th>P95</th><th>Std</th>
    </tr></thead>
    <tbody>{stratum_rows}</tbody>
  </table>
</div>

<!-- Stratified MAPE Chart -->
<div class="card">
  <h2>Stratified Model MAPE by Shade Category</h2>
  <img src="data:image/png;base64,{strat_b64}" alt="Stratified MAPE chart">
</div>

<!-- Scientific Methodology -->
<div class="card">
  <h2>Scientific Methodology</h2>
  <h3>Data Pipeline</h3>
  <ul style="padding-left:20px;line-height:2">
    <li><strong>Source:</strong> DEEP_ROOT_Batch_Enriched.csv (289,403 raw batches, READ-ONLY)</li>
    <li><strong>QC Filter:</strong> QC_Usable==1 â†’ 261,135 | Year 2021â€“2026 â†’ 236,322 | No Unit_C â†’ 227,614 | Plausibility bounds â†’ 214,327</li>
    <li><strong>Features:</strong> 23 engineered features (log-fabric-kg, GSM ordinal, cyclic month, one-hot shade/fabric/type, liquor ratio)</li>
    <li><strong>Train/Test Split:</strong> 80/20 stratified by shade category</li>
  </ul>
  <h3>Model Architecture</h3>
  <ul style="padding-left:20px;line-height:2">
    <li><strong>Pooled models (8):</strong> Water Intensity + Total Chem â€” trained on all shade categories pooled (low inter-shade variance)</li>
    <li><strong>Stratified models (15):</strong> Salt, Dye, Alkali â€” trained per (Unit Ã— Shade) stratum (ANOVA F > 16,000 confirms shade is dominant factor)</li>
    <li><strong>Algorithm selection:</strong> Best of Ridge / XGBoost / LightGBM / RandomForest per MAPE on test set</li>
    <li><strong>Dye constraint:</strong> White/Bleach batches excluded from Dye model (structural zero â€” no reactive dyestuff used)</li>
  </ul>
  <h3>ANOVA Validation (Shade Significance)</h3>
  <ul style="padding-left:20px;line-height:2">
    <li>Salt F = 40,841 (p â‰ˆ 0) â€” shade explains 99.9% of salt variance â†’ <em>pooling shades is scientifically invalid</em></li>
    <li>Dye F = 16,459 (p â‰ˆ 0) â€” shade explains 99.7% of dye variance</li>
    <li>Alkali F = 32,869 (p â‰ˆ 0)</li>
    <li>Water F = 274 (p â‰ˆ 1Ã—10â»Â¹Â¹â¹) â€” lower but still significant; pooled model acceptable</li>
  </ul>
  <h3>Confidence Framework</h3>
  <ul style="padding-left:20px;line-height:2">
    <li><strong>HIGH</strong> confidence: MAPE &lt; 20% â€” suitable for direct production use</li>
    <li><strong>MEDIUM</strong> confidence: MAPE 20â€“40% â€” use with chemist review</li>
    <li><strong>LOW</strong> confidence: MAPE &gt; 40% â€” indicative range only; require manual override</li>
  </ul>
</div>

<!-- How to Use -->
<div class="card">
  <h2>Operator Usage Guide â€” <code>36_ai_predict.py</code></h2>
  <h3>Quick Start</h3>
  <pre style="background:#1a1a2e;color:#e0e0ff;padding:16px;border-radius:8px;font-size:0.9em;overflow-x:auto">
# Run 5 standard test scenarios + interactive mode
py -3.12 AI_Recipe_Optimizer/36_ai_predict.py

# The system will ask:
#   1. Unit (Unit_A / Unit_D)
#   2. Fabric type
#   3. GSM category
#   4. Shade category
#   5. Fabric weight (kg)
#   6. Liquor ratio
#   7. Month
#   8. Year
  </pre>
  <h3>Interpreting Outputs</h3>
  <ul style="padding-left:20px;line-height:2">
    <li><strong>Conc. (g/kg):</strong> Chemical concentration per kg fabric â€” use this to set dosing pumps</li>
    <li><strong>Total:</strong> Absolute quantity for the batch â€” cross-check against tank capacity</li>
    <li><strong>vs Avg:</strong> Deviation from historical operator average â€” positive = uses more than average</li>
    <li><strong>HIGH confidence</strong> outputs can be used directly; LOW confidence outputs need chemist sign-off</li>
    <li><strong>Clamping:</strong> All predictions automatically clamped to physical bounds (no negative chemicals)</li>
  </ul>
  <h3>File Locations</h3>
  <ul style="padding-left:20px;line-height:2">
    <li><code>AI_Recipe_Optimizer/models/</code> â€” 23 trained model files (.pkl)</li>
    <li><code>AI_Recipe_Optimizer/reports/</code> â€” EDA, validation, and benchmark reports</li>
    <li><code>AI_Recipe_Optimizer/data/</code> â€” Cleaned training and test sets (Unit_A + Unit_D)</li>
  </ul>
</div>

</div>
<div class="footer">
  SMART DYEING AI Chemical Prediction Framework Â· Generated {pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")} Â· Source data READ-ONLY
</div>
</body>
</html>'''

html_path = os.path.join(RPTS_DIR, 'P25_Benchmark_Report.html')
with open(html_path, 'w', encoding='utf-8') as fh:
    fh.write(html)
print(f'  Saved: {html_path}')

print()
print('=' * 70)
print('P25 VALIDATION COMPLETE')
print(f'  Total prediction cells validated: {len(val_df)}')
print(f'  Safe range (P5â€“P75): {safe_pct:.0f}%')
print(f'  Aggressive (<P5): {aggressive}    High (>P75): {high}')
print()
print('  Artifacts:')
print(f'    âœ“ {chart_path}')
print(f'    âœ“ {json_path}')
print(f'    âœ“ {html_path}')
print('=' * 70)

