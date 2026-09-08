#!/usr/bin/env python3
"""
AI_Recipe_Predictor_v3_Ultimate / 02_build_v3_dataset.py
==========================================================
STEP 2: Build the Multi-Target ML Training Dataset

PURPOSE:
    Transforms the 12,604 tokenized recipe lines into a FLAT, batch-level
    feature matrix suitable for multi-output machine learning.

    This is the most scientifically critical data engineering step.
    Each row = ONE BATCH.
    Input features (X) = Production parameters we KNOW before dyeing begins.
    Output targets (y) = The full recipe concentrations we want to PREDICT.

SCIENTIFIC APPROACH:
    - TARGETS: We pivot the GL_pct concentrations by chemical class to create
      separate output columns for each class (Salt, Alkali, Total_Dye,
      Yellow_Dye, Red_Dye, Blue_Dye, Black_Dye, Enzyme, Aux).
    - FEATURES: We engineer production-level features from the master data
      (Shade Category, PID Family, Color Depth, Fabric Qty, Buyer, etc.)
    - VALIDATION: We verify the dataset against the highly accurate v2
      aggregate predictions (Salt_GL, Soda_GL) to confirm data integrity.

DATA LINEAGE:
    tokenized_recipes.csv  (12,604 lines from Step 1)
    +
    data/PID_Master_Recipe.csv  (master batch info)
    +
    data/DEEP_ROOT_Batch_Enriched.csv (v2 link, if exists)
    â†’ v3_training_dataset.csv  (660 rows Ã— ~40 columns)

OUTPUTS:
    - v3_training_dataset.csv: Finalized ML training dataset
    - v3_dataset_report.json: Statistics and data quality audit
"""

import pandas as pd
import numpy as np
import json
import re
from pathlib import Path

OUTPUT_DIR = Path('AI_Recipe_Predictor_v3_Ultimate')

print("=" * 70)
print("AI RECIPE PREDICTOR v3 â€” Step 2: Build Training Dataset")
print("=" * 70)

# ============================================================
# [1] LOAD TOKENIZED LINES
# ============================================================
print("\n[1] Loading tokenized recipe lines...")
tok = pd.read_csv(OUTPUT_DIR / 'tokenized_recipes.csv')
master = pd.read_csv('data/PID_Master_Recipe.csv')
print(f"    Lines loaded: {len(tok):,}  |  Batches: {tok['Batch_No'].nunique():,}")

# Fix the "SODIUM BI CORBONATE" = Alkali Caustic (typo for sodium bicarbonate)
tok.loc[tok['Item_Name'] == 'SODIUM BI CORBONATE', 'Chem_Class'] = 'ALKALI_CAUSTIC'
tok.loc[tok['Item_Name'] == 'SODIUM BI CORBONATE', 'Chem_Class_Broad'] = 'ALKALI_CAUSTIC'

# ============================================================
# [2] PIVOT: Create target columns (one per chemical class)
# ============================================================
print("\n[2] Pivoting recipe lines to batch-level target matrix...")

# Sum GL_pct by Batch Ã— Chem_Class
pivot = tok.groupby(['Batch_No', 'Chem_Class'])['GL_pct'].sum().unstack(fill_value=0)
pivot.columns = [f"gl_{c.lower()}" for c in pivot.columns]
pivot = pivot.reset_index()

