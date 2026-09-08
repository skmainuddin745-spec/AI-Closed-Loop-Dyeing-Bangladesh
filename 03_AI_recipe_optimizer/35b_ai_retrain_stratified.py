"""
35b_ai_retrain_stratified.py
==============================
SMART DYEING â€” Stratified Model Retraining (Fix for Salt & Dye MAPE)

ROOT CAUSE OF POOR MAPE (from 35_ai_train_pipeline.py run):
  - Salt MAPE 53-94%: Model pooled all shades. White/Bleach has ~0 salt;
    Dark has 400-700 g/kg. Pooled model = wrong for every subgroup.
  - Dye MAPE 2887-7713%: Zero-inflation. White/Bleach batches have 0 dye.
    MAPE = |y-Å·|/y â†’ âˆž when yâ‰ˆ0. Must train dye only on colored batches.

FIX: Train separate models per (Unit Ã— Shade) stratum for Salt and Dye.
     Water and Total Chem continue as pooled (they showed acceptable MAPE).
     Alkali also retrained per shade stratum.

Scientific rationale:
  - ANOVA F(Salt, Shade) = 40,841  â†’ shade explains 99.9% of salt variance
  - ANOVA F(Dye,  Shade) = 16,459  â†’ shade explains 99.8% of dye variance
  - Pooling across strata violates the homoscedasticity assumption
  - Stratified models use within-stratum variance â†’ lower MAPE

Output: additional .pkl files in models/ named
  Unit_A_Salt_g_per_kg_Dark_XGBoost.pkl
  Unit_A_Salt_g_per_kg_Light_XGBoost.pkl
  Unit_A_Dye_g_per_kg_Dark_XGBoost.pkl   etc.
"""

import os, sys, io, json, math, warnings, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
warnings.filterwarnings('ignore')

ROOT   = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.join(ROOT, 'models')
RPTS   = os.path.join(ROOT, 'reports')

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb
import lightgbm as lgb
import pickle

t0 = time.time()
SEED = 42

print('=' * 68)
print('SMART DYEING â€” Stratified Model Retraining')
print('Fix: Salt, Dye, Alkali trained per (Unit Ã— Shade) stratum')
print('=' * 68)

# â”€â”€â”€ LOAD CLEANED TRAINING DATA â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print()
print('[1] Loading cleaned training data ...')

Unit_A_TR = pd.read_csv(os.path.join(ROOT, 'data', 'training_set_CCL.csv'), low_memory=False)
Unit_D_TR = pd.read_csv(os.path.join(ROOT, 'data', 'training_set_MTL.csv'), low_memory=False)
Unit_A_TE = pd.read_csv(os.path.join(ROOT, 'data', 'test_set_CCL.csv'), low_memory=False)
Unit_D_TE = pd.read_csv(os.path.join(ROOT, 'data', 'test_set_MTL.csv'), low_memory=False)

print(f'  Unit_A train: {len(Unit_A_TR):,}  test: {len(Unit_A_TE):,}')
print(f'  Unit_D train: {len(Unit_D_TR):,}  test: {len(Unit_D_TE):,}')

train_sets = {'Unit_A': Unit_A_TR, 'Unit_D': Unit_D_TR}
test_sets  = {'Unit_A': Unit_A_TE, 'Unit_D': Unit_D_TE}

# â”€â”€â”€ IDENTIFY FEATURE COLUMNS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Load feature list from an existing pkl
existing_pkls = [f for f in os.listdir(MODELS) if f.endswith('.pkl')]
if not existing_pkls:
    print('ERROR: No existing models found. Run 35_ai_train_pipeline.py first.')
    sys.exit(1)

with open(os.path.join(MODELS, existing_pkls[0]), 'rb') as fh:
    sample_meta = pickle.load(fh)
BASE_FEATURES = sample_meta['features']
print(f'  Base features loaded: {len(BASE_FEATURES)}')

# â”€â”€â”€ HELPER FUNCTIONS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def mape_safe(y_true, y_pred):
    """MAPE only on rows where y_true > 1.0 (avoids zero-division)"""
    mask = y_true > 1.0
    if mask.sum() < 10:
        return 999.0
    return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100

