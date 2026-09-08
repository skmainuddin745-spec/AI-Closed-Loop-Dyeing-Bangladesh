#!/usr/bin/env python3
"""
AI_Recipe_Predictor_v3_Ultimate / 01_chemical_tokenizer.py
============================================================
STEP 1: Rigorous Chemical Tokenization and Class Assignment

PURPOSE:
    Every chemical used in reactive dyeing has a specific functional role:
    Dye (chromophore), Salt (exhaustion), Alkali (fixation), Enzyme (bio-finish),
    Leveling Agent, Sequestering Agent, Defoamer, Wash-Off/Soaping, etc.
    
    v1 and v2 models treated these as opaque black-box names. This script
    builds a scientifically rigorous chemical taxonomy using pattern matching,
    then assigns each of the 196 unique chemicals to its correct functional class.
    
    This is the FOUNDATION of v3 â€” without accurate chemical class labels,
    the multi-output ML model cannot learn meaningful patterns.

SCIENTIFIC BASIS:
    Classification follows standard reactive dyeing process chemistry:
    Phase 1 - Pre-treatment (Scour/Bleach)
    Phase 2 - Enzymatic treatment (Bio-Finish)
    Phase 3 - Dyestuff application (Dye + Salt)
    Phase 4 - Fixation (Alkali)
    Phase 5 - Wash-off/Soaping (Auxiliaries)

OUTPUTS:
    - chemical_taxonomy.csv: Master chemical â†’ class mapping
    - tokenized_recipes.csv: All 12,604 lines with class label
    - tokenizer_report.json: Classification statistics

AUTHOR: AI_Recipe_Predictor_v3_Ultimate Pipeline
"""

import pandas as pd
import numpy as np
import json
import re
from pathlib import Path

# ============================================================
# CONFIGURATION
# ============================================================
INPUT_RECIPES  = 'data/industrial_batch_dataset.csv'
INPUT_MASTER   = 'data/PID_Master_Recipe.csv'
OUTPUT_DIR     = Path('AI_Recipe_Predictor_v3_Ultimate')
OUTPUT_DIR.mkdir(exist_ok=True)

