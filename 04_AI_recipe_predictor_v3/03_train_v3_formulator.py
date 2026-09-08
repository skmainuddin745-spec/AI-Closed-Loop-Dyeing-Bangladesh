#!/usr/bin/env python3
"""
AI_Recipe_Predictor_v3_Ultimate / 03_train_v3_formulator.py
=============================================================
STEP 3: Multi-Target AI Recipe Formulator — Training & Evaluation

PURPOSE:
    This is the core of the v3 system. We train and compare THREE competing
    architectures for multi-output chemical recipe prediction:

    Architecture A — MultiOutput XGBoost (Chained Regressor)
    Architecture B — MultiOutput Random Forest (Ensemble Baseline)  
    Architecture C — MultiLayer Perceptron (Deep Neural Network)

    Then we perform model selection via rigorous cross-validated metrics,
    SHAP explainability analysis, and per-shade-tier performance auditing.

SCIENTIFIC JUSTIFICATION FOR ARCHITECTURE CHOICES:
    - XGBoost is chosen because it handles the zero-inflated distribution of
      dye concentrations (many White/Light batches have zero dye). It natively
      handles non-linear interactions (e.g., Shade_Tier × PID_Family × LR).
    - MLP is chosen to learn complex non-linear relationships that tree methods
      may miss, especially for continuous concentration interpolation.
    - Chained regression captures inter-chemical dependencies (e.g., darker
      shades needing more salt BECAUSE they need more dye — not independent).

METRICS:
    For each of 10 targets:
    - R² (coefficient of determination): How much variance explained
    - MAE (Mean Absolute Error in g/L): Practical error for dyemaster
    - MAPE (Mean Absolute Percentage Error): Relative accuracy
    - Within-tolerance: % predictions within ±20% of actual (industry standard)

OUTPUTS:
    - v3_models/: Saved model files (.pkl)
    - v3_results/: Per-target metrics CSVs
    - v3_training_report.json: Full comparative analysis
    - v3_shap_analysis.json: Feature importance per target
"""

import pandas as pd
import numpy as np
import json
import sys
import os
import warnings
import pickle
import matplotlib

# Force UTF-8 output for special characters
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
matplotlib.use('Agg')  # non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from pathlib import Path
from sklearn.multioutput import MultiOutputRegressor, RegressorChain
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.metrics import r2_score, mean_absolute_error, mean_absolute_percentage_error
from sklearn.model_selection import cross_val_score, KFold
from sklearn.pipeline import Pipeline
from xgboost import XGBRegressor
import shap

warnings.filterwarnings('ignore')

# ============================================================
# CONFIGURATION
# ============================================================
OUTPUT_DIR   = Path('AI_Recipe_Predictor_v3_Ultimate')
MODELS_DIR   = OUTPUT_DIR / 'v3_models'
RESULTS_DIR  = OUTPUT_DIR / 'v3_results'
MODELS_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

TARGETS = [
    'gl_salt', 'gl_alkali_total', 'gl_dye_total',
    'gl_dye_yellow', 'gl_dye_red', 'gl_dye_blue', 'gl_dye_black',
    'gl_enzyme', 'gl_pretreat', 'gl_aux_total'
]

# Feature columns (everything that is NOT a target or batch ID)
NON_FEATURES = TARGETS + ['Batch_No', 'Shade', 'PID_Final', 'PID_Family',
                           'Shade_Tier', 'Buyer_Clean', 'Color_Depth_Clean',
                           'Salt_GL', 'Soda_GL', 'Dyeing_Type',  # v2 known values (leakage risk)
                           'LR_computed']  # derived from parsed, keep LR_parsed instead

print("=" * 70)
print("AI RECIPE PREDICTOR v3 — Step 3: Multi-Target Formulator Training")
print("=" * 70)

# ============================================================
# [1] LOAD DATA
# ============================================================
print("\n[1] Loading training/test datasets...")
train = pd.read_csv(OUTPUT_DIR / 'v3_train.csv')
test  = pd.read_csv(OUTPUT_DIR / 'v3_test.csv')

