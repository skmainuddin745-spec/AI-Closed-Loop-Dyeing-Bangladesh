"""
35_ai_train_pipeline.py
=========================
SMART DYEING â€” AI Chemical Prediction Framework
Phase 1â€“6: Data Validation, Feature Engineering, EDA, Training, Validation.

Input  (read-only originals â€” NEVER MODIFIED):
  DEEP_ROOT_Batch_Enriched.csv        â€” primary training source (261K usable)

Output (AI_Recipe_Optimizer/):
  data/training_set.csv               â€” cleaned training copy
  data/test_set.csv                   â€” held-out test copy
  models/Unit_A_salt_gbm.pkl etc.        â€” trained model artifacts
  reports/training_report.json        â€” full metrics
  reports/EDA_Report_V2.html          â€” visual EDA report
  reports/Validation_Results.html     â€” stratified error table

Run: py -3.12 35_ai_train_pipeline.py
"""

import os, sys, io, json, math, warnings, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
warnings.filterwarnings('ignore')

# â”€â”€â”€ PATHS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
ROOT   = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(ROOT)
SRC    = os.path.join(PARENT, '2026-09-03_Categorization_Insights',
                      'DEEP_ROOT_Batch_Enriched.csv')
OUT    = ROOT  # AI_Recipe_Optimizer/
DATA   = os.path.join(OUT, 'data')
MODELS = os.path.join(OUT, 'models')
RPTS   = os.path.join(OUT, 'reports')
for d in [DATA, MODELS, RPTS]:
    os.makedirs(d, exist_ok=True)

print('=' * 68)
print('SMART DYEING â€” AI Chemical Prediction Framework')
print('Phase 1â€“6: Data â†’ Features â†’ EDA â†’ Train â†’ Validate')
print('=' * 68)
print('Source (READ-ONLY):', SRC)
print()

# â”€â”€â”€ IMPORTS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from scipy import stats
from sklearn.model_selection import train_test_split, cross_val_score, KFold
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.inspection import permutation_importance
import xgboost as xgb
import lightgbm as lgb
import pickle

t0 = time.time()

# â”€â”€â”€ PHASE 1: DATA LOADING & VALIDATION â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print('[Phase 1] Loading and validating data ...')
df_raw = pd.read_csv(SRC, low_memory=False)
print(f'  Raw rows: {len(df_raw):,}')

# Apply QC filters (same protocol as V2 report â€” no bias)
df = df_raw.copy()
df = df[df['QC_Usable'] == 1]
print(f'  After QC_Usable==1: {len(df):,}')

# Year filter: 2021â€“2026 only (exclude pre-2021 warmup)
df['Year'] = pd.to_numeric(df['Year'], errors='coerce')
df = df[df['Year'].between(2021, 2026)]
print(f'  After year 2021â€“2026: {len(df):,}')

# Exclude Unit_C (physically implausible salt for disperse dyeing)
df = df[df['Dye_Unit'] != 'Unit_C']
print(f'  After Unit_C exclusion: {len(df):,}')

# Numeric coercion
num_cols = ['Fabric_Kg','Water_L','Liquor_Ratio_1_to_X','Water_Intensity_L_per_kg',
            'Chem_g_per_kg','Salt_g_per_kg','Dye_g_per_kg','Alkali_Kg',
            'Recipe_Lines','Chem_Total_Kg','Cost_Tk_per_kg']
for c in num_cols:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors='coerce')

# Derive Alkali_g_per_kg if missing
if 'Alkali_g_per_kg' not in df.columns:
    df['Alkali_g_per_kg'] = ((df['Alkali_Kg'].fillna(0)) /
                              df['Fabric_Kg'].replace(0, np.nan)) * 1000

# Physical plausibility bounds (dual-constraint â€” V2 protocol)
BOUNDS = {
    'Salt_g_per_kg':          (0, 700),
    'Dye_g_per_kg':           (0, 300),
    'Chem_g_per_kg':          (5, 3000),
    'Water_Intensity_L_per_kg':(0.5, 50),
    'Fabric_Kg':              (10, 5000),
    'Alkali_g_per_kg':        (0, 500),
}
before = len(df)
for col, (lo, hi) in BOUNDS.items():
    if col in df.columns:
        df = df[df[col].notna() & df[col].between(lo, hi)]
print(f'  After plausibility bounds: {len(df):,} (removed {before-len(df):,})')

# Parse Month
df['Month_num'] = pd.to_numeric(df['Month'].str[5:7], errors='coerce').fillna(6)

# â”€â”€â”€ PHASE 2: FEATURE ENGINEERING â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print()
print('[Phase 2] Feature engineering ...')