# ============================================================
# CHEMICAL TAXONOMY (Rigorously defined by dye chemistry)
# ============================================================
# Order matters: more specific patterns FIRST
CHEMICAL_TAXONOMY = {
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ REACTIVE DYES â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    'DYE_YELLOW': [
        r'yellow', r'golden', r'lemon', r's-3r', r's-w\b', r's8gn', r'yellow.*s-matrix',
        r'f-4g', r'f-?3g', r'f-?2g', r's-gr', r'gl\b'
    ],
    'DYE_RED': [
        r'red', r'carmine', r'scarlet', r'ruby', r'cosmos.*carmine', r's-2b', r'f-3b',
        r'f-2b', r'rb\b', r'r\b(?=.*dye|.*bezaktiv|.*novacron)'
    ],
    'DYE_BLUE': [
        r'blue', r'turquoise', r'navy', r'bezaktiv.*blue', r'novacron.*blue',
        r'sw\b', r'b\b(?=.*dye|.*bezaktiv|.*novacron)', r'rblueblack'
    ],
    'DYE_BLACK': [
        r'black', r'super black', r'jet black', r'rblack', r'go\b(?=.*dye|.*black)'
    ],
    'DYE_VIOLET': [r'violet', r'purple', r'mauve'],
    'DYE_ORANGE': [r'orange', r'amber'],
    'DYE_NAVY': [r'navy(?!.*blue)', r'marine'],  # standalone navy
    'DYE_OTHER': [
        r'bezaktiv', r'novacron', r'drimaren', r'remazol', r'synozol',
        r'avitera', r'dianix', r'bemacron', r'neocron', r'drimagen',
        r'levafix', r'sumifix', r'procion', r'ostazin', r'cibacron',
        r'reactive\s+dye', r'dyeex', r'dyex'
    ],

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ ELECTROLYTE (SALT) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    'SALT': [
        r'soudiam sulphate', r'sodium sulphate', r'sodium sulfate',
        r'glauber', r'salt', r'nacl', r'common salt', r'sulphate.*viscose'
    ],

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ ALKALI / FIXATION â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    'ALKALI_SODA': [r'soda ash', r'sodium carbonate', r'na2co3', r'soda\s+ash'],
    'ALKALI_CAUSTIC': [
        r'caustic soda', r'naoh', r'sodium hydroxide', r'caustic.*prills',
        r'caustic.*flake', r'sodium bi carb', r'sodium bic', r'sodium.*bicorb'
    ],

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ PRE-TREATMENT â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    'PRETREAT_BLEACH': [
        r'hydrogen per.?oxide', r'h2o2', r'bleach(?!.*wash)', r'verio bleach',
        r'peroxide'
    ],
    'PRETREAT_SCOUR': [
        r'rucogen', r'scouring', r'winscour', r'rossacid', r'bioprep',
        r'avco.?tex', r'detergent', r'wetting', r'permelan', r'kieralon',
        r'leophen', r'lissapol', r'multiscour', r'neoscour', r'bainco.*scour',
        r'felosan', r'egasol', r'surfox', r'tubingal', r'contavan',
        r'fastasol', r'lorinol', r'prima.*green', r'jingen', r'potex',
        r'cht.*disper', r'meropan', r'securon', r'arristan'
    ],

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ ENZYME â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    'ENZYME': [
        r'cellusoft', r'invazyme', r'rkzyme', r'enzyme', r'biopolish',
        r'endolase', r'bactosol', r'ecostone', r'novozyme', r'celluclean',
        r'indiage', r'conzyme', r'applizyme', r'acid cellulase', r'cht.*catalase',
        r'midori.*cat', r'crosprep'
    ],

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ LEVELING / MIGRATION â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    'LEVELER': [
        r'levell?er', r'levelling', r'level.?1488', r'albatex', r'sarabid',
        r'antimussol', r'avco.*levell?er', r'migration', r'cotobalance',
        r'nylofixan', r'levegal', r'avco.?levpol', r'cyclanon', r'maga.*b',
        r'nicca.*sunsolt', r'depicol', r'sapamine'
    ],

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ SEQUESTERING / CHELATING â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    'SEQUESTRANT': [
        r'oxinol', r'sequester', r'chelat', r'rossacid', r'prestogen',
        r'sodium hexameta', r'edta', r'trilon', r'dequest', r'invatex',
        r'neosol', r'complexing', r'lavan', r'optifix', r'albafix',
        r'serafast', r'dbc.*10', r'rucofin'
    ],

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ WASH-OFF / SOAPING â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    'WASH_OFF': [
        r'soaping', r'soap.?off', r'wash.?off', r'lexex', r'albaflow',
        r'dyex', r'dyel', r'kelite', r'sirrix', r'eriopon', r'leocol',
        r'nonionic.*detergent', r'decol', r'felasan', r'cht.*disper',
        r'chi.*x'
    ],

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ SOFTENER / FINISHING â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    'SOFTENER': [
        r'softener', r'lubricant', r'lubrication', r'silicon', r'biavin',
        r'celpolish', r'verinol', r'hydro.*soft', r'mesoft', r'neosoft',
        r'lanaset', r'primasil', r'texsoft', r'neo.?soft', r'neosil',
        r'persoftal', r'novolube', r'microfinish', r'rucofin'
    ],

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ ANTI-FOAM â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    'ANTIFOAM': [r'antifoam', r'anti.?foam', r'defoam', r'anti.?mussol', r'contol'],

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ ACID / pH CONTROL â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    'ACID_pH': [
        r'citric acid', r'acetic acid', r'formic acid', r'buffer', r'ph.*regul',
        r'acidol', r'kieracid', r'glauber.*acid'
    ],

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ REDUCTION CLEANER â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    'REDUCTION_CLEANER': [
        r'hydrose', r'sodium hydrosulphite', r'hydrosulphite', r'sodium sulphoxylate',
        r'reduction.*clean', r'hydronate'
    ],

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ OPTICAL BRIGHTENER â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    'OBA': [
        r'optical brightener', r'oba', r'blankophor', r'tinopal', r'uvitex',
        r'signo white', r'syno white', r'ultraphor', r'threephor'
    ],
}