# Compute convenient aggregations
dye_cols = [c for c in pivot.columns if c.startswith('gl_dye_')]
pivot['gl_dye_total']   = pivot[dye_cols].sum(axis=1)
pivot['gl_alkali_total']= pivot.get('gl_alkali_soda', 0) + pivot.get('gl_alkali_caustic', 0)
pivot['gl_salt']        = pivot.get('gl_salt', 0)
pivot['gl_enzyme']      = pivot.get('gl_enzyme', 0)
pivot['gl_leveler']     = pivot.get('gl_leveler', 0)
pivot['gl_sequestrant'] = pivot.get('gl_sequestrant', 0)
pivot['gl_softener']    = pivot.get('gl_softener', 0)
pivot['gl_wash_off']    = pivot.get('gl_wash_off', 0)
pivot['gl_pretreat']    = pivot.get('gl_pretreat_scour', 0) + pivot.get('gl_pretreat_bleach', 0)
pivot['gl_oba']         = pivot.get('gl_oba', 0)
pivot['gl_acid_ph']     = pivot.get('gl_acid_ph', 0)
pivot['gl_aux_total']   = (pivot['gl_leveler'] + pivot['gl_sequestrant'] +
                           pivot['gl_softener'] + pivot['gl_wash_off'] +
                           pivot['gl_pretreat'] + pivot['gl_oba'] + pivot['gl_acid_ph'])
pivot['n_recipe_lines'] = tok.groupby('Batch_No').size().values

print(f"    Pivot shape: {pivot.shape}")
print(f"    Dye sub-columns found: {dye_cols}")

# ============================================================
# [3] PARSE PRODUCTION FEATURES FROM MASTER
# ============================================================
print("\n[3] Engineering input features from master batch data...")

def clean_color_depth(s):
    """Extract just the colour depth code, strip trailing HTML blob."""
    if pd.isna(s): return 'UNKNOWN'
    s = str(s).strip()
    # Take first token of uppercase letters, slashes, parens, dashes
    match = re.match(r'^([A-Z/\(\)\-]+)', s)
    return match.group(1) if match else s.split()[0].upper()

def parse_fabric_qty(s):
    if pd.isna(s): return np.nan
    m = re.search(r'Fabric Qty\s*:\s*([\d,\.]+)', str(s))
    return float(m.group(1).replace(',', '')) if m else np.nan

def parse_water(s):
    if pd.isna(s): return np.nan
    m = re.search(r'\bWater\s*:\s*([\d,\.]+)', str(s))
    return float(m.group(1).replace(',', '')) if m else np.nan

def parse_lr(s):
    if pd.isna(s): return np.nan
    m = re.search(r'Liquor Ratio\s*(?:\d+\s*)?:\s*([\d\.]+)', str(s))
    if m: return float(m.group(1))
    return np.nan

def parse_dyeing_type(s):
    if pd.isna(s): return 'Normal'
    m = re.search(r'Status:\s*(\w+)', str(s))
    return m.group(1) if m else 'Normal'

master['Color_Depth_Clean'] = master['Color_Depth'].apply(clean_color_depth)
master['Fabric_Qty_Kg']     = master['Color_Depth'].apply(parse_fabric_qty)
master['Water_L']           = master['Color_Depth'].apply(parse_water)
master['LR_parsed']         = master['Color_Depth'].apply(parse_lr)
master['LR_computed']       = master['Water_L'] / master['Fabric_Qty_Kg']
master['Dyeing_Type']       = master['Color_Depth'].apply(parse_dyeing_type)

# LR fallback: if Color_Depth parse fails, try the raw Fabric_Type column
lr_miss = master['LR_parsed'].isna()
master.loc[lr_miss, 'LR_parsed'] = master.loc[lr_miss, 'Fabric_Type'].apply(parse_lr)
lr_miss2 = master['LR_parsed'].isna()
master.loc[lr_miss2, 'LR_parsed'] = master.loc[lr_miss2, 'LR_computed']

print(f"    Fabric_Qty_Kg parsed: {master['Fabric_Qty_Kg'].notna().sum()} batches")
print(f"    LR parsed: {master['LR_parsed'].notna().sum()} batches")
print(f"    Color_Depth_Clean distribution: {master['Color_Depth_Clean'].value_counts().head(8).to_dict()}")
print(f"    Dyeing_Type: {master['Dyeing_Type'].value_counts().to_dict()}")