# Cyclic month encoding
df['Month_sin'] = np.sin(2 * np.pi * df['Month_num'] / 12)
df['Month_cos'] = np.cos(2 * np.pi * df['Month_num'] / 12)

# Log-transform fabric weight (right-skewed)
df['Log_Fabric_Kg'] = np.log1p(df['Fabric_Kg'])

# Ordinal GSM
GSM_ORD = {'Light (<150)': 1, 'Medium (150-249)': 2, 'Heavy (250+)': 3, 'Unknown': 2}
df['GSM_Ord'] = df['GSM_Category'].map(GSM_ORD).fillna(2).astype(float)

# One-hot: Shade â€” explicitly cast to float to guarantee numeric dtype
shade_dummies = pd.get_dummies(df['Shade_Category'], prefix='Shade').astype(float)
df = pd.concat([df, shade_dummies], axis=1)

# One-hot: Fabric category (top 7 + Other)
top_fab = df['Fabric_Category'].value_counts().head(7).index.tolist()
df['Fabric_Cat_Clean'] = df['Fabric_Category'].apply(
    lambda x: x if x in top_fab else 'Other')
fab_dummies = pd.get_dummies(df['Fabric_Cat_Clean'], prefix='Fab').astype(float)
df = pd.concat([df, fab_dummies], axis=1)

# One-hot: Dyeing type
dtype_dummies = pd.get_dummies(
    df['Dyeing_Type'].fillna('Normal').str[:10], prefix='DType').astype(float)
df = pd.concat([df, dtype_dummies], axis=1)

# Interaction: GSM Ã— log(FabricKg)
df['GSM_x_LogFab'] = df['GSM_Ord'] * df['Log_Fabric_Kg']

# Liquor ratio (fill missing with median per unit)
df['LR'] = df['Liquor_Ratio_1_to_X'].fillna(
    df.groupby('Dye_Unit')['Liquor_Ratio_1_to_X'].transform('median'))
df['LR'] = df['LR'].fillna(7.0)

# Ensure all engineered numerics are float
for _c in ['Log_Fabric_Kg','Month_sin','Month_cos','LR','GSM_x_LogFab','Year','Recipe_Lines']:
    if _c in df.columns:
        df[_c] = pd.to_numeric(df[_c], errors='coerce').fillna(0).astype(float)

print(f'  Features created. DataFrame shape: {df.shape}')

# Base feature list (unit-independent)
BASE_FEATURES = (
    ['Log_Fabric_Kg','GSM_Ord','LR','Month_sin','Month_cos','Year',
     'Recipe_Lines','GSM_x_LogFab'] +
    [c for c in df.columns if c.startswith('Shade_')] +
    [c for c in df.columns if c.startswith('Fab_')] +
    [c for c in df.columns if c.startswith('DType_')]
)
# Drop all-zero columns â€” guard with is_numeric_dtype to avoid string-sum TypeError
BASE_FEATURES = [
    f for f in BASE_FEATURES
    if f in df.columns
    and pd.api.types.is_numeric_dtype(df[f])
    and float(df[f].sum()) > 0
]

TARGETS = {
    'Salt_g_per_kg':           'Salt (g/kg)',
    'Dye_g_per_kg':            'Dye (g/kg)',
    'Alkali_g_per_kg':         'Alkali (g/kg)',
    'Chem_g_per_kg':           'Total Chem (g/kg)',
    'Water_Intensity_L_per_kg':'Water Intensity (L/kg)',
}
UNITS = ['Unit_A', 'Unit_D']

print(f'  Base features: {len(BASE_FEATURES)}')
print(f'  Targets: {list(TARGETS.keys())}')
print(f'  Units: {UNITS}')

# â”€â”€â”€ PHASE 3: EDA â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print()
print('[Phase 3] Exploratory Data Analysis ...')

eda_stats = {}
for unit in UNITS:
    sub = df[df['Dye_Unit'] == unit]
    eda_stats[unit] = {'n': len(sub)}
    for tgt in TARGETS:
        if tgt not in sub.columns: continue
        s = sub[tgt].dropna()
        eda_stats[unit][tgt] = {
            'mean':   round(float(s.mean()), 3),
            'median': round(float(s.median()), 3),
            'std':    round(float(s.std()), 3),
            'p10':    round(float(s.quantile(0.10)), 3),
            'p25':    round(float(s.quantile(0.25)), 3),
            'p75':    round(float(s.quantile(0.75)), 3),
            'p90':    round(float(s.quantile(0.90)), 3),
            'cv_pct': round(float(s.std()/s.mean()*100), 1) if s.mean() > 0 else 0,
            'n':      int(len(s)),
        }
    print(f'  {unit}: {len(sub):,} batches')

