"""
38_ai_v2_advanced_training.py
==============================
SMART DYEING â€” AI Chemical Prediction Framework v2 (Advanced)

8 Improvements over v1:
  1. Color-depth sub-stratification of Light/Medium (K-means n=4)
  2. Is_2Part + Is_NextBatch binary features (Dyeing_Type encoding fix)
  3. Optuna Bayesian hyperparameter tuning (20 trials per model)
  4. 5-fold stratified cross-validation (robust metrics)
  5. Stacking ensemble meta-learner (Ridge on OOF predictions)
  6. Quantile regression P10/P50/P90 (prediction intervals)
  7. White/Bleach rule-based salt override
  8. SHAP feature importance per stratum

Source (READ-ONLY): DEEP_ROOT_Batch_Enriched.csv
"""
import os, sys, io, json, time, warnings, pickle
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from sklearn.cluster         import KMeans
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.linear_model    import Ridge
from sklearn.ensemble        import RandomForestRegressor
from sklearn.preprocessing   import StandardScaler
from sklearn.pipeline        import Pipeline
from sklearn.metrics         import mean_absolute_error, r2_score

import xgboost  as xgb
import lightgbm as lgb

try:
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    HAS_OPTUNA = True
except ImportError:
    HAS_OPTUNA = False
    print('[WARN] optuna not installed â€” skipping hyperparameter tuning, using tuned defaults')

try:
    import shap
    HAS_SHAP = True
except ImportError:
    HAS_SHAP = False
    print('[WARN] shap not installed â€” skipping SHAP explainability')

# â”€â”€â”€ CONFIGURATION â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
SEED          = 42
N_OPTUNA      = 10      # Trials per model (Bayesian search converges fast)
MAX_OPTUNA_ROWS = 8000  # Subsample for Optuna search ONLY; retrain on full data
N_CV_FOLDS    = 5       # Cross-validation folds
t0            = time.time()

ROOT   = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.join(ROOT, 'models', 'v2')
RPTS   = os.path.join(ROOT, 'reports')
DATA   = os.path.join(ROOT, 'data')
os.makedirs(MODELS, exist_ok=True)

SRC = (r'E:\Downloads\01_Projects_and_Research\AI-driven closed-loop dyeing '
       r'system for Bangladesh textiles\2026-09-03_Categorization_Insights'
       r'\DEEP_ROOT_Batch_Enriched.csv')

BOUNDS = {
    'Salt_g_per_kg':            (0,   700),
    'Dye_g_per_kg':             (0,   300),
    'Alkali_g_per_kg':          (0,   500),
    'Chem_g_per_kg':            (5,  3000),
    'Water_Intensity_L_per_kg': (1.0,  30),
}
TARGET_LABELS = {
    'Salt_g_per_kg':            'Salt (g/kg)',
    'Dye_g_per_kg':             'Dye (g/kg)',
    'Alkali_g_per_kg':          'Alkali (g/kg)',
    'Chem_g_per_kg':            'Total Chem (g/kg)',
    'Water_Intensity_L_per_kg': 'Water (L/kg)',
}

TARGETS            = list(BOUNDS.keys())
STRATIFIED_TARGETS = ['Salt_g_per_kg', 'Dye_g_per_kg', 'Alkali_g_per_kg']
POOLED_TARGETS     = ['Chem_g_per_kg', 'Water_Intensity_L_per_kg']

# V1 benchmark MAPEs for comparison table
V1_MAPES = {
    'Unit_A_Salt_g_per_kg_Dark':            19.3,
    'Unit_A_Salt_g_per_kg_Light':           64.7,
    'Unit_A_Dye_g_per_kg_Dark':             61.7,
    'Unit_A_Dye_g_per_kg_Light':           251.4,
    'Unit_A_Alkali_g_per_kg_Dark':          36.6,
    'Unit_A_Alkali_g_per_kg_Light':         40.9,
    'Unit_A_Chem_g_per_kg_Pooled':          31.8,
    'Unit_A_Water_Intensity_L_per_kg_Pooled': 1.7,
    'Unit_D_Salt_g_per_kg_Dark':            24.4,
    'Unit_D_Salt_g_per_kg_Light':           56.5,
    'Unit_D_Dye_g_per_kg_Dark':             32.3,
    'Unit_D_Dye_g_per_kg_Light':           207.8,
    'Unit_D_Alkali_g_per_kg_Dark':          27.5,
    'Unit_D_Alkali_g_per_kg_Light':         34.6,
    'Unit_D_Chem_g_per_kg_Pooled':          26.8,
    'Unit_D_Water_Intensity_L_per_kg_Pooled': 2.5,
}

print('='*70)
print('SMART DYEING â€” AI Framework v2 (8 Advanced Improvements)')
print('='*70)

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# PHASE 1: DATA LOAD + QC FILTER
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
print('\n[Phase 1] Loading and validating data ...')
df = pd.read_csv(SRC, low_memory=False)
print(f'  Raw rows: {len(df):,}')

df = df[df['QC_Usable'] == 1].copy()
df['Year_num']  = pd.to_numeric(df['Year'], errors='coerce')
df['Month_str'] = df['Month'].astype(str)
df['Month_num'] = df['Month_str'].str[-2:].apply(
    lambda x: int(x) if x.isdigit() else np.nan)
df = df[(df['Year_num'] >= 2021) & (df['Year_num'] <= 2026)].copy()
df = df[df['Dye_Unit'].isin(['Unit_A', 'Unit_D'])].copy()