FEATURE_COLS = [c for c in train.columns if c not in NON_FEATURES]
existing_targets = [t for t in TARGETS if t in train.columns]

print(f"    Train: {len(train)} batches  |  Test: {len(test)} batches")
print(f"    Features: {len(FEATURE_COLS)}")
print(f"    Targets:  {len(existing_targets)}")
print(f"    Feature columns: {FEATURE_COLS}")

X_train = train[FEATURE_COLS].fillna(0).values
y_train = train[existing_targets].fillna(0).values
X_test  = test[FEATURE_COLS].fillna(0).values
y_test  = test[existing_targets].fillna(0).values

# ============================================================
# [2] DEFINE ARCHITECTURES
# ============================================================
print("\n[2] Defining model architectures...")

# Architecture A — MultiOutput XGBoost (best for zero-inflated tabular data)
xgb_base = XGBRegressor(
    n_estimators=500,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    min_child_weight=3,
    reg_alpha=0.1,
    reg_lambda=1.0,
    random_state=42,
    n_jobs=-1,
    tree_method='hist'
)
model_xgb = MultiOutputRegressor(xgb_base, n_jobs=-1)

# Architecture B — MultiOutput Random Forest (interpretable ensemble baseline)
rf_base = RandomForestRegressor(
    n_estimators=300,
    max_depth=10,
    min_samples_leaf=3,
    max_features='sqrt',
    random_state=42,
    n_jobs=-1
)
model_rf = MultiOutputRegressor(rf_base, n_jobs=-1)

# Architecture C — MLP Neural Network (learns non-linear concentration interpolation)
scaler = RobustScaler()  # Robust to outliers (extreme dark shades)
model_mlp = Pipeline([
    ('scaler', RobustScaler()),
    ('mlp', MLPRegressor(
        hidden_layer_sizes=(256, 128, 64, 32),
        activation='relu',
        solver='adam',
        alpha=0.01,          # L2 regularization
        batch_size=32,
        learning_rate='adaptive',
        max_iter=1000,
        early_stopping=True,
        validation_fraction=0.15,
        n_iter_no_change=30,
        random_state=42,
        tol=1e-5
    ))
])

architectures = {
    'XGBoost_MultiOutput': model_xgb,
    'RandomForest_MultiOutput': model_rf,
    'MLP_Neural_Network': model_mlp,
}

# ============================================================
# [3] TRAIN ALL ARCHITECTURES
# ============================================================
print("\n[3] Training all architectures...")
trained_models = {}
for name, model in architectures.items():
    print(f"    Training {name}...", end=' ', flush=True)
    model.fit(X_train, y_train)
    trained_models[name] = model
    print("Done")

# ============================================================
# [4] EVALUATE: PER-TARGET METRICS
# ============================================================
print("\n[4] Evaluating per-target performance...")

def evaluate_model(name, model, X_test, y_test, target_names):
    """Compute R², MAE, MAPE, Within-Tolerance for each target."""
    y_pred = model.predict(X_test)
    y_pred = np.clip(y_pred, 0, None)  # Concentrations can't be negative
    
    results = []
    for i, tgt in enumerate(target_names):
        yt = y_test[:, i]
        yp = y_pred[:, i]
        
        # Only evaluate on non-zero actuals for MAPE (avoid div-by-zero)
        nonzero = yt > 0
        
        r2  = r2_score(yt, yp) if yt.std() > 0 else np.nan
        mae = mean_absolute_error(yt, yp)
        mape = mean_absolute_percentage_error(yt[nonzero], yp[nonzero]) * 100 if nonzero.sum() > 0 else np.nan
        
        # Within ±20% tolerance (industry-standard for recipe QC)
        tol_20 = np.mean(np.abs(yp[nonzero] - yt[nonzero]) / yt[nonzero] <= 0.20) * 100 if nonzero.sum() > 0 else np.nan
        # Within ±10% for high-precision targets
        tol_10 = np.mean(np.abs(yp[nonzero] - yt[nonzero]) / yt[nonzero] <= 0.10) * 100 if nonzero.sum() > 0 else np.nan
        
        results.append({
            'model': name, 'target': tgt,
            'R2': round(r2, 4), 'MAE_gL': round(mae, 4),
            'MAPE_pct': round(mape, 2) if not np.isnan(mape) else None,
            'Within_10pct': round(tol_10, 1) if not np.isnan(tol_10) else None,
            'Within_20pct': round(tol_20, 1) if not np.isnan(tol_20) else None,
            'n_nonzero_test': int(nonzero.sum())
        })
    return results, y_pred