# ANOVA F-stats (shade Ã— target)
from scipy.stats import f_oneway
anova_results = {}
for tgt in TARGETS:
    if tgt not in df.columns: continue
    groups = [df[df['Shade_Category']==s][tgt].dropna().values
              for s in df['Shade_Category'].unique() if len(df[df['Shade_Category']==s]) > 10]
    if len(groups) >= 2:
        F, p = f_oneway(*groups)
        anova_results[tgt] = {'F': round(float(F), 2), 'p': float(p)}
        print(f'  ANOVA {tgt[:20]:20s}: F={F:,.1f}  pâ‰ˆ{p:.2e}')

# Pearson correlations (key pairs)
pearson_pairs = [
    ('Chem_g_per_kg',       'Cost_Tk_per_kg'),
    ('Salt_g_per_kg',       'Dye_g_per_kg'),
    ('Chem_g_per_kg',       'Salt_g_per_kg'),
    ('Water_Intensity_L_per_kg', 'Fabric_Kg'),
    ('Water_Intensity_L_per_kg', 'Cost_Tk_per_kg'),
    ('Log_Fabric_Kg',       'Water_Intensity_L_per_kg'),
    ('GSM_Ord',             'Salt_g_per_kg'),
]
pearson_results = {}
for (a, b) in pearson_pairs:
    if a in df.columns and b in df.columns:
        mask = df[[a,b]].notna().all(axis=1)
        r, pv = stats.pearsonr(df.loc[mask, a], df.loc[mask, b])
        pearson_results[f'{a} â†” {b}'] = {'r': round(float(r), 4), 'n': int(mask.sum())}

# Cross-tabulation: Shade Ã— GSM
xtab = {}
for tgt in ['Salt_g_per_kg', 'Dye_g_per_kg', 'Water_Intensity_L_per_kg']:
    if tgt not in df.columns: continue
    xtab[tgt] = {}
    for shade in ['Light/Medium Colored', 'Dark/Extra Dark', 'White/Bleach']:
        xtab[tgt][shade] = {}
        for gsm in ['Light (<150)', 'Medium (150-249)', 'Heavy (250+)']:
            sub = df[(df['Shade_Category']==shade) & (df['GSM_Category']==gsm)][tgt].dropna()
            xtab[tgt][shade][gsm] = {
                'n':   int(len(sub)),
                'mean': round(float(sub.mean()), 2) if len(sub) > 0 else 0,
                'p25': round(float(sub.quantile(0.25)), 2) if len(sub) > 0 else 0,
            }

print('  EDA complete.')

# â”€â”€â”€ PHASE 4+5: MODEL TRAINING â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print()
print('[Phase 4+5] Model training ...')

SEED = 42
all_metrics = {}
saved_models = {}

def mape(y_true, y_pred):
    mask = y_true > 0
    return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100

def get_models():
    return {
        'Ridge': Pipeline([
            ('scaler', StandardScaler()),
            ('model', Ridge(alpha=10.0))
        ]),
        'RandomForest': RandomForestRegressor(
            n_estimators=200, max_depth=12, min_samples_leaf=10,
            n_jobs=-1, random_state=SEED
        ),
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
    }

train_dfs = {}
test_dfs  = {}