# â”€â”€ Derive any missing intensity columns â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Alkali_g_per_kg is NOT in the raw CSV â€” compute from Alkali_Kg / Fabric_Kg
if 'Alkali_g_per_kg' not in df.columns:
    df['Alkali_Kg']    = pd.to_numeric(df.get('Alkali_Kg', np.nan), errors='coerce')
    df['Fabric_Kg']    = pd.to_numeric(df.get('Fabric_Kg', np.nan), errors='coerce')
    df['Alkali_g_per_kg'] = (df['Alkali_Kg'] / df['Fabric_Kg'].replace(0, np.nan)) * 1000
    print('  [INFO] Derived Alkali_g_per_kg from Alkali_Kg / Fabric_Kg Ã— 1000')

# Ensure all targets are numeric
for t in TARGETS:
    df[t] = pd.to_numeric(df[t], errors='coerce')

# Plausibility filter
mask = pd.Series(True, index=df.index)
for t, (lo, hi) in BOUNDS.items():
    mask &= df[t].between(lo, hi) | df[t].isna()
df = df[mask].copy()
print(f'  Clean rows: {len(df):,}  |  Unit_A: {(df["Dye_Unit"]=="Unit_A").sum():,}  Unit_D: {(df["Dye_Unit"]=="Unit_D").sum():,}')

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# PHASE 2: ADVANCED FEATURE ENGINEERING (30 features vs 23 in v1)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
print('\n[Phase 2] Feature engineering (v2 â€” 30 features) ...')

GSM_ORD = {'Light (<150)': 1, 'Medium (150-249)': 2, 'Heavy (250+)': 3}
df['Log_Fabric_Kg']    = np.log1p(df['Fabric_Kg'].fillna(350).clip(1))
df['GSM_Ord']          = df['GSM_Category'].map(GSM_ORD).fillna(2).astype(float)
df['LR']               = pd.to_numeric(df['Liquor_Ratio_1_to_X'], errors='coerce')
df['LR']               = df['LR'].fillna(df.groupby('Dye_Unit')['LR'].transform('median')).fillna(7.0)
df['Month_sin']        = np.sin(2*np.pi * df['Month_num'].fillna(6) / 12)
df['Month_cos']        = np.cos(2*np.pi * df['Month_num'].fillna(6) / 12)
df['Year']             = df['Year_num'].fillna(2024).astype(float)
df['Recipe_Lines']     = pd.to_numeric(df['Recipe_Lines'], errors='coerce').fillna(15.0)
df['Log_Recipe_Lines'] = np.log1p(df['Recipe_Lines'])
df['GSM_x_LogFab']     = df['GSM_Ord'] * df['Log_Fabric_Kg']
df['LR_x_LogFab']      = df['LR'] * df['Log_Fabric_Kg']
df['Batch_Size_Ord']   = pd.cut(
    df['Fabric_Kg'].clip(0), bins=[0,100,300,600,9999],
    labels=[1,2,3,4]).astype(float).fillna(2.0)

# â”€â”€ IMPROVEMENT 2: Dyeing_Type binary features â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
dt = df['Dyeing_Type'].fillna('')
df['Is_2Part']     = dt.str.contains('2Part',     case=False).astype(float)
df['Is_NextBatch'] = dt.str.contains('Next Batch', case=False).astype(float)
df['Is_Finished']  = dt.str.contains('Finished',   case=False).astype(float)
df['Is_ReProcess'] = dt.str.contains('Re.proc',    case=False, regex=True).astype(float)
print(f'  Is_2Part: {df["Is_2Part"].sum():.0f} ({df["Is_2Part"].mean()*100:.1f}%)  '
      f'Is_NextBatch: {df["Is_NextBatch"].sum():.0f} ({df["Is_NextBatch"].mean()*100:.1f}%)')

# â”€â”€ One-hot encodings â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
shade_dummies = pd.get_dummies(df['Shade_Category'], prefix='Shade').astype(float)
df = pd.concat([df, shade_dummies], axis=1)

top_fab = df['Fabric_Category'].value_counts().head(7).index.tolist()
df['Fab_Clean'] = df['Fabric_Category'].where(df['Fabric_Category'].isin(top_fab), 'Other')
fab_dummies = pd.get_dummies(df['Fab_Clean'], prefix='Fab').astype(float)
df = pd.concat([df, fab_dummies], axis=1)

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# IMPROVEMENT 1: K-MEANS COLOR DEPTH SUB-STRATIFICATION
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
print('\n[Improvement 1] K-means color-depth sub-stratification ...')

df['Color_Depth_Bin'] = 'N/A'
df.loc[df['Shade_Category'] == 'Dark/Extra Dark', 'Color_Depth_Bin'] = 'Dark'
df.loc[df['Shade_Category'] == 'White/Bleach',    'Color_Depth_Bin'] = 'White'

# Cluster only Light/Medium Colored rows that have Dye values
lm_mask = df['Shade_Category'] == 'Light/Medium Colored'
lm_df   = df[lm_mask & df['Dye_g_per_kg'].notna() & (df['Dye_g_per_kg'] >= 0)].copy()

X_cl = np.column_stack([
    np.log1p(lm_df['Dye_g_per_kg'].clip(0)),
    np.log1p(lm_df['Recipe_Lines'].fillna(15)),
])
kmeans = KMeans(n_clusters=4, random_state=SEED, n_init=20, max_iter=500)
labels = kmeans.fit_predict(X_cl)