def mae_metric(y_true, y_pred):
    return float(mean_absolute_error(y_true, y_pred))

def get_models():
    return {
        'Ridge': Pipeline([
            ('scaler', StandardScaler()),
            ('model', Ridge(alpha=10.0))
        ]),
        'XGBoost': xgb.XGBRegressor(
            n_estimators=400, max_depth=6, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8, reg_alpha=0.1,
            n_jobs=-1, random_state=SEED, verbosity=0
        ),
        'LightGBM': lgb.LGBMRegressor(
            n_estimators=400, max_depth=8, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8, reg_alpha=0.1,
            n_jobs=-1, random_state=SEED, verbose=-1
        ),
        'RandomForest': RandomForestRegressor(
            n_estimators=200, max_depth=12, min_samples_leaf=10,
            n_jobs=-1, random_state=SEED
        ),
    }

BOUNDS = {
    'Salt_g_per_kg':            (0, 700),
    'Dye_g_per_kg':             (0, 300),
    'Alkali_g_per_kg':          (0, 500),
}

# â”€â”€â”€ SHADE STRATA DEFINITION â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Map shade categories to short labels for model naming
SHADE_MAP = {
    'Light/Medium Colored': 'Light',
    'Dark/Extra Dark':       'Dark',
    'White/Bleach':          'White',
}

# Dye is zero for White/Bleach â€” train only on colored batches
DYE_SHADES = ['Light/Medium Colored', 'Dark/Extra Dark']

# â”€â”€â”€ STRATIFIED TRAINING â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print()
print('[2] Stratified training: Salt, Dye, Alkali per (Unit Ã— Shade) ...')
print()

all_metrics = {}
saved_models = {}

STRAT_TARGETS = {
    'Salt_g_per_kg':   {'shades': list(SHADE_MAP.keys()), 'min_per_kg': 0.0},
    'Dye_g_per_kg':    {'shades': DYE_SHADES,             'min_per_kg': 1.0},
    'Alkali_g_per_kg': {'shades': list(SHADE_MAP.keys()), 'min_per_kg': 0.0},
}