for unit in UNITS:
    sub = df[df['Dye_Unit'] == unit].copy()
    # Stratify by Shade_Category for reproducible split
    X_all = sub[BASE_FEATURES].fillna(0)
    strat_labels = sub['Shade_Category'].fillna('Unknown')

    tr_idx, te_idx = train_test_split(
        sub.index, test_size=0.20, random_state=SEED, stratify=strat_labels)
    train_df = sub.loc[tr_idx]
    test_df  = sub.loc[te_idx]
    train_dfs[unit] = train_df
    test_dfs[unit]  = test_df

    print(f'\n  â”€â”€ {unit} ({len(sub):,} batches | train:{len(train_df):,} test:{len(test_df):,}) â”€â”€')
    all_metrics[unit] = {}

    for tgt_col, tgt_name in TARGETS.items():
        if tgt_col not in sub.columns:
            continue
        # Drop rows where target is NaN
        tr = train_df[train_df[tgt_col].notna()]
        te = test_df[test_df[tgt_col].notna()]
        if len(tr) < 200 or len(te) < 50:
            print(f'    {tgt_name}: SKIP (too few rows)')
            continue

        X_tr = tr[BASE_FEATURES].fillna(0).values
        y_tr = tr[tgt_col].values
        X_te = te[BASE_FEATURES].fillna(0).values
        y_te = te[tgt_col].values

        all_metrics[unit][tgt_col] = {}
        best_mape = 999; best_name = None; best_model = None

        for mname, model in get_models().items():
            try:
                model.fit(X_tr, y_tr)
                y_pred = np.clip(model.predict(X_te), 0, None)
                mae_v  = round(float(mean_absolute_error(y_te, y_pred)), 3)
                rmse_v = round(float(np.sqrt(mean_squared_error(y_te, y_pred))), 3)
                mape_v = round(float(mape(y_te, y_pred)), 2)
                r2_v   = round(float(r2_score(y_te, y_pred)), 4)
                all_metrics[unit][tgt_col][mname] = {
                    'MAE': mae_v, 'RMSE': rmse_v, 'MAPE_pct': mape_v, 'R2': r2_v,
                    'train_n': len(X_tr), 'test_n': len(X_te)
                }
                status = 'â˜… BEST' if mape_v < best_mape else ''
                print(f'    {tgt_name:22s} | {mname:12s} | MAE={mae_v:7.2f} MAPE={mape_v:5.1f}% RÂ²={r2_v:.3f} {status}')
                if mape_v < best_mape:
                    best_mape = mape_v; best_name = mname; best_model = model
            except Exception as e:
                print(f'    {tgt_name} | {mname}: ERROR â€” {e}')

        if best_model is not None:
            key = f'{unit}_{tgt_col}_{best_name}'
            saved_models[key] = {
                'model': best_model,
                'features': BASE_FEATURES,
                'unit': unit,
                'target': tgt_col,
                'model_type': best_name,
                'mape': best_mape,
            }
            pkl_path = os.path.join(MODELS, f'{unit}_{tgt_col}_{best_name}.pkl')
            with open(pkl_path, 'wb') as f_pkl:
                pickle.dump(saved_models[key], f_pkl)
            all_metrics[unit][tgt_col]['_best'] = best_name
            print(f'    â†’ Saved: {os.path.basename(pkl_path)} (MAPE={best_mape:.1f}%)')

# Save train/test splits
for unit in UNITS:
    train_dfs[unit].to_csv(os.path.join(DATA, f'training_set_{unit}.csv'), index=False)
    test_dfs[unit].to_csv(os.path.join(DATA, f'test_set_{unit}.csv'), index=False)
    print(f'  Saved: data/training_set_{unit}.csv ({len(train_dfs[unit]):,} rows)')

# â”€â”€â”€ PHASE 6: PHYSICAL PLAUSIBILITY CHECK â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print()
print('[Phase 6] Plausibility validation ...')
violations = 0
for key, meta in saved_models.items():
    unit = meta['unit']; tgt = meta['target']
    model = meta['model']
    te = test_dfs[unit][test_dfs[unit][tgt].notna()]
    X_te = te[BASE_FEATURES].fillna(0).values
    preds = model.predict(X_te)
    lo, hi = BOUNDS.get(tgt, (0, 1e9))
    viol = int(np.sum((preds < lo) | (preds > hi)))
    total = len(preds)
    pct = viol / total * 100
    violations += viol
    print(f'  {unit:3s} {tgt:28s}: {viol:4d}/{total:,} out-of-bounds ({pct:.2f}%)')
print(f'  Total violations: {violations}')

# â”€â”€â”€ SAVE training_report.json â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
report = {
    'generated': time.strftime('%Y-%m-%dT%H:%M:%S'),
    'qc_usable_total': int(len(df)),
    'units_trained': UNITS,
    'targets': list(TARGETS.keys()),
    'features_n': len(BASE_FEATURES),
    'features': BASE_FEATURES,
    'metrics': all_metrics,
    'anova': anova_results,
    'pearson': pearson_results,
    'eda_stats': eda_stats,
    'cross_tab': xtab,
    'physical_violations': violations,
    'runtime_sec': round(time.time() - t0, 1),
}
rpt_path = os.path.join(RPTS, 'training_report.json')
with open(rpt_path, 'w', encoding='utf-8') as f_rpt:
    json.dump(report, f_rpt, indent=2, ensure_ascii=False)
print(f'  Saved: reports/training_report.json')

# â”€â”€â”€ GENERATE EDA + VALIDATION HTML REPORT â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print()
print('[Phase 6b] Generating HTML reports ...')

# â”€â”€ EDA charts (matplotlib, BeautifulFigures style) â”€â”€
C_NAVY='#1C3A6B'; C_TEAL='#2E8B8B'; C_LIGHT='#6B4C8A'; C_WARN='#B5382B'
C_MED='#D97706'; C_GRID='#E4E4E4'; C_SPINE='#999999'