# ============================================================
# TOKENIZER FUNCTION
# ============================================================
def classify_chemical(name: str) -> str:
    """
    Assigns a chemical to its functional class using the scientific taxonomy.
    Returns the class name or 'UNCLASSIFIED' if no pattern matches.
    """
    if pd.isna(name):
        return 'UNCLASSIFIED'
    n = name.lower().strip()
    for chem_class, patterns in CHEMICAL_TAXONOMY.items():
        for pat in patterns:
            if re.search(pat, n):
                return chem_class
    return 'UNCLASSIFIED'

# ============================================================
# MAIN
# ============================================================
print("=" * 70)
print("AI RECIPE PREDICTOR v3 â€” Step 1: Chemical Tokenizer")
print("=" * 70)

print("\n[1] Loading raw recipe data...")
df = pd.read_csv(INPUT_RECIPES)
master = pd.read_csv(INPUT_MASTER)
print(f"    Recipe lines: {len(df):,}  |  Unique batches: {df['Batch_No'].nunique():,}")
print(f"    Unique chemicals: {df['Item_Name'].nunique():,}")

print("\n[2] Building chemical taxonomy (rigorous pattern matching)...")
# Build master taxonomy for all unique chemicals
unique_chems = pd.DataFrame({'Item_Name': df['Item_Name'].unique()})
unique_chems['Chem_Class'] = unique_chems['Item_Name'].apply(classify_chemical)

# Show classification results
class_counts = unique_chems['Chem_Class'].value_counts()
print(f"\n    Classification results ({len(unique_chems)} unique chemicals):")
for cls, cnt in class_counts.items():
    pct = cnt / len(unique_chems) * 100
    print(f"    {cls:<25} {cnt:3d}  ({pct:.1f}%)")

# Show unclassified for human review
unclassified = unique_chems[unique_chems['Chem_Class'] == 'UNCLASSIFIED']
if len(unclassified) > 0:
    print(f"\n    UNCLASSIFIED chemicals ({len(unclassified)}) â€” need review:")
    for c in unclassified['Item_Name'].tolist():
        print(f"      - {c}")

print("\n[3] Applying classification to all recipe lines...")
df = df.merge(unique_chems, on='Item_Name', how='left')

# Collapse dye sub-classes into parent DYE for aggregation convenience
df['Chem_Class_Broad'] = df['Chem_Class'].apply(
    lambda x: 'DYE' if str(x).startswith('DYE_') else x
)

# QA check
print(f"\n    Classified lines:   {(df['Chem_Class'] != 'UNCLASSIFIED').sum():,} / {len(df):,}")
print(f"    Classification rate: {(df['Chem_Class'] != 'UNCLASSIFIED').mean()*100:.1f}%")

print("\n[4] Merging with master batch data...")
# Clean the Color_Depth column (it often has raw HTML appended)
def clean_color_depth(s):
    if pd.isna(s): return np.nan
    # The column contains things like "SPECIAL(B/R) Buyer Name : PUMA Fabric Qty : ..."
    # Just take the first word/token
    s = str(s).strip()
    match = re.match(r'^([A-Z/\(\)]+)', s)
    return match.group(1) if match else s.split()[0]

master['Color_Depth_Clean'] = master['Color_Depth'].apply(clean_color_depth)

# Parse fabric quantity and liquor ratio from the raw Color_Depth / Fabric_Type blobs
def parse_fabric_qty(s):
    if pd.isna(s): return np.nan
    m = re.search(r'Fabric Qty\s*:\s*([\d,\.]+)', str(s))
    if m: return float(m.group(1).replace(',', ''))
    return np.nan

def parse_water(s):
    if pd.isna(s): return np.nan
    m = re.search(r'Water\s*:\s*([\d,\.]+)', str(s))
    if m: return float(m.group(1).replace(',', ''))
    return np.nan