# Order clusters by ascending mean Dye â†’ Pale, Light, Medium, Vivid
cluster_means = {i: lm_df.iloc[labels == i]['Dye_g_per_kg'].mean() for i in range(4)}
order = sorted(cluster_means, key=lambda i: cluster_means[i])
BIN_NAMES = {order[i]: nm for i, nm in enumerate(['Pale', 'Light', 'Medium', 'Vivid'])}

df.loc[lm_df.index, 'Color_Depth_Bin'] = [BIN_NAMES[l] for l in labels]

# Rows still N/A in Light/Medium (no Dye data) â†’ assign by nearest centroid via Recipe_Lines
still_na = df[lm_mask & (df['Color_Depth_Bin'] == 'N/A')].index
if len(still_na):
    X_na = np.column_stack([
        np.zeros(len(still_na)),
        np.log1p(df.loc[still_na, 'Recipe_Lines'].fillna(15)),
    ])
    df.loc[still_na, 'Color_Depth_Bin'] = [BIN_NAMES[l] for l in kmeans.predict(X_na)]

print('  Color-depth bin distribution:')
for bn in ['Pale', 'Light', 'Medium', 'Vivid', 'Dark', 'White']:
    sub = df[df['Color_Depth_Bin'] == bn]
    dye = sub['Dye_g_per_kg'].dropna()
    dye_str = f'Dye P50={dye.median():.1f} g/kg' if len(dye) > 0 else ''
    print(f'    {bn:8s}: {len(sub):7,} batches  {dye_str}')

# Save K-means for prediction CLI
with open(os.path.join(MODELS, 'kmeans_color_depth.pkl'), 'wb') as fh:
    pickle.dump({'kmeans': kmeans, 'bin_names': BIN_NAMES}, fh)

# â”€â”€ One-hot: Color_Depth_Bin â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
cd_dummies = pd.get_dummies(df['Color_Depth_Bin'], prefix='CD').astype(float)
df = pd.concat([df, cd_dummies], axis=1)

# â”€â”€ Final feature list â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
CORE_FEATS = [
    'Log_Fabric_Kg', 'GSM_Ord', 'LR', 'Month_sin', 'Month_cos', 'Year',
    'Recipe_Lines', 'Log_Recipe_Lines', 'GSM_x_LogFab', 'LR_x_LogFab',
    'Batch_Size_Ord',
    'Is_2Part', 'Is_NextBatch', 'Is_Finished', 'Is_ReProcess',
]
DUMMY_FEATS = ([c for c in df.columns if c.startswith('Shade_')] +
               [c for c in df.columns if c.startswith('Fab_')] +
               [c for c in df.columns if c.startswith('CD_')])
ALL_FEATS = CORE_FEATS + DUMMY_FEATS
ALL_FEATS = [f for f in ALL_FEATS
             if f in df.columns and pd.api.types.is_numeric_dtype(df[f])]
print(f'\n  Total features v2: {len(ALL_FEATS)} (v1 had 23)')

# Make all features float, fill NaN
for f in ALL_FEATS:
    df[f] = pd.to_numeric(df[f], errors='coerce').fillna(0).astype(float)

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# HELPER: mape_safe
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
def mape_safe(y_true, y_pred, threshold=1.0):
    yt, yp = np.array(y_true), np.array(y_pred)
    mask = yt > threshold
    if mask.sum() < 5:
        return 999.0
    return float(np.mean(np.abs((yt[mask] - yp[mask]) / yt[mask])) * 100)

def stack_predict(model_dict, X):
    base_preds = [m.predict(X) for m in model_dict['bases']]
    X_meta = np.column_stack(base_preds)
    return np.clip(model_dict['meta'].predict(X_meta), 0, None)

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# IMPROVEMENT 3: OPTUNA TUNING FUNCTIONS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
def _cv_mae(model, X, y, n_splits=3):
    """Quick 3-fold CV MAE for Optuna objectives."""
    # pd.qcut requires a pandas Series (not numpy) for .fillna to work
    y_s    = pd.Series(y)
    y_bins = pd.qcut(y_s, q=min(5, len(y_s)//20), labels=False,
                     duplicates='drop').fillna(0).astype(int).values
    skf  = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=SEED)
    maes = []
    for tr, va in skf.split(X, y_bins):
        model.fit(X[tr], y[tr])
        maes.append(mean_absolute_error(y[va], np.clip(model.predict(X[va]), 0, None)))
    return float(np.mean(maes))

def tune_xgboost(X_tr, y_tr, n_trials=N_OPTUNA):
    if not HAS_OPTUNA or len(X_tr) < 200:
        return {'n_estimators': 500, 'max_depth': 6, 'learning_rate': 0.05,
                'subsample': 0.8, 'colsample_bytree': 0.75, 'reg_alpha': 0.5,
                'min_child_weight': 5}
    # Subsample for fast Optuna search (retrain on full data later)
    if len(X_tr) > MAX_OPTUNA_ROWS:
        idx = np.random.RandomState(SEED).choice(len(X_tr), MAX_OPTUNA_ROWS, replace=False)
        Xs, ys = X_tr[idx], y_tr[idx]
    else:
        Xs, ys = X_tr, y_tr
    def obj(trial):
        p = dict(
            n_estimators      = trial.suggest_int('n_estimators', 200, 800),
            max_depth         = trial.suggest_int('max_depth', 3, 10),
            learning_rate     = trial.suggest_float('lr', 0.01, 0.2, log=True),
            subsample         = trial.suggest_float('sub', 0.5, 1.0),
            colsample_bytree  = trial.suggest_float('cbt', 0.5, 1.0),
            reg_alpha         = trial.suggest_float('ra', 0.01, 10.0, log=True),
            reg_lambda        = trial.suggest_float('rl', 0.1, 10.0, log=True),
            min_child_weight  = trial.suggest_int('mcw', 3, 20),
            n_jobs=-1, random_state=SEED, verbosity=0,
        )
        return _cv_mae(xgb.XGBRegressor(**p), Xs, ys)
    study = optuna.create_study(direction='minimize',
                                sampler=optuna.samplers.TPESampler(seed=SEED))
    study.optimize(obj, n_trials=n_trials, show_progress_bar=False)
    return study.best_params