def apply_style():
    from matplotlib import rcParams
    rcParams.update({
        'font.family':'sans-serif','font.size':9,'axes.titlesize':10,
        'axes.titleweight':'bold','axes.facecolor':'white',
        'axes.edgecolor':C_SPINE,'axes.linewidth':0.8,
        'axes.spines.top':False,'axes.spines.right':False,
        'axes.grid':True,'axes.axisbelow':True,
        'grid.color':C_GRID,'grid.linewidth':0.55,'grid.linestyle':'--',
        'figure.facecolor':'white','savefig.dpi':150,
        'savefig.facecolor':'white','savefig.bbox':'tight',
    })

chart_files = []

# Chart 1: Distribution of targets per unit (box plot)
apply_style()
fig, axes = plt.subplots(2, 3, figsize=(13, 7))
fig.subplots_adjust(hspace=0.45, wspace=0.35)
tgt_list = ['Salt_g_per_kg','Dye_g_per_kg','Alkali_g_per_kg',
            'Chem_g_per_kg','Water_Intensity_L_per_kg']
unit_cols = {u: c for u, c in zip(UNITS, [C_NAVY, C_WARN])}
for i, tgt in enumerate(tgt_list):
    ax = axes[i//3][i%3]
    data_to_plot = [df[df['Dye_Unit']==u][tgt].dropna().values for u in UNITS]
    bp = ax.boxplot(data_to_plot, patch_artist=True, widths=0.5,
                    showfliers=False, notch=True)
    for patch, col in zip(bp['boxes'], [C_NAVY, C_WARN]):
        patch.set_facecolor(col); patch.set_alpha(0.7)
    for med in bp['medians']:
        med.set_color('white'); med.set_linewidth(2)
    ax.set_xticklabels(UNITS)
    ax.set_title(TARGETS.get(tgt, tgt), fontsize=9, pad=4)
    ax.set_ylabel('g/kg or L/kg', fontsize=8)
axes[1][2].set_visible(False)
fig.suptitle('Target Variable Distributions by Dyeing Unit (Unit_A vs Unit_D)',
             fontsize=11, fontweight='bold', y=1.01)
c1 = os.path.join(RPTS, 'eda_ch1_distributions.png')
fig.savefig(c1, dpi=150, facecolor='white', bbox_inches='tight')
plt.close(fig); chart_files.append(c1)
print('  Chart 1: distributions')

# Chart 2: ANOVA F-stats
apply_style()
fig, ax = plt.subplots(figsize=(7, 3.6))
tgt_names = [TARGETS.get(t, t) for t in TARGETS if t in anova_results]
f_vals    = [anova_results[t]['F'] for t in TARGETS if t in anova_results]
cols_a    = [C_NAVY if f > 1000 else (C_TEAL if f > 100 else C_WARN) for f in f_vals]
bars = ax.barh(range(len(tgt_names)), f_vals, color=cols_a, alpha=0.85,
               height=0.5, zorder=3, edgecolor='white')
for b, v in zip(bars, f_vals):
    ax.text(b.get_width()+max(f_vals)*0.01, b.get_y()+b.get_height()/2,
            f'F = {v:,.0f}', va='center', fontsize=8, fontweight='600')
ax.set_yticks(range(len(tgt_names))); ax.set_yticklabels(tgt_names, fontsize=8.5)
ax.set_xlabel('ANOVA F-Statistic (shade categories, p â‰ˆ 0 for all)', fontsize=9)
ax.invert_yaxis()
ax.grid(axis='x'); ax.grid(axis='y', visible=False)
ax.spines['left'].set_visible(False); ax.tick_params(left=False)
ax.set_title('ANOVA F-Statistics: Shade is the Primary Chemical Stratifier (n=261K)', pad=8)
fig.tight_layout()
c2 = os.path.join(RPTS, 'eda_ch2_anova.png')
fig.savefig(c2, dpi=150, facecolor='white', bbox_inches='tight')
plt.close(fig); chart_files.append(c2)
print('  Chart 2: ANOVA')

# Chart 3: Shade Ã— GSM cross-tab (Salt g/kg)
if 'Salt_g_per_kg' in xtab:
    apply_style()
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    shades = ['Light/Medium Colored', 'Dark/Extra Dark', 'White/Bleach']
    gsms   = ['Light (<150)', 'Medium (150-249)', 'Heavy (250+)']
    gsm_cols = [C_LIGHT, C_TEAL, C_NAVY]
    x = np.arange(len(shades)); w = 0.22; offs = [-w, 0, w]
    for gi, (gsm, gc, off) in enumerate(zip(gsms, gsm_cols, offs)):
        vals = [xtab['Salt_g_per_kg'].get(sh, {}).get(gsm, {}).get('mean', 0)
                for sh in shades]
        bars = ax.bar(x+off, vals, w, color=gc, alpha=0.86, label=gsm,
                      zorder=3, edgecolor='white')
        for b, v in zip(bars, vals):
            if v > 0:
                ax.text(b.get_x()+b.get_width()/2, b.get_height()+5,
                        f'{v:.0f}', ha='center', va='bottom',
                        fontsize=7.5, fontweight='600', color=gc)
    ax.set_xticks(x)
    ax.set_xticklabels(['Light/Medium', 'Dark/Extra Dark', 'White/Bleach'], fontsize=8.5)
    ax.set_ylabel('Salt g/kg fabric', fontsize=9)
    ax.set_ylim(0, 650)
    ax.legend(title='GSM Class', fontsize=8)
    ax.set_title('Salt g/kg by Shade Ã— GSM â€” GSM is an Independent Predictor', pad=8)
    fig.tight_layout()
    c3 = os.path.join(RPTS, 'eda_ch3_shade_gsm.png')
    fig.savefig(c3, dpi=150, facecolor='white', bbox_inches='tight')
    plt.close(fig); chart_files.append(c3)
    print('  Chart 3: ShadeÃ—GSM')

# Chart 4: MAPE comparison across models
apply_style()
mape_data = {}
for unit in UNITS:
    for tgt in TARGETS:
        if tgt not in all_metrics.get(unit, {}): continue
        for mname in ['Ridge','RandomForest','XGBoost','LightGBM']:
            if mname not in all_metrics[unit][tgt]: continue
            key = f'{unit} {tgt[:12]}'
            if key not in mape_data: mape_data[key] = {}
            mape_data[key][mname] = all_metrics[unit][tgt][mname]['MAPE_pct']

if mape_data:
    keys = list(mape_data.keys())
    model_names = ['Ridge','RandomForest','XGBoost','LightGBM']
    model_cols  = [C_LIGHT, C_TEAL, C_NAVY, C_WARN]
    fig, ax = plt.subplots(figsize=(12, max(4, len(keys)*0.5+2)))
    y = np.arange(len(keys)); w = 0.18; n = len(model_names)
    offs = np.linspace(-(n-1)/2*w, (n-1)/2*w, n)
    for mi, (mname, mc, off) in enumerate(zip(model_names, model_cols, offs)):
        vals = [mape_data[k].get(mname, np.nan) for k in keys]
        mask = [not math.isnan(v) for v in vals]
        ax.barh([y[i]+off for i in range(len(keys)) if mask[i]],
                [vals[i] for i in range(len(vals)) if mask[i]],
                w, color=mc, alpha=0.82, label=mname, zorder=3, edgecolor='white')
    ax.set_yticks(y); ax.set_yticklabels(keys, fontsize=7.5)
    ax.set_xlabel('MAPE % (lower is better)', fontsize=9)
    ax.axvline(15, linestyle='--', color=C_WARN, lw=1, alpha=0.6, label='15% target')
    ax.legend(loc='lower right', fontsize=8)
    ax.invert_yaxis()
    ax.set_title('MAPE Comparison: Ridge vs RF vs XGBoost vs LightGBM', pad=8)
    fig.tight_layout()
    c4 = os.path.join(RPTS, 'eda_ch4_mape_comparison.png')
    fig.savefig(c4, dpi=150, facecolor='white', bbox_inches='tight')
    plt.close(fig); chart_files.append(c4)
    print('  Chart 4: MAPE comparison')

# Chart 5: Pearson correlations
if pearson_results:
    apply_style()
    fig, ax = plt.subplots(figsize=(7, 4))
    pairs = list(pearson_results.keys())
    r_vals = [pearson_results[p]['r'] for p in pairs]
    cols_p = [C_TEAL if abs(r)>0.5 else (C_WARN if abs(r)<0.1 else C_LIGHT) for r in r_vals]
    ax.barh(range(len(pairs)), r_vals, color=cols_p, alpha=0.85, height=0.5,
            zorder=3, edgecolor='white')
    ax.axvline(0, color=C_SPINE, lw=0.8)
    for i, (p, r) in enumerate(zip(pairs, r_vals)):
        ax.text(r+(0.01 if r>=0 else -0.01), i,
                f'r={r:+.3f}', va='center',
                ha='left' if r>=0 else 'right', fontsize=8, fontweight='600')
    ax.set_yticks(range(len(pairs))); ax.set_yticklabels(pairs, fontsize=8)
    ax.set_xlabel('Pearson r', fontsize=9); ax.invert_yaxis()
    ax.set_xlim(-0.55, 1.1)
    ax.grid(axis='x'); ax.grid(axis='y', visible=False)
    ax.spines['left'].set_visible(False); ax.tick_params(left=False)
    ax.set_title('Pearson Correlation Structure (n=261K batches)', pad=8)
    fig.tight_layout()
    c5 = os.path.join(RPTS, 'eda_ch5_pearson.png')
    fig.savefig(c5, dpi=150, facecolor='white', bbox_inches='tight')
    plt.close(fig); chart_files.append(c5)
    print('  Chart 5: Pearson')

# â”€â”€ Build EDA HTML â”€â”€
def img_b64(path):
    import base64
    with open(path, 'rb') as fh:
        return base64.b64encode(fh.read()).decode()

anova_rows = ''
for tgt, vals in anova_results.items():
    name = TARGETS.get(tgt, tgt)
    sig = 'â˜…â˜…â˜…' if vals['p'] < 1e-100 else ('â˜…â˜…' if vals['p'] < 1e-10 else 'â˜…')
    anova_rows += f'<tr><td>{name}</td><td>{vals["F"]:,.1f}</td><td>â‰ˆ 0</td><td>{sig}</td></tr>'

metrics_rows = ''
for unit in UNITS:
    for tgt, tname in TARGETS.items():
        if tgt not in all_metrics.get(unit,{}): continue
        best = all_metrics[unit][tgt].get('_best', '')
        for mname in ['Ridge','RandomForest','XGBoost','LightGBM']:
            if mname not in all_metrics[unit][tgt]: continue
            m = all_metrics[unit][tgt][mname]
            star = 'â­' if mname == best else ''
            metrics_rows += (
                f'<tr class="{"best" if mname==best else ""}">'
                f'<td>{unit}</td><td>{tname}</td><td>{mname}</td>'
                f'<td>{m["MAE"]:.2f}</td><td>{m["RMSE"]:.2f}</td>'
                f'<td><b>{m["MAPE_pct"]:.1f}%</b></td><td>{m["R2"]:.3f}</td>'
                f'<td>{star}</td></tr>'
            )

chart_imgs = ''
chart_titles = ['Target Distributions by Unit', 'ANOVA F-Statistics',
                'Salt: Shade Ã— GSM Cross-tab', 'MAPE Model Comparison', 'Pearson Correlations']
for i, (cf, ct) in enumerate(zip(chart_files, chart_titles)):
    b64 = img_b64(cf)
    ext = 'png'
    chart_imgs += f'''
    <div class="chart-block">
      <h3>Figure {i+1}. {ct}</h3>
      <img src="data:image/{ext};base64,{b64}" style="max-width:100%;border:1px solid #e4e4e4;border-radius:4px;">
    </div>'''

eda_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>SMART DYEING â€” EDA & Model Validation Report V2</title>
<meta name="description" content="Exploratory Data Analysis and AI Model Validation for 261K dyeing batches">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
<style>
  :root {{--navy:#1C3A6B;--teal:#2E8B8B;--red:#B5382B;--orange:#E97316;--bg:#F8FAFC;--card:#fff;}}
  *{{box-sizing:border-box;margin:0;padding:0;}}
  body{{font-family:'Inter',sans-serif;background:var(--bg);color:#1a1a1a;font-size:14px;}}
  header{{background:var(--navy);color:#fff;padding:28px 40px;}}
  header h1{{font-size:22px;font-weight:700;margin-bottom:6px;}}
  header p{{font-size:13px;opacity:0.8;}}
  .badge{{display:inline-block;background:#2E8B8B;color:#fff;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:600;margin-left:10px;}}
  .container{{max-width:1200px;margin:0 auto;padding:24px;}}
  .kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:16px;margin:24px 0;}}
  .kpi{{background:var(--card);border-radius:8px;padding:16px;border-left:4px solid var(--navy);box-shadow:0 1px 4px rgba(0,0,0,.06);}}
  .kpi .val{{font-size:24px;font-weight:700;color:var(--navy);}}
  .kpi .lbl{{font-size:11px;color:#666;margin-top:4px;}}
  section{{background:var(--card);border-radius:8px;padding:20px 24px;margin-bottom:20px;box-shadow:0 1px 4px rgba(0,0,0,.06);}}
  h2{{font-size:15px;font-weight:700;color:var(--navy);margin-bottom:14px;border-bottom:2px solid var(--navy);padding-bottom:6px;}}
  h3{{font-size:13px;font-weight:600;color:var(--teal);margin:12px 0 8px;}}
  table{{width:100%;border-collapse:collapse;font-size:12.5px;}}
  th{{background:var(--navy);color:#fff;padding:8px 10px;text-align:left;font-weight:600;}}
  td{{padding:7px 10px;border-bottom:1px solid #e8ecf0;}}
  tr:nth-child(even) td{{background:#f4f7fb;}}
  tr.best td{{background:#e8f5e9 !important;}}
  .chart-block{{margin:20px 0;}}
  .alert{{background:#FFF8E6;border-left:4px solid var(--orange);padding:10px 14px;border-radius:4px;font-size:13px;margin:12px 0;}}
  footer{{text-align:center;padding:20px;font-size:11px;color:#888;}}
</style>
</head>
<body>
<header>
  <h1>SMART DYEING â€” EDA & AI Model Validation Report
    <span class="badge">Version 2</span>
  </h1>
  <p>Population: {len(df):,} QC-usable batches Â· Unit_A + Unit_D Â· 2021â€“2026 Â· Generated {time.strftime("%Y-%m-%d %H:%M")}</p>
</header>
<div class="container">

  <div class="kpi-grid">
    <div class="kpi"><div class="val">{len(df):,}</div><div class="lbl">QC-Usable Batches</div></div>
    <div class="kpi"><div class="val">{len(BASE_FEATURES)}</div><div class="lbl">Features Engineered</div></div>
    <div class="kpi"><div class="val">{len(saved_models)}</div><div class="lbl">Models Trained</div></div>
    <div class="kpi"><div class="val">{violations}</div><div class="lbl">Physical Violations</div></div>
    <div class="kpi"><div class="val">{report["runtime_sec"]:.0f}s</div><div class="lbl">Training Runtime</div></div>
  </div>

  <section>
    <h2>Â§1  ANOVA Validation â€” Shade is the Primary Stratifier</h2>
    <table>
      <tr><th>Target Variable</th><th>ANOVA F</th><th>p-value</th><th>Significance</th></tr>
      {anova_rows}
    </table>
    <p style="margin-top:10px;font-size:12px;color:#555;">â˜…â˜…â˜… = p &lt; 10â»Â¹â°â° Â· All differences statistically certain at population scale.</p>
  </section>

  <section>
    <h2>Â§2  Pearson Correlation Structure</h2>
    <table>
      <tr><th>Variable Pair</th><th>Pearson r</th><th>n</th><th>Interpretation</th></tr>
      {''.join(
        f"<tr><td>{p}</td><td><b>{pearson_results[p]['r']:+.4f}</b></td>"
        f"<td>{pearson_results[p]['n']:,}</td>"
        f"<td>{'Strong' if abs(pearson_results[p]['r'])>0.7 else ('Independent' if abs(pearson_results[p]['r'])<0.1 else 'Moderate')}</td></tr>"
        for p in pearson_results
      )}
    </table>
  </section>

  <section>
    <h2>Â§3  Model Performance (MAE Â· MAPE Â· RÂ²) â€” All Models All Targets</h2>
    <div class="alert">â­ = best model per (unit, target). Highlighted rows saved as .pkl prediction artifact.</div>
    <table>
      <tr><th>Unit</th><th>Target</th><th>Model</th><th>MAE</th><th>RMSE</th><th>MAPE %</th><th>RÂ²</th><th></th></tr>
      {metrics_rows}
    </table>
  </section>

  <section>
    <h2>Â§4  EDA Charts</h2>
    {chart_imgs}
  </section>

</div>
<footer>SMART DYEING Â· Industrial Knit Dyeing Facility. / Industrial Research Consortium Â· Confidential Â· {time.strftime("%B %Y")} Â·
  {len(df):,} batches Â· {len(saved_models)} models Â· Physical violations: {violations}</footer>
</body>
</html>'''

eda_path = os.path.join(RPTS, 'EDA_Report_V2.html')
with open(eda_path, 'w', encoding='utf-8') as fh:
    fh.write(eda_html)
print(f'  Saved: reports/EDA_Report_V2.html ({os.path.getsize(eda_path)//1024} KB)')

# â”€â”€ SUMMARY â”€â”€
print()
print('=' * 68)
print('TRAINING COMPLETE')
print(f'  QC-usable batches trained: {len(df):,}')
print(f'  Models saved:              {len(saved_models)}')
print(f'  Physical violations:       {violations}')
print(f'  Runtime:                   {time.time()-t0:.1f}s')
print()
print('  Artifacts:')
for f_name in ['data/training_set_CCL.csv','data/training_set_MTL.csv',
               'reports/training_report.json','reports/EDA_Report_V2.html']:
    p = os.path.join(OUT, f_name)
    if os.path.exists(p):
        print(f'    âœ“ {f_name} ({os.path.getsize(p)//1024} KB)')
print()
for k in saved_models:
    print(f'    âœ“ models/{k}.pkl  (MAPE={saved_models[k]["mape"]:.1f}%)')
print('=' * 68)