def parse_lr(s):
    if pd.isna(s): return np.nan
    # Matches patterns like: "Liquor Ratio 1 : 7.00" or "AOP Liquor Ratio 1 : 6.00"
    m = re.search(r'Liquor Ratio\s*(?:\d+\s*)?:\s*([\d\.]+)', str(s))
    if m: return float(m.group(1))
    # Fallback: direct ratio after any colon following LR
    m2 = re.search(r'LR\s+1\s*:\s*([\d\.]+)', str(s))
    if m2: return float(m2.group(1))
    return np.nan

master['Fabric_Qty_Kg'] = master['Color_Depth'].apply(parse_fabric_qty)
master['Water_L']       = master['Color_Depth'].apply(parse_water)
master['LR_parsed']     = master['Color_Depth'].apply(parse_lr)
master['LR_computed']   = master['Water_L'] / master['Fabric_Qty_Kg']

# Quick parse of dyeing type (Normal / 2Part / etc)
def parse_dyeing_type(s):
    if pd.isna(s): return 'Normal'
    m = re.search(r'Status:\s*(\w+)', str(s))
    return m.group(1) if m else 'Normal'

master['Dyeing_Type'] = master['Color_Depth'].apply(parse_dyeing_type)

print(f"    Parsed Fabric_Qty_Kg: {master['Fabric_Qty_Kg'].notna().sum()} batches")
print(f"    Parsed LR: {master['LR_parsed'].notna().sum()} batches")
print(f"    Dyeing_Type: {master['Dyeing_Type'].value_counts().to_dict()}")
print(f"    Color_Depth_Clean: {master['Color_Depth_Clean'].value_counts().head(8).to_dict()}")

# Merge classified lines with master
merged = df.merge(
    master[['Batch_No','Shade','PID_Final','PID_Family','Color_Depth_Clean',
            'Salt_GL','Soda_GL','Buyer_Clean','shade_tier','Fabric_Qty_Kg',
            'Water_L','LR_parsed','LR_computed','Dyeing_Type']],
    on='Batch_No', how='left'
)

print("\n[5] Saving outputs...")
# Save taxonomy
unique_chems.sort_values('Chem_Class').to_csv(OUTPUT_DIR / 'chemical_taxonomy.csv', index=False)
print(f"    Saved: chemical_taxonomy.csv  ({len(unique_chems)} chemicals)")

# Save tokenized recipes
merged.to_csv(OUTPUT_DIR / 'tokenized_recipes.csv', index=False)
print(f"    Saved: tokenized_recipes.csv  ({len(merged):,} lines)")

# Save report
report = {
    'total_lines': len(merged),
    'unique_batches': merged['Batch_No'].nunique(),
    'unique_chemicals': len(unique_chems),
    'classification_rate_pct': round((df['Chem_Class'] != 'UNCLASSIFIED').mean()*100, 2),
    'class_distribution': class_counts.to_dict(),
    'shade_distribution': df.groupby('Batch_No')['Shade'].first().value_counts().to_dict() if 'Shade' in df.columns else {},
    'color_depth_distribution': master['Color_Depth_Clean'].value_counts().to_dict(),
    'pid_family_distribution': master['PID_Family'].value_counts().to_dict(),
    'fabric_qty_stats': {
        'mean': round(master['Fabric_Qty_Kg'].mean(), 1),
        'min': round(master['Fabric_Qty_Kg'].min(), 1),
        'max': round(master['Fabric_Qty_Kg'].max(), 1),
        'notna': int(master['Fabric_Qty_Kg'].notna().sum())
    },
    'lr_stats': {
        'mean': round(master['LR_computed'].mean(), 2),
        'min': round(master['LR_computed'].min(), 2),
        'max': round(master['LR_computed'].max(), 2),
    },
    'unclassified_chemicals': unclassified['Item_Name'].tolist()
}
with open(OUTPUT_DIR / 'tokenizer_report.json', 'w') as f:
    json.dump(report, f, indent=2)
print(f"    Saved: tokenizer_report.json")

print("\n" + "=" * 70)
print("STEP 1 COMPLETE")
print(f"  Classification rate: {report['classification_rate_pct']}%")
print(f"  Tokenized {report['total_lines']:,} lines across {report['unique_batches']} batches")
print(f"  Next: Run 02_build_v3_dataset.py")
print("=" * 70)