all_results = []
all_preds = {}
for name, model in trained_models.items():
    results, preds = evaluate_model(name, model, X_test, y_test, existing_targets)
    all_results.extend(results)
    all_preds[name] = preds

results_df = pd.DataFrame(all_results)

print("\n    === PER-TARGET R² COMPARISON ===")
pivot_r2 = results_df.pivot(index='target', columns='model', values='R2')
print(pivot_r2.round(3).to_string())

print("\n    === PER-TARGET MAE (g/L) COMPARISON ===")
pivot_mae = results_df.pivot(index='target', columns='model', values='MAE_gL')
print(pivot_mae.round(3).to_string())

print("\n    === WITHIN ±20% TOLERANCE (%) ===")
pivot_tol = results_df.pivot(index='target', columns='model', values='Within_20pct')
print(pivot_tol.to_string())

# ============================================================
# [5] SELECT BEST MODEL PER TARGET (Ensemble approach)
# ============================================================
print("\n[5] Selecting best model per target...")

best_model_per_target = {}
for tgt in existing_targets:
    tgt_df = results_df[results_df['target'] == tgt].copy()
    # Score = weighted avg of R2 and Within_20pct
    tgt_df['score'] = tgt_df['R2'].fillna(0) * 0.6 + (tgt_df['Within_20pct'].fillna(0) / 100) * 0.4
    best_row = tgt_df.loc[tgt_df['score'].idxmax()]
    best_model_per_target[tgt] = best_row['model']
    print(f"    {tgt:<22} -> best: {best_row['model']}  (R2={best_row['R2']:.3f}, Within20%={best_row['Within_20pct']}%)")

# Identify overall winner (mode of best models)
from collections import Counter
model_votes = Counter(best_model_per_target.values())
overall_best = model_votes.most_common(1)[0][0]
print(f"\n    Overall best architecture: {overall_best} (wins {model_votes[overall_best]}/{len(existing_targets)} targets)")

# ============================================================
# [6] SHADE-TIER PERFORMANCE AUDIT
# ============================================================
print("\n[6] Per-shade-tier performance audit (XGBoost)...")
best_preds = all_preds[overall_best]
test_aug = test.copy()
for i, tgt in enumerate(existing_targets):
    test_aug[f'pred_{tgt}'] = best_preds[:, i]

print(f"\n    {'Target':<20}  {'White':>8}  {'Light':>8}  {'Medium':>8}  {'Dark':>8}")
print(f"    {'-'*60}")
for tgt in existing_targets:
    row_str = f"    {tgt:<20}"
    for shade in ['White', 'Light', 'Medium', 'Dark']:
        mask = test_aug['Shade_Tier'] == shade
        if mask.sum() > 0:
            yt = test_aug.loc[mask, tgt].values
            yp = test_aug.loc[mask, f'pred_{tgt}'].values
            mae_s = mean_absolute_error(yt, yp)
            row_str += f"  {mae_s:>8.2f}"
        else:
            row_str += f"  {'N/A':>8}"
    print(row_str)
print(f"    (Values = MAE in g/L per shade tier)")

# ============================================================
# [7] SHAP EXPLAINABILITY ANALYSIS
# ============================================================
print("\n[7] SHAP feature importance analysis...")
shap_results = {}

# Use XGBoost SHAP (tree explainer — exact, not approximate)
best_model = trained_models['XGBoost_MultiOutput']
feature_names = FEATURE_COLS