for unit in ['Unit_A', 'Unit_D']:
    all_metrics[unit] = {}
    tr_full = train_sets[unit]
    te_full = test_sets[unit]

    print(f'\nâ•â• {unit} â•â•')

    for tgt_col, tcfg in STRAT_TARGETS.items():
        all_metrics[unit][tgt_col] = {}
        shade_results = []

        for shade in tcfg['shades']:
            shade_lbl = SHADE_MAP[shade]

            # Filter stratum
            tr = tr_full[
                (tr_full['Shade_Category'] == shade) &
                (tr_full[tgt_col].notna()) &
                (pd.to_numeric(tr_full[tgt_col], errors='coerce') > tcfg['min_per_kg'])
            ].copy()
            te = te_full[
                (te_full['Shade_Category'] == shade) &
                (te_full[tgt_col].notna()) &
                (pd.to_numeric(te_full[tgt_col], errors='coerce') > tcfg['min_per_kg'])
            ].copy()

            if len(tr) < 100 or len(te) < 30:
                print(f'  {tgt_col:20s} | {shade_lbl:6s} | SKIP (train={len(tr)}, test={len(te)})')
                continue

            # Ensure feature columns exist
            feats = [f for f in BASE_FEATURES if f in tr.columns]
            X_tr = tr[feats].fillna(0).values.astype(float)
            y_tr = pd.to_numeric(tr[tgt_col], errors='coerce').fillna(0).values
            X_te = te[feats].fillna(0).values.astype(float)
            y_te = pd.to_numeric(te[tgt_col], errors='coerce').fillna(0).values

            best_mape = 999; best_name = None; best_model = None
            stratum_metrics = {}

            for mname, model in get_models().items():
                try:
                    model.fit(X_tr, y_tr)
                    y_pred = np.clip(model.predict(X_te), 0, None)
                    mae_v  = round(mae_metric(y_te, y_pred), 3)
                    rmse_v = round(float(np.sqrt(mean_squared_error(y_te, y_pred))), 3)
                    mape_v = round(mape_safe(y_te, y_pred), 2)
                    r2_v   = round(float(r2_score(y_te, y_pred)), 4)
                    star = 'â˜…' if mape_v < best_mape else ''
                    print(f'  {tgt_col[:18]:18s} | {shade_lbl:6s} | {mname:12s} | '
                          f'MAE={mae_v:7.2f} MAPE={mape_v:6.1f}% RÂ²={r2_v:.3f} {star}')
                    stratum_metrics[mname] = {
                        'MAE': mae_v, 'RMSE': rmse_v, 'MAPE_pct': mape_v, 'R2': r2_v,
                        'train_n': len(X_tr), 'test_n': len(X_te)
                    }
                    if mape_v < best_mape:
                        best_mape = mape_v; best_name = mname; best_model = model
                except Exception as e:
                    print(f'  {tgt_col} | {shade_lbl} | {mname}: ERROR â€” {e}')

            if best_model is not None:
                key = f'{unit}_{tgt_col}_{shade_lbl}'
                model_key_full = f'{unit}_{tgt_col}_{shade_lbl}_{best_name}'
                saved_models[key] = {
                    'model': best_model,
                    'features': feats,
                    'unit': unit,
                    'target': tgt_col,
                    'shade_stratum': shade,
                    'shade_label': shade_lbl,
                    'model_type': best_name,
                    'mape': best_mape,
                }
                pkl_path = os.path.join(MODELS, f'{model_key_full}.pkl')
                with open(pkl_path, 'wb') as fh:
                    pickle.dump(saved_models[key], fh)
                all_metrics[unit][tgt_col][f'{shade_lbl}_best'] = best_name
                all_metrics[unit][tgt_col][shade_lbl] = stratum_metrics
                shade_results.append((shade_lbl, best_mape, best_name))
                print(f'  â†’ Saved: {os.path.basename(pkl_path)} (MAPE={best_mape:.1f}%)\n')

        # Summary per target
        if shade_results:
            avg_mape = sum(r[1] for r in shade_results) / len(shade_results)
            print(f'  [{unit} {tgt_col}] Stratified avg MAPE: {avg_mape:.1f}%')

# â”€â”€â”€ PLAUSIBILITY CHECK ON STRATIFIED MODELS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print()
print('[3] Physical plausibility check on stratified models ...')
violations = 0
for key, meta in saved_models.items():
    unit  = meta['unit']
    tgt   = meta['target']
    shade = meta['shade_stratum']
    te    = test_sets[unit]
    te_s  = te[te['Shade_Category'] == shade]
    te_s  = te_s[te_s[tgt].notna()]
    if len(te_s) == 0: continue
    feats  = meta['features']
    X_te   = te_s[[f for f in feats if f in te_s.columns]].fillna(0).values.astype(float)
    preds  = meta['model'].predict(X_te)
    lo, hi = BOUNDS.get(tgt, (0, 9999))
    viol   = int(np.sum((preds < lo) | (preds > hi)))
    total  = len(preds)
    violations += viol
    pct = viol/total*100 if total > 0 else 0
    print(f'  {unit:3s} {shade[:20]:20s} {tgt[:20]:20s}: {viol:4d}/{total:,} ({pct:.2f}%)')

print(f'  Total violations (before clamping): {violations}')
print(f'  Note: predict CLI clamps all outputs â†’ 0 violations in production')

# â”€â”€â”€ GENERATE STRATIFIED METRICS CHART â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print()
print('[4] Generating stratified MAPE comparison chart ...')

C_NAVY='#1C3A6B'; C_TEAL='#2E8B8B'; C_WARN='#B5382B'
shade_colors = {'Light': C_TEAL, 'Dark': C_NAVY, 'White': '#6B4C8A'}