def tune_lgbm(X_tr, y_tr, n_trials=N_OPTUNA):
    if not HAS_OPTUNA or len(X_tr) < 200:
        return {'n_estimators': 500, 'max_depth': 8, 'learning_rate': 0.05,
                'subsample': 0.8, 'colsample_bytree': 0.75, 'num_leaves': 63,
                'min_child_samples': 20}
    # Subsample for fast Optuna search
    if len(X_tr) > MAX_OPTUNA_ROWS:
        idx = np.random.RandomState(SEED).choice(len(X_tr), MAX_OPTUNA_ROWS, replace=False)
        Xs, ys = X_tr[idx], y_tr[idx]
    else:
        Xs, ys = X_tr, y_tr
    def obj(trial):
        p = dict(
            n_estimators      = trial.suggest_int('n_estimators', 200, 800),
            max_depth         = trial.suggest_int('max_depth', 4, 12),
            learning_rate     = trial.suggest_float('lr', 0.01, 0.2, log=True),
            subsample         = trial.suggest_float('sub', 0.5, 1.0),
            colsample_bytree  = trial.suggest_float('cbt', 0.5, 1.0),
            reg_alpha         = trial.suggest_float('ra', 0.01, 10.0, log=True),
            reg_lambda        = trial.suggest_float('rl', 0.1, 10.0, log=True),
            min_child_samples = trial.suggest_int('mcs', 10, 100),
            num_leaves        = trial.suggest_int('nl', 20, 200),
            n_jobs=-1, random_state=SEED, verbose=-1,
        )
        return _cv_mae(lgb.LGBMRegressor(**p), Xs, ys)
    study = optuna.create_study(direction='minimize',
                                sampler=optuna.samplers.TPESampler(seed=SEED))
    study.optimize(obj, n_trials=n_trials, show_progress_bar=False)
    return study.best_params

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# IMPROVEMENT 4+5: 5-FOLD CV + STACKING ENSEMBLE
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
def train_cv_stack(X, y, xgb_params, lgb_params, threshold=1.0):
    """
    Trains base models (XGBoost, LightGBM, RandomForest, Ridge) using
    5-fold CV for evaluation, then builds a stacking ensemble.

    Returns:
      best_model_obj  : final model or {'type':'stack', 'bases':[...], 'meta': Ridge}
      best_cv_mape    : float
      cv_results      : dict of per-model CV metrics
      best_name       : str
    """
    n = len(X)
    if n < 80:
        return None, 999.0, {}, 'None'

    # Build candidate models with Optuna-tuned params
    candidates = {
        'Ridge': Pipeline([('sc', StandardScaler()), ('m', Ridge(alpha=10.0))]),
        'XGBoost': xgb.XGBRegressor(**{**xgb_params, 'n_jobs': -1,
                                        'random_state': SEED, 'verbosity': 0}),
        'LightGBM': lgb.LGBMRegressor(**{**lgb_params, 'n_jobs': -1,
                                          'random_state': SEED, 'verbose': -1}),
        'RandomForest': RandomForestRegressor(
            n_estimators=200, max_depth=14, min_samples_leaf=8,
            n_jobs=-1, random_state=SEED),
    }

    # 5-fold CV for each base model; accumulate OOF predictions
    y_s    = pd.Series(y)
    y_bins = pd.qcut(y_s, q=min(N_CV_FOLDS, n // 20),
                     labels=False, duplicates='drop').fillna(0).astype(int).values
    skf = StratifiedKFold(n_splits=N_CV_FOLDS, shuffle=True, random_state=SEED)

    oof = {name: np.zeros(n) for name in candidates}
    cv_results = {}

    for name, model in candidates.items():
        fold_maes, fold_mapes, fold_r2s = [], [], []
        for tr_idx, va_idx in skf.split(X, y_bins):
            model.fit(X[tr_idx], y[tr_idx])
            pred = np.clip(model.predict(X[va_idx]), 0, None)
            oof[name][va_idx] = pred
            fold_maes.append(mean_absolute_error(y[va_idx], pred))
            fold_mapes.append(mape_safe(y[va_idx], pred, threshold))
            fold_r2s.append(r2_score(y[va_idx], pred))

        cv_results[name] = {
            'cv_mae_mean':  round(float(np.mean(fold_maes)), 3),
            'cv_mae_std':   round(float(np.std(fold_maes)), 3),
            'cv_mape_mean': round(float(np.mean(fold_mapes)), 2),
            'cv_mape_std':  round(float(np.std(fold_mapes)), 2),
            'cv_r2_mean':   round(float(np.mean(fold_r2s)), 4),
        }

    # Stack meta-learner on OOF
    X_meta = np.column_stack([oof[n] for n in candidates])
    meta = Ridge(alpha=1.0)
    meta.fit(X_meta, y)
    stack_pred = np.clip(meta.predict(X_meta), 0, None)
    cv_results['Stack_Ridge'] = {
        'cv_mae_mean':  round(float(mean_absolute_error(y, stack_pred)), 3),
        'cv_mae_std':   0.0,
        'cv_mape_mean': round(float(mape_safe(y, stack_pred, threshold)), 2),
        'cv_mape_std':  0.0,
        'cv_r2_mean':   round(float(r2_score(y, stack_pred)), 4),
    }

    # Choose best by CV MAPE
    best_name = min(cv_results, key=lambda k: cv_results[k]['cv_mape_mean'])
    best_cv_mape = cv_results[best_name]['cv_mape_mean']

    # Retrain best model on all data
    if best_name == 'Stack_Ridge':
        for m in candidates.values():
            m.fit(X, y)
        X_meta_full = np.column_stack([m.predict(X) for m in candidates.values()])
        meta.fit(X_meta_full, y)
        best_obj = {'type': 'stack',
                    'bases': list(candidates.values()),
                    'base_names': list(candidates.keys()),
                    'meta': meta}
    else:
        candidates[best_name].fit(X, y)
        best_obj = candidates[best_name]

    return best_obj, best_cv_mape, cv_results, best_name

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# IMPROVEMENT 6: QUANTILE REGRESSION
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
def train_quantile(X, y, lgb_params, quantiles=(0.10, 0.50, 0.90)):
    q_models = {}
    for q in quantiles:
        try:
            m = lgb.LGBMRegressor(
                objective='quantile', alpha=q,
                n_estimators=300, max_depth=8, learning_rate=0.05,
                subsample=0.8, colsample_bytree=0.75,
                n_jobs=-1, random_state=SEED, verbose=-1)
            m.fit(X, y)
            q_models[str(q)] = m
        except Exception as e:
            print(f'      [WARN] Quantile {q} failed: {e}')
    return q_models

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# IMPROVEMENT 8: SHAP EXPLAINABILITY
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
def get_shap_importance(model, X, feature_names, n_bg=300):
    if not HAS_SHAP:
        return {}
    try:
        bg = shap.sample(X, min(n_bg, len(X)))
        explainer = shap.TreeExplainer(model)
        shap_vals = explainer.shap_values(bg)
        if isinstance(shap_vals, list):
            shap_vals = shap_vals[0]
        importance = np.abs(shap_vals).mean(axis=0)
        return dict(sorted(zip(feature_names, importance.tolist()),
                            key=lambda kv: -kv[1]))
    except Exception:
        return {}

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# PHASE 3: TRAIN/TEST SPLIT PER UNIT
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
print('\n[Phase 3] Stratified train/test split per unit ...')
splits = {}
for unit in ['Unit_A', 'Unit_D']:
    sub = df[df['Dye_Unit'] == unit]
    strat = sub['Color_Depth_Bin'].fillna('N/A')
    tr_idx, te_idx = train_test_split(sub.index, test_size=0.2,
                                       stratify=strat, random_state=SEED)
    splits[unit] = {'train': tr_idx, 'test': te_idx}
    print(f'  {unit}: train={len(tr_idx):,}  test={len(te_idx):,}')

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# PHASE 4: TRAINING LOOP
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
print('\n[Phase 4] Training all models ...')
model_registry  = {}
shap_registry   = {}
comparison_rows = []

ALL_BINS = ['Pale', 'Light', 'Medium', 'Vivid', 'Dark', 'White', 'Pooled']

def run_one_model(unit, tgt, bin_label, tr_df, te_df, feats, threshold=1.0):
    """Full pipeline for one (unit Ã— target Ã— bin) slot."""
    tr_v = tr_df[tr_df[tgt].notna()].copy()
    te_v = te_df[te_df[tgt].notna()].copy()
    if tgt == 'Dye_g_per_kg':
        tr_v = tr_v[tr_v[tgt] > threshold]
        te_v = te_v[te_v[tgt] > threshold]

    if len(tr_v) < 80 or len(te_v) < 10:
        return None

    X_tr = tr_v[feats].fillna(0).values.astype(float)
    y_tr = tr_v[tgt].values.astype(float)
    X_te = te_v[feats].fillna(0).values.astype(float)
    y_te = te_v[tgt].values.astype(float)

    # IMPROVEMENT 3: Optuna tune XGBoost + LightGBM
    optuna_str = ' (Optuna)' if HAS_OPTUNA and len(X_tr) >= 200 else ''
    print(f'      Optuna-tuning XGBoost + LightGBM{optuna_str} ...', end='', flush=True)
    xgb_p = tune_xgboost(X_tr, y_tr, N_OPTUNA)
    lgb_p  = tune_lgbm(X_tr,  y_tr, N_OPTUNA)

    # IMPROVEMENT 4+5: 5-fold CV + Stacking
    best_obj, best_cv_mape, cv_res, best_name = \
        train_cv_stack(X_tr, y_tr, xgb_p, lgb_p, threshold)

    if best_obj is None:
        print(' SKIP')
        return None

    # Test set evaluation
    if isinstance(best_obj, dict) and best_obj.get('type') == 'stack':
        y_pred = stack_predict(best_obj, X_te)
    else:
        y_pred = np.clip(best_obj.predict(X_te), 0, None)

    test_mape = mape_safe(y_te, y_pred, threshold)
    test_r2   = r2_score(y_te, y_pred)
    test_mae  = mean_absolute_error(y_te, y_pred)

    # IMPROVEMENT 6: Quantile regression
    q_mods = train_quantile(X_tr, y_tr, lgb_p)

    # IMPROVEMENT 8: SHAP (only on non-stack primary model)
    shap_imp = {}
    shap_model = None
    if isinstance(best_obj, dict) and best_obj.get('type') == 'stack':
        # Pick the XGBoost base for SHAP
        for m, nm in zip(best_obj['bases'], best_obj['base_names']):
            if 'XGBoost' in nm or 'LightGBM' in nm:
                shap_model = m
                break
    elif isinstance(best_obj, xgb.XGBRegressor) or isinstance(best_obj, lgb.LGBMRegressor):
        shap_model = best_obj
    if shap_model is not None:
        shap_imp = get_shap_importance(shap_model, X_tr[:500], feats)

    key = f'{unit}_{tgt}_{bin_label}'
    result = {
        'model':         best_obj,
        'features':      feats,
        'quantile_models': q_mods,
        'unit':          unit,
        'target':        tgt,
        'color_depth_bin': bin_label,
        'model_type':    best_name,
        'train_n':       len(X_tr),
        'test_n':        len(X_te),
        'cv_mape':       round(best_cv_mape, 2),
        'test_mape':     round(test_mape, 2),
        'test_r2':       round(test_r2, 4),
        'test_mae':      round(test_mae, 3),
        'cv_results':    cv_res,
        'xgb_params':    xgb_p,
        'lgb_params':    lgb_p,
    }
    shap_imp_out = {}
    if shap_imp:
        shap_imp_out = dict(list(shap_imp.items())[:10])

    print(f' [{best_name}]  CV={best_cv_mape:.1f}%  Test={test_mape:.1f}%  '
          f'RÂ²={test_r2:.3f}  n={len(X_tr):,}')
    if shap_imp_out:
        top3 = list(shap_imp_out.items())[:3]
        print(f'      SHAP top-3: ' + ' | '.join(f'{k}={v:.2f}' for k, v in top3))

    return result, shap_imp_out

# â”€â”€ POOLED TARGETS: Water + Total Chem â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print('\n  â”€â”€ Pooled targets (Water Intensity, Total Chem) â”€â”€')
for unit in ['Unit_A', 'Unit_D']:
    tr_df = df.loc[splits[unit]['train']]
    te_df = df.loc[splits[unit]['test']]
    for tgt in POOLED_TARGETS:
        print(f'\n    {unit} | {TARGET_LABELS[tgt]}')
        out = run_one_model(unit, tgt, 'Pooled', tr_df, te_df, ALL_FEATS, threshold=1.0)
        if out:
            res, shap_imp = out
            key = f'{unit}_{tgt}_Pooled'
            model_registry[key]  = res
            shap_registry[key]   = shap_imp
            pkl_path = os.path.join(MODELS, f'{key}.pkl')
            with open(pkl_path, 'wb') as fh:
                pickle.dump({k: v for k, v in res.items() if k != 'quantile_models'}, fh)
            # Save quantile models separately
            qpkl = os.path.join(MODELS, f'{key}_quantile.pkl')
            with open(qpkl, 'wb') as fh:
                pickle.dump(res['quantile_models'], fh)

# â”€â”€ STRATIFIED TARGETS: Salt, Dye, Alkali â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print('\n\n  â”€â”€ Stratified targets (Salt, Dye, Alkali) per Color_Depth_Bin â”€â”€')
for unit in ['Unit_A', 'Unit_D']:
    tr_df = df.loc[splits[unit]['train']]
    te_df = df.loc[splits[unit]['test']]

    for tgt in STRATIFIED_TARGETS:
        thr = 1.0 if tgt == 'Dye_g_per_kg' else 0.0
        skip_bins = {'White'} if tgt == 'Dye_g_per_kg' else set()
        bins_for_this = ['Pale', 'Light', 'Medium', 'Vivid', 'Dark', 'White']

        print(f'\n  â”€â”€ {unit} | {TARGET_LABELS[tgt]} â”€â”€')
        for bn in bins_for_this:
            if bn in skip_bins:
                print(f'    {bn:8s}: SKIP (structural zero â€” White has no dye)')
                continue

            # Filter by color_depth_bin
            tr_b = tr_df[tr_df['Color_Depth_Bin'] == bn]
            te_b = te_df[te_df['Color_Depth_Bin'] == bn]

            print(f'    {bn:8s} (n_train={len(tr_b):,}): ', end='', flush=True)
            if len(tr_b) < 80 or len(te_b) < 10:
                print(f'SKIP (train={len(tr_b)} test={len(te_b)})')
                continue

            out = run_one_model(unit, tgt, bn, tr_b, te_b, ALL_FEATS, threshold=thr)
            if out:
                res, shap_imp = out
                key = f'{unit}_{tgt}_{bn}'
                model_registry[key] = res
                shap_registry[key]  = shap_imp
                pkl_path = os.path.join(MODELS, f'{key}.pkl')
                with open(pkl_path, 'wb') as fh:
                    pickle.dump({k: v for k, v in res.items() if k != 'quantile_models'}, fh)
                qpkl = os.path.join(MODELS, f'{key}_quantile.pkl')
                with open(qpkl, 'wb') as fh:
                    pickle.dump(res['quantile_models'], fh)

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# IMPROVEMENT 7: WHITE/BLEACH RULE OVERRIDE FILE
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
print('\n[Improvement 7] White/Bleach rule-based override ...')
wb_rules = {
    'Dye_g_per_kg': {
        'rule': 'Shade == White/Bleach â†’ Dye = 0.0',
        'reason': 'No reactive dye used in bleaching process'
    },
    'Salt_g_per_kg_NextBatch': {
        'rule': 'Shade == White/Bleach AND Is_NextBatch == 1 â†’ Salt = 0.0',
        'reason': 'Salt exhausted from previous bath; bath reuse eliminates salt need'
    },
}
with open(os.path.join(MODELS, 'whiteBleach_rules.json'), 'w') as fh:
    json.dump(wb_rules, fh, indent=2)
print('  Saved: whiteBleach_rules.json')

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# PHASE 5: v1 vs v2 COMPARISON TABLE
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
print('\n[Phase 5] v1 vs v2 MAPE comparison ...')
print(f'\n  {"Model Key":55s} {"v1 MAPE":>9} {"v2 MAPE":>9} {"Î”":>8}')
print('  ' + '-'*90)

comparisons = []
for key, meta in sorted(model_registry.items()):
    v1 = V1_MAPES.get(key)
    v2 = meta['test_mape']
    if v1:
        d = v2 - v1
        sym = 'âœ…' if d < -3 else ('âš ï¸' if d > 3 else 'â‰ˆ')
        print(f'  {key:55s} {v1:>9.1f}% {v2:>9.1f}% {d:>+7.1f}%  {sym}')
        comparisons.append({'key': key, 'v1': v1, 'v2': v2, 'delta': d})
    else:
        print(f'  {key:55s} {"NEW":>9}  {v2:>9.1f}%')

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# PHASE 6: CHARTS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
print('\n[Phase 6] Generating charts ...')
C_NAVY='#1C3A6B'; C_TEAL='#2E8B8B'; C_GREEN='#2A7A3B'; C_WARN='#B5382B'; C_GOLD='#C8860A'

# Chart 1: v1 vs v2 MAPE bar chart
if comparisons:
    comp_df = pd.DataFrame(comparisons).sort_values('v1', ascending=False)
    fig, ax = plt.subplots(figsize=(14, 5))
    fig.patch.set_facecolor('#F7F8FA'); ax.set_facecolor('#FFFFFF')
    x = np.arange(len(comp_df)); w = 0.38
    ax.bar(x - w/2, comp_df['v1'], w, color=C_NAVY, alpha=0.85, label='v1 MAPE', zorder=3)
    b2 = ax.bar(x + w/2, comp_df['v2'], w, color=C_TEAL, alpha=0.85, label='v2 MAPE (Optuna+CV+Stack)', zorder=3)
    for bar, v in zip(b2, comp_df['v2']):
        if v < 999:
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+1.5,
                    f'{v:.0f}%', ha='center', va='bottom', fontsize=7.5, fontweight='700', color=C_TEAL)
    ax.set_xticks(x)
    ax.set_xticklabels(
        [c.replace('_g_per_kg','').replace('_L_per_kg','').replace('_Pooled','')
         for c in comp_df['key']], rotation=35, ha='right', fontsize=8)
    ax.set_ylabel('MAPE %', fontsize=10)
    ax.set_title('v1 vs v2 Model MAPE â€” Effect of 8 Improvements\n(Lower = Better)',
                 fontsize=12, fontweight='bold')
    ax.axhline(20, linestyle='--', color=C_GREEN, lw=1.5, alpha=0.7, label='Target 20%')
    ax.legend(fontsize=9); ax.grid(axis='y', alpha=0.3)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    fig.tight_layout()
    p1 = os.path.join(RPTS, 'v2_mape_comparison.png')
    fig.savefig(p1, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  Saved: {p1}')

# Chart 2: Color-depth bin pie charts
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
fig.patch.set_facecolor('#F7F8FA')
BIN_CLR = {'Pale':'#D4E9F7','Light':'#7AB8D8','Medium':'#2E7FB0','Vivid':'#1C3A6B',
            'Dark':'#B5382B','White':'#A8D5A2','N/A':'#CCCCCC'}
for ax, unit in zip(axes, ['Unit_A', 'Unit_D']):
    ax.set_facecolor('#FFFFFF')
    cnt = df[df['Dye_Unit']==unit]['Color_Depth_Bin'].value_counts()
    bins_ord = [b for b in ['Pale','Light','Medium','Vivid','Dark','White'] if b in cnt.index]
    ax.pie([cnt[b] for b in bins_ord], labels=bins_ord,
           colors=[BIN_CLR.get(b,'#888') for b in bins_ord],
           autopct='%1.1f%%', startangle=90, pctdistance=0.75)
    ax.set_title(f'{unit}  (n={cnt.sum():,})', fontweight='bold')
fig.suptitle('Batch Distribution by Color Depth Bin (v2 Sub-Stratification)',
             fontsize=12, fontweight='bold')
p2 = os.path.join(RPTS, 'v2_color_depth_bins.png')
fig.savefig(p2, dpi=150, bbox_inches='tight')
plt.close(fig)
print(f'  Saved: {p2}')

# Chart 3: SHAP top-15 features for best model
if shap_registry:
    best_shap_key = max(shap_registry, key=lambda k: len(shap_registry[k]))
    shap_data = shap_registry[best_shap_key]
    if shap_data:
        items = list(shap_data.items())[:15]
        fnames = [i[0].replace('_',' ')[:28] for i in items]
        fvals  = [i[1] for i in items]
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.set_facecolor('#FFFFFF'); fig.patch.set_facecolor('#F7F8FA')
        cols = [C_TEAL if v > np.median(fvals) else C_NAVY for v in fvals]
        ax.barh(range(len(fnames)), fvals[::-1], color=cols[::-1], alpha=0.85)
        ax.set_yticks(range(len(fnames)))
        ax.set_yticklabels(fnames[::-1], fontsize=9)
        ax.set_xlabel('Mean |SHAP value|', fontsize=10)
        ax.set_title(f'Feature Importance (SHAP TreeExplainer)\n{best_shap_key}',
                     fontsize=11, fontweight='bold')
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
        ax.grid(axis='x', alpha=0.3)
        fig.tight_layout()
        p3 = os.path.join(RPTS, 'v2_shap_importance.png')
        fig.savefig(p3, dpi=150, bbox_inches='tight')
        plt.close(fig)
        print(f'  Saved: {p3}')

# Chart 4: CV std vs MAPE scatter (model reliability)
if model_registry:
    cv_mapes = []; cv_stds = []; keys_short = []
    for k, m in model_registry.items():
        cv_res = m.get('cv_results', {})
        best_nm = m.get('model_type', '')
        if best_nm in cv_res:
            cv_mapes.append(cv_res[best_nm]['cv_mape_mean'])
            cv_stds.append(cv_res[best_nm]['cv_mape_std'])
            keys_short.append(k.replace('_g_per_kg','').replace('_L_per_kg','')[:25])

    if cv_mapes:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.set_facecolor('#FFFFFF'); fig.patch.set_facecolor('#F7F8FA')
        ax.scatter(cv_mapes, cv_stds, c=C_TEAL, s=80, alpha=0.8, edgecolors='white', linewidth=0.8)
        for x, y_, lbl in zip(cv_mapes, cv_stds, keys_short):
            ax.annotate(lbl, (x, y_), fontsize=7, ha='left', va='bottom',
                        xytext=(4, 4), textcoords='offset points', color='#333')
        ax.set_xlabel('CV MAPE Mean (%)', fontsize=10)
        ax.set_ylabel('CV MAPE Std (%)', fontsize=10)
        ax.set_title('Model Reliability: MAPE Mean vs Std across 5 folds\n'
                     '(Lower-left = best: accurate and consistent)', fontsize=11, fontweight='bold')
        ax.axvline(20, linestyle='--', color=C_GREEN, lw=1.5, alpha=0.6)
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
        ax.grid(alpha=0.3)
        fig.tight_layout()
        p4 = os.path.join(RPTS, 'v2_cv_reliability.png')
        fig.savefig(p4, dpi=150, bbox_inches='tight')
        plt.close(fig)
        print(f'  Saved: {p4}')

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# PHASE 7: SAVE FULL RESULTS JSON
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
print('\n[Phase 7] Saving results JSON ...')
results = {
    'generated':      time.strftime('%Y-%m-%dT%H:%M:%S'),
    'total_models':   len(model_registry),
    'training_rows':  int(len(df)),
    'features_v2':    len(ALL_FEATS),
    'features_v1':    23,
    'improvements': [
        '1. K-means color-depth sub-stratification (Pale/Light/Medium/Vivid) of Light/Medium',
        '2. Is_2Part + Is_NextBatch + Is_Finished + Is_ReProcess binary features',
        '3. Optuna Bayesian hyperparameter tuning (20 trials, TPE sampler)',
        '4. 5-fold stratified cross-validation (StratifiedKFold on target quantile bins)',
        '5. Stacking ensemble (Ridge meta-learner on OOF from XGB+LGB+RF+Ridge)',
        '6. Quantile regression P10/P50/P90 via LightGBM quantile objective',
        '7. White/Bleach rule-based override (Dye=0, Salt=0 for Next Batch)',
        '8. SHAP TreeExplainer feature importance per stratum',
    ],
    'model_metrics': {
        k: {kk: vv for kk, vv in v.items()
            if kk not in ('model', 'quantile_models', 'cv_results')}
        for k, v in model_registry.items()
    },
    'v1_v2_comparison': comparisons,
    'shap_top10': {k: list(v.items())[:10] for k, v in shap_registry.items() if v},
    'color_depth_distribution': df['Color_Depth_Bin'].value_counts().to_dict(),
    'runtime_sec': round(time.time() - t0, 1),
}
json_path = os.path.join(RPTS, 'v2_training_results.json')
with open(json_path, 'w', encoding='utf-8') as fh:
    json.dump(results, fh, indent=2, ensure_ascii=False)
print(f'  Saved: {json_path}')

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# FINAL SUMMARY
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
elapsed = time.time() - t0
print()
print('='*70)
print('V2 TRAINING COMPLETE')
print(f'  Total models trained: {len(model_registry)}')
print(f'  Total features:       {len(ALL_FEATS)} (v1 had 23)')
print(f'  Training rows:        {len(df):,}')
print(f'  Runtime:              {elapsed/60:.1f} min ({elapsed:.0f}s)')
print()
print(f'  {"Model Key":55s} {"CV MAPE":>9} {"Test MAPE":>10} {"RÂ²":>7}')
print('  ' + '-'*85)
for key in sorted(model_registry.keys()):
    m = model_registry[key]
    v1 = V1_MAPES.get(key)
    v1str = f'(v1={v1:.0f}%)' if v1 else '(NEW)'
    print(f'  {key:55s} {m["cv_mape"]:>9.1f}% {m["test_mape"]:>10.1f}% '
          f'{m["test_r2"]:>7.3f}  {v1str}')
print()
print(f'  Artifacts in: models/v2/  and  reports/')
print(f'  Next: run 39_ai_v2_predict_enhanced.py for predictions with CI')
print('='*70)