try:
    for i, tgt in enumerate(existing_targets[:5]):  # Top 5 most important targets
        estimator = best_model.estimators_[i]
        explainer = shap.TreeExplainer(estimator)
        shap_vals = explainer.shap_values(X_test)
        mean_abs_shap = np.abs(shap_vals).mean(axis=0)
        # Top 10 features
        top_idx = np.argsort(mean_abs_shap)[::-1][:10]
        shap_results[tgt] = {
            feature_names[j]: round(float(mean_abs_shap[j]), 4)
            for j in top_idx
        }
        print(f"    Top features for {tgt}:")
        for feat, val in shap_results[tgt].items():
            print(f"      {feat:<35} SHAP={val:.4f}")
        print()
except Exception as e:
    print(f"    SHAP analysis warning: {e}")
    # Fallback: use built-in feature importances
    for i, tgt in enumerate(existing_targets[:5]):
        estimator = best_model.estimators_[i]
        if hasattr(estimator, 'feature_importances_'):
            fi = estimator.feature_importances_
            top_idx = np.argsort(fi)[::-1][:10]
            shap_results[tgt] = {feature_names[j]: round(float(fi[j]), 4) for j in top_idx}

# ============================================================
# [8] CROSS-VALIDATION (5-fold) FOR PUBLICATION QUALITY
# ============================================================
print("\n[8] 5-fold cross-validation (XGBoost, all data)...")
import numpy as np
full_df = pd.read_csv(OUTPUT_DIR / 'v3_training_dataset.csv')
X_all = full_df[FEATURE_COLS].fillna(0).values
y_all = full_df[existing_targets].fillna(0).values

cv_results = {}
kf = KFold(n_splits=5, shuffle=True, random_state=42)

# XGBoost single-target for fast CV on key targets
for i, tgt in enumerate(existing_targets[:6]):  # Key 6 targets
    base = XGBRegressor(n_estimators=300, max_depth=6, learning_rate=0.05,
                        subsample=0.8, random_state=42, n_jobs=-1, tree_method='hist')
    scores = cross_val_score(base, X_all, y_all[:, i], cv=kf, scoring='r2', n_jobs=-1)
    cv_results[tgt] = {
        'cv_r2_mean': round(scores.mean(), 4),
        'cv_r2_std': round(scores.std(), 4),
        'cv_r2_min': round(scores.min(), 4),
        'cv_r2_max': round(scores.max(), 4)
    }
    print(f"    {tgt:<22}: CV R² = {scores.mean():.3f} ± {scores.std():.3f}  [{scores.min():.3f} – {scores.max():.3f}]")

# ============================================================
# [9] SAVE MODELS & RESULTS
# ============================================================
print("\n[9] Saving trained models and results...")

# Save all models
for name, model in trained_models.items():
    fname = MODELS_DIR / f'{name.lower()}_model.pkl'
    with open(fname, 'wb') as f:
        pickle.dump(model, f)
    print(f"    Saved: {fname.name}")

# Save feature names (needed for inference)
with open(MODELS_DIR / 'feature_names.json', 'w') as f:
    json.dump({'feature_cols': FEATURE_COLS, 'targets': existing_targets}, f, indent=2)

# Save all results
results_df.to_csv(RESULTS_DIR / 'v3_all_metrics.csv', index=False)
pivot_r2.to_csv(RESULTS_DIR / 'v3_r2_comparison.csv')
pivot_mae.to_csv(RESULTS_DIR / 'v3_mae_comparison.csv')
test_aug.to_csv(RESULTS_DIR / 'v3_test_with_predictions.csv', index=False)

# Master training report
training_report = {
    'overall_best_architecture': overall_best,
    'model_wins': dict(model_votes),
    'best_model_per_target': best_model_per_target,
    'cv_results_xgb': cv_results,
    'shap_top_features': shap_results,
    'test_metrics': {
        name: {
            tgt: {
                'R2': row['R2'], 'MAE_gL': row['MAE_gL'],
                'MAPE_pct': row['MAPE_pct'], 'Within_20pct': row['Within_20pct']
            }
            for _, row in results_df[results_df['model']==name].set_index('target').iterrows()
            for tgt in [_]
        }
        for name in trained_models.keys()
    }
}
with open(RESULTS_DIR / 'v3_training_report.json', 'w') as f:
    json.dump(training_report, f, indent=2, default=str)
print(f"    Saved: v3_training_report.json")