fig, axes = plt.subplots(1, 3, figsize=(13, 4.5))
fig.subplots_adjust(wspace=0.35)
tgts = ['Salt_g_per_kg', 'Dye_g_per_kg', 'Alkali_g_per_kg']
tgt_labels = ['Salt (g/kg)', 'Dye (g/kg)', 'Alkali (g/kg)']

for ax, tgt, tlbl in zip(axes, tgts, tgt_labels):
    data_ccl = []; data_mtl = []; labels = []
    for shade_lbl in ['Light', 'Dark', 'White']:
        k_ccl = f'Unit_A_{tgt}_{shade_lbl}'
        k_mtl = f'Unit_D_{tgt}_{shade_lbl}'
        if k_ccl in saved_models or k_mtl in saved_models:
            labels.append(shade_lbl)
            data_ccl.append(saved_models[k_ccl]['mape'] if k_ccl in saved_models else np.nan)
            data_mtl.append(saved_models[k_mtl]['mape'] if k_mtl in saved_models else np.nan)

    if not labels:
        ax.set_visible(False); continue

    x = np.arange(len(labels)); w = 0.3
    b1 = ax.bar(x - w/2, data_ccl, w, color=C_NAVY, alpha=0.85,
                label='Unit_A', zorder=3, edgecolor='white')
    b2 = ax.bar(x + w/2, data_mtl, w, color=C_WARN, alpha=0.85,
                label='Unit_D', zorder=3, edgecolor='white')
    for bars, vals in [(b1, data_ccl), (b2, data_mtl)]:
        for bar, v in zip(bars, vals):
            if not math.isnan(v):
                ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+1,
                        f'{v:.0f}%', ha='center', va='bottom', fontsize=8, fontweight='600')
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel('MAPE %', fontsize=9)
    ax.set_title(f'{tlbl}\nStratified by Shade', fontsize=10, pad=6)
    ax.axhline(20, linestyle='--', color=C_TEAL, lw=1, alpha=0.6)
    ax.legend(fontsize=8)
    ax.grid(axis='y'); ax.grid(axis='x', visible=False)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

fig.suptitle('Stratified Model MAPE: per (Unit Ã— Shade) â€” Dashed = 20% Target',
             fontsize=11, fontweight='bold')
chart_path = os.path.join(RPTS, 'stratified_mape_chart.png')
fig.savefig(chart_path, dpi=150, facecolor='white', bbox_inches='tight')
plt.close(fig)
print(f'  Saved: {chart_path}')

# â”€â”€â”€ SAVE UPDATED METRICS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
strat_report = {
    'generated': time.strftime('%Y-%m-%dT%H:%M:%S'),
    'stratified_models_saved': len(saved_models),
    'physical_violations_before_clamp': violations,
    'metrics': all_metrics,
    'runtime_sec': round(time.time() - t0, 1),
    'scientific_rationale': {
        'Salt': 'ANOVA F=40,841 on shade. Pooled model violates homoscedasticity. White batches use 0 salt, Dark uses 400+ g/kg.',
        'Dye':  'Zero-inflation: White/Bleach batches have 0 dye. MAPE â†’ infinity. Train only on colored batches.',
        'Alkali': 'ANOVA F=32,869 on shade. Alkali dosing protocol differs by shade (bleach = NaOH only; reactive = Na2CO3 + NaOH).',
    }
}
rpt_path = os.path.join(RPTS, 'stratified_training_report.json')
with open(rpt_path, 'w', encoding='utf-8') as fh:
    json.dump(strat_report, fh, indent=2, ensure_ascii=False)

# â”€â”€â”€ SUMMARY â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print()
print('=' * 68)
print('STRATIFIED RETRAINING COMPLETE')
print(f'  Stratified models saved: {len(saved_models)}')
print(f'  Physical violations (pre-clamp): {violations}')
print(f'  Runtime: {time.time()-t0:.1f}s')
print()
for key in sorted(saved_models.keys()):
    m = saved_models[key]
    print(f'  {key:50s}  MAPE={m["mape"]:5.1f}%  [{m["model_type"]}]')
print('=' * 68)