# ============================================================
# [4] MAP SHADE TIERS TO CLEAN LABELS
# ============================================================
# Color_Depth_Clean â†’ 6-level shade tier matching v2 K-means bins
shade_map = {
    'LIGHT'       : 'Light',
    'WHITE'       : 'White',
    'MEDIUM'      : 'Medium',
    'DARK'        : 'Dark',
    'EXTRADARK'   : 'Dark',
    'SPECIAL(B/R)': 'Dark',
    'RBLUEBLACK'  : 'Dark',
    'WASH'        : 'White',
    'UNKNOWN'     : 'Unknown',
}
master['Shade_Tier'] = master['Color_Depth_Clean'].map(shade_map).fillna('Unknown')

print(f"\n    Shade_Tier: {master['Shade_Tier'].value_counts().to_dict()}")

# ============================================================
# [5] ENCODE CATEGORICAL FEATURES
# ============================================================
print("\n[5] Encoding categorical features...")

# PID Family encoding
pid_dummies = pd.get_dummies(master['PID_Family'], prefix='fam')

# Shade tier encoding
shade_dummies = pd.get_dummies(master['Shade_Tier'], prefix='shade')

# Dyeing type binary
master['Is_2Part']     = (master['Dyeing_Type'] == '2Part').astype(int)
master['Is_Normal']    = (master['Dyeing_Type'] == 'Normal').astype(int)

# Buyer importance flag (top 5 buyers = 1)
top_buyers = master['Buyer_Clean'].value_counts().head(5).index.tolist()
master['Is_TopBuyer']  = master['Buyer_Clean'].isin(top_buyers).astype(int)

# Log transform fabric qty (to handle 13 kg â†’ 1,352 kg range)
master['Log_Fabric_Qty'] = np.log1p(master['Fabric_Qty_Kg'])

# LR interaction
master['LR_x_LogFab'] = master['LR_parsed'] * master['Log_Fabric_Qty']

# Shade tier numeric
shade_num = {'White': 0, 'Light': 1, 'Medium': 2, 'Dark': 3, 'Unknown': 1.5}
master['Shade_Num']    = master['Shade_Tier'].map(shade_num)

# Merge all master features
master_features = pd.concat([
    master[['Batch_No','Shade','PID_Final','PID_Family','Shade_Tier','Shade_Num',
            'Salt_GL','Soda_GL','Buyer_Clean','shade_tier',
            'Fabric_Qty_Kg','Log_Fabric_Qty','LR_parsed','LR_computed',
            'LR_x_LogFab','Is_2Part','Is_Normal','Is_TopBuyer','Chem_Cost',
            'Dyes_Cost','Total_Cost','Dye_Chem_Ratio']],
    pid_dummies,
    shade_dummies
], axis=1)

# ============================================================
# [6] MERGE FEATURES + TARGETS
# ============================================================
print("\n[6] Merging features and targets...")
df = pivot.merge(master_features, on='Batch_No', how='inner')
print(f"    Final dataset: {df.shape[0]} batches Ã— {df.shape[1]} columns")

# ============================================================
# [7] DATA QUALITY CHECKS (Cross-validate against v2 known values)
# ============================================================
print("\n[7] Data quality validation...")

# Cross-validate Salt GL against v2 known Salt_GL
both_salt = df[df['Salt_GL'].notna() & (df['Salt_GL'] > 0) & (df['gl_salt'] > 0)]
if len(both_salt) > 0:
    corr_salt = both_salt['Salt_GL'].corr(both_salt['gl_salt'])
    print(f"    Salt_GL (master) vs gl_salt (parsed) correlation: r={corr_salt:.3f}  (n={len(both_salt)})")
    mae_salt = (both_salt['Salt_GL'] - both_salt['gl_salt']).abs().mean()
    print(f"    Salt MAE (master vs parsed): {mae_salt:.2f} g/L  â€” should be <2.0")