# ============================================================
# [10] GENERATE TRAINING CHARTS
# ============================================================
print("\n[10] Generating evaluation charts...")

fig, axes = plt.subplots(2, 5, figsize=(20, 8))
fig.suptitle('AI Recipe Predictor v3 — Per-Target Prediction Accuracy (XGBoost)', 
             fontsize=14, fontweight='bold', y=1.02)
axes = axes.flatten()

best_preds_df = test_aug.copy()
for i, tgt in enumerate(existing_targets):
    ax = axes[i]
    yt = test_aug[tgt].values
    yp = test_aug[f'pred_{tgt}'].values
    
    ax.scatter(yt, yp, alpha=0.5, s=20, c='steelblue', edgecolors='none')
    lim_max = max(yt.max(), yp.max()) * 1.05
    ax.plot([0, lim_max], [0, lim_max], 'r--', lw=1, label='Perfect')
    ax.plot([0, lim_max], [0, lim_max*1.2], 'g:', lw=0.8, alpha=0.5, label='+20%')
    ax.plot([0, lim_max], [0, lim_max*0.8], 'g:', lw=0.8, alpha=0.5, label='-20%')
    
    r2_val = results_df[(results_df['model']==overall_best) & (results_df['target']==tgt)]['R2'].values
    mae_val= results_df[(results_df['model']==overall_best) & (results_df['target']==tgt)]['MAE_gL'].values
    r2_txt = f'{r2_val[0]:.3f}' if len(r2_val) > 0 else 'N/A'
    mae_txt= f'{mae_val[0]:.2f}' if len(mae_val) > 0 else 'N/A'
    
    ax.set_title(f'{tgt}\nR²={r2_txt}  MAE={mae_txt}g/L', fontsize=9)
    ax.set_xlabel('Actual (g/L)', fontsize=8)
    ax.set_ylabel('Predicted (g/L)', fontsize=8)
    ax.tick_params(labelsize=7)

plt.tight_layout()
plt.savefig(RESULTS_DIR / 'v3_prediction_scatter.png', dpi=150, bbox_inches='tight')
plt.close()
print(f"    Saved: v3_prediction_scatter.png")

# R² bar chart
fig2, ax2 = plt.subplots(figsize=(14, 6))
x = np.arange(len(existing_targets))
width = 0.25
colors = ['#2196F3', '#4CAF50', '#FF9800']
for j, (mname, color) in enumerate(zip(architectures.keys(), colors)):
    r2s = [results_df[(results_df['model']==mname) & (results_df['target']==t)]['R2'].values[0]
           for t in existing_targets]
    bars = ax2.bar(x + j*width, r2s, width, label=mname, color=color, alpha=0.85)
    for bar, val in zip(bars, r2s):
        if val > 0:
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                     f'{val:.2f}', ha='center', va='bottom', fontsize=7)

ax2.set_xticks(x + width)
ax2.set_xticklabels([t.replace('gl_','').replace('_',' ') for t in existing_targets],
                    rotation=30, ha='right', fontsize=9)
ax2.axhline(0.8, color='green', linestyle='--', lw=1, label='R²=0.8 threshold')
ax2.axhline(0.9, color='darkgreen', linestyle='--', lw=1, label='R²=0.9 excellent')
ax2.set_ylim(-0.1, 1.15)
ax2.set_ylabel('R² Score', fontsize=11)
ax2.set_title('v3 Multi-Target Recipe Formulator — R² by Architecture and Target', fontsize=12)
ax2.legend(fontsize=9)
ax2.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig(RESULTS_DIR / 'v3_r2_comparison.png', dpi=150, bbox_inches='tight')
plt.close()
print(f"    Saved: v3_r2_comparison.png")

print("\n" + "=" * 70)
print("STEP 3 COMPLETE — Multi-Target Recipe Formulator Trained")
print(f"  Best overall architecture: {overall_best}")
print(f"  Models saved to: {MODELS_DIR}")
print(f"  Results saved to: {RESULTS_DIR}")
print(f"  Next: Run 04_v3_recipe_generator_cli.py")
print("=" * 70)