# Cross-validate Alkali against Soda_GL
both_alk = df[df['Soda_GL'].notna() & (df['Soda_GL'] > 0) & (df['gl_alkali_total'] > 0)]
if len(both_alk) > 0:
    corr_alk = both_alk['Soda_GL'].corr(both_alk['gl_alkali_total'])
    print(f"    Soda_GL (master) vs gl_alkali_total (parsed) correlation: r={corr_alk:.3f}  (n={len(both_alk)})")

# Distribution stats for each target
target_cols = ['gl_salt','gl_alkali_total','gl_dye_total',
               'gl_dye_yellow','gl_dye_red','gl_dye_blue','gl_dye_black',
               'gl_enzyme','gl_pretreat','gl_aux_total']
existing_targets = [c for c in target_cols if c in df.columns]

print(f"\n    Target statistics (g/L concentrations):")
print(f"    {'Target':<22} {'Non-zero':<10} {'Mean':>8} {'Median':>8} {'Max':>8}")
print(f"    {'-'*60}")
for col in existing_targets:
    nz = (df[col] > 0).sum()
    print(f"    {col:<22} {nz:<10} {df[col].mean():>8.2f} {df[col].median():>8.2f} {df[col].max():>8.2f}")

# Check for shade-wise separation (key validation)
print(f"\n    Shade-tier dye separation (g/L):")
for shade in ['White','Light','Medium','Dark']:
    mask = df['Shade_Tier'] == shade
    if mask.sum() > 0:
        dye_med = df.loc[mask, 'gl_dye_total'].median()
        salt_med = df.loc[mask, 'gl_salt'].median()
        n = mask.sum()
        print(f"      {shade:<8}: n={n:3d}  Dye_median={dye_med:6.2f} g/L  Salt_median={salt_med:6.1f} g/L")

# ============================================================
# [8] TRAIN/TEST SPLIT
# ============================================================
from sklearn.model_selection import train_test_split
np.random.seed(42)
train_df, test_df = train_test_split(df, test_size=0.2, random_state=42,
                                      stratify=df['Shade_Tier'].fillna('Unknown'))

print(f"\n[8] Train/Test split:")
print(f"    Train: {len(train_df)} batches  |  Test: {len(test_df)} batches")

# ============================================================
# [9] SAVE
# ============================================================
print("\n[9] Saving outputs...")
df.to_csv(OUTPUT_DIR / 'v3_training_dataset.csv', index=False)
train_df.to_csv(OUTPUT_DIR / 'v3_train.csv', index=False)
test_df.to_csv(OUTPUT_DIR / 'v3_test.csv', index=False)

print(f"    Saved: v3_training_dataset.csv  ({len(df)} rows)")
print(f"    Saved: v3_train.csv  ({len(train_df)} rows)")
print(f"    Saved: v3_test.csv  ({len(test_df)} rows)")

# Save metadata
meta = {
    'n_batches': len(df),
    'n_train': len(train_df),
    'n_test': len(test_df),
    'n_features': len([c for c in df.columns if c not in existing_targets]),
    'targets': existing_targets,
    'feature_columns': [c for c in df.columns if c not in existing_targets and c != 'Batch_No'],
    'shade_dist_train': train_df['Shade_Tier'].value_counts().to_dict(),
    'salt_cross_corr': round(corr_salt, 4) if 'corr_salt' in dir() else None,
    'alkali_cross_corr': round(corr_alk, 4) if 'corr_alk' in dir() else None,
}
with open(OUTPUT_DIR / 'v3_dataset_report.json', 'w') as f:
    json.dump(meta, f, indent=2)
print(f"    Saved: v3_dataset_report.json")

print("\n" + "=" * 70)
print("STEP 2 COMPLETE")
print(f"  Dataset: {len(df)} batches Ã— {df.shape[1]} columns")
print(f"  Targets: {len(existing_targets)} chemical concentrations")
print(f"  Next: Run 03_train_v3_formulator.py")
print("=" * 70)

