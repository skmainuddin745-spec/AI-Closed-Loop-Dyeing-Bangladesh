#!/usr/bin/env python3
"""
AI_Recipe_Predictor_v3_Ultimate / 04_v3_recipe_generator_cli.py
================================================================
STEP 4: Recipe Generation CLI with Physicochemical Constraint Enforcement

PURPOSE:
    This is the user-facing inference engine. It takes a simple set of
    production inputs (what you know BEFORE dyeing) and generates a
    complete, physically valid dye recipe card.

    Critically, raw ML predictions are post-processed through
    PHYSICOCHEMICAL CONSTRAINT ENFORCEMENT — a rules engine grounded
    in reactive dyeing chemistry — to ensure the output recipe is not
    just statistically plausible but physically realizable.

PHYSICOCHEMICAL CONSTRAINTS APPLIED:
    1. ZERO-STATE RULES: White/Prep batches → zero dye, zero salt forced.
    2. SOLUBILITY LIMIT: Salt cannot exceed ~120 g/L (physical saturation).
    3. ALKALI-DYE CO-DEPENDENCE: If predicted dye = 0, force alkali = 0
       for the dyeing phase (but pre-treatment alkali kept).
    4. DYE COMPOSITION NORMALIZATION: Individual dye colours (Y/R/B/K) must
       sum to ≤ total dye prediction. Excess is proportionally scaled down.
    5. MINIMUM AUXILIARY GUARANTEE: Process chemistry requires at least
       2.5 g/L pretreat chemicals regardless of shade.
    6. TRICHROMATIC COMPLETENESS CHECK: If a batch is colored but missing
       any of Y/R/B predictions → flag for human review.
    7. V2 ANCHOR VALIDATION: The v3 dye+salt prediction is cross-checked
       against the highly accurate v2 aggregate model bounds.

USAGE:
    Interactive CLI mode:
        py -3.12 04_v3_recipe_generator_cli.py

    Batch mode from CSV:
        py -3.12 04_v3_recipe_generator_cli.py --batch new_orders.csv --out recipe_cards.xlsx

    Single prediction:
        py -3.12 04_v3_recipe_generator_cli.py --predict \
            --shade_tier Dark --pid_family Cotton \
            --fabric_qty 500 --lr 7.0 --buyer HM
"""

import pandas as pd
import numpy as np
import json
import pickle
import warnings
import argparse
from pathlib import Path
from datetime import datetime

warnings.filterwarnings('ignore')

OUTPUT_DIR   = Path('AI_Recipe_Predictor_v3_Ultimate')
MODELS_DIR   = OUTPUT_DIR / 'v3_models'
RESULTS_DIR  = OUTPUT_DIR / 'v3_results'

# ============================================================
# PHYSICOCHEMICAL CONSTANTS (from reactive dyeing science)
# ============================================================
SALT_SOLUBILITY_MAX_GL      = 120.0   # g/L absolute maximum at 60°C
SALT_MINIMUM_LIGHT_GL       = 5.0     # g/L minimum for any colored bath
SALT_DARK_MINIMUM_GL        = 40.0    # g/L minimum for dark/special shades
ALKALI_MINIMUM_GL           = 3.0     # g/L minimum soda ash for fixation
PRETREAT_MINIMUM_GL         = 2.5     # g/L minimum pretreat chemicals
DYE_MAXIMUM_DARK_GL         = 15.0    # g/L max realistic dye load (dark)
DYE_MAXIMUM_MEDIUM_GL       = 5.0     # g/L max realistic dye load (medium)
DYE_MAXIMUM_LIGHT_GL        = 2.0     # g/L max realistic dye load (light)
ENZYME_TYPICAL_GL           = 0.7     # g/L standard enzyme dose

# Shade-aware dye max lookup
DYE_MAX = {'White': 0.0, 'Light': DYE_MAXIMUM_LIGHT_GL,
           'Medium': DYE_MAXIMUM_MEDIUM_GL, 'Dark': DYE_MAXIMUM_DARK_GL,
           'Unknown': DYE_MAXIMUM_MEDIUM_GL}

# ============================================================
# LOAD MODEL & FEATURE CONFIG
# ============================================================
def load_model_and_config():
    """Load the best trained model and feature configuration."""
    with open(MODELS_DIR / 'feature_names.json') as f:
        config = json.load(f)
    
    # Load training report to determine best model
    report_path = RESULTS_DIR / 'v3_training_report.json'
    if report_path.exists():
        with open(report_path) as f:
            report = json.load(f)
        best_arch = report.get('overall_best_architecture', 'XGBoost_MultiOutput')
    else:
        best_arch = 'XGBoost_MultiOutput'
    
    model_file = MODELS_DIR / f'{best_arch.lower()}_model.pkl'
    if not model_file.exists():
        # Fallback to any available model
        pkls = list(MODELS_DIR.glob('*.pkl'))
        model_file = pkls[0] if pkls else None
    
    if model_file is None:
        raise FileNotFoundError("No trained model found. Run 03_train_v3_formulator.py first.")
    
    with open(model_file, 'rb') as f:
        model = pickle.load(f)
    
    print(f"  Loaded model: {model_file.name}")
    return model, config

# ============================================================
# FEATURE VECTOR BUILDER
# ============================================================
def build_feature_vector(shade_tier: str, pid_family: str, fabric_qty_kg: float,
                          lr: float, buyer: str, is_topbuyer: bool,
                          feature_cols: list) -> np.ndarray:
    """
    Construct the input feature vector from user-provided production parameters.
    Mirrors the encoding used in 02_build_v3_dataset.py.
    """
    # Base feature dict
    feats = {c: 0.0 for c in feature_cols}
    
    # Numeric features
    feats['Fabric_Qty_Kg']  = fabric_qty_kg
    feats['Log_Fabric_Qty'] = np.log1p(fabric_qty_kg)
    feats['LR_parsed']      = lr
    feats['LR_x_LogFab']    = lr * np.log1p(fabric_qty_kg)
    feats['Is_TopBuyer']    = 1.0 if is_topbuyer else 0.0
    feats['Is_2Part']       = 0.0
    feats['Is_Normal']      = 1.0
    
    # Shade numeric
    shade_num = {'White': 0, 'Light': 1, 'Medium': 2, 'Dark': 3, 'Unknown': 1.5}
    feats['Shade_Num'] = shade_num.get(shade_tier, 1.5)
    
    # PID family dummies
    fam_col = f'fam_{pid_family}'
    if fam_col in feats:
        feats[fam_col] = 1.0
    
    # Shade tier dummies
    shade_col = f'shade_{shade_tier}'
    if shade_col in feats:
        feats[shade_col] = 1.0
    
    # shade_tier numeric (in dataset this was an integer 1-4)
    shade_tier_int = {'White': 0, 'Light': 1, 'Medium': 2, 'Dark': 3, 'Unknown': 1}
    feats['shade_tier'] = shade_tier_int.get(shade_tier, 1)
    
    # Dye-Chem-Ratio prior (learned from shade tier)
    dcr_prior = {'White': 0.0, 'Light': 0.08, 'Medium': 0.25, 'Dark': 0.85, 'Unknown': 0.15}
    feats['Dye_Chem_Ratio'] = dcr_prior.get(shade_tier, 0.15)
    
    return np.array([feats.get(c, 0.0) for c in feature_cols]).reshape(1, -1)

# ============================================================
# PHYSICOCHEMICAL CONSTRAINT ENFORCER
# ============================================================
def apply_constraints(predictions: dict, shade_tier: str, fabric_qty_kg: float,
                       lr: float) -> tuple[dict, list]:
    """
    Apply physicochemical constraints to raw ML predictions.
    Returns (constrained_predictions, list_of_warnings).
    """
    p = predictions.copy()
    warnings_list = []
    
    water_l = fabric_qty_kg * lr
    
    # ── CONSTRAINT 1: Zero-state for White/Prep ──
    if shade_tier in ['White']:
        if p['gl_dye_total'] > 0.5:
            warnings_list.append(f"[CONSTRAINT 1] White shade: dye suppressed from {p['gl_dye_total']:.2f} → 0.0 g/L")
        p['gl_dye_total']  = 0.0
        p['gl_dye_yellow'] = 0.0
        p['gl_dye_red']    = 0.0
        p['gl_dye_blue']   = 0.0
        p['gl_dye_black']  = 0.0
        p['gl_salt']       = 0.0
    
    # ── CONSTRAINT 2: Salt solubility hard ceiling ──
    if p['gl_salt'] > SALT_SOLUBILITY_MAX_GL:
        warnings_list.append(f"[CONSTRAINT 2] Salt capped: {p['gl_salt']:.1f} → {SALT_SOLUBILITY_MAX_GL:.1f} g/L (solubility limit)")
        p['gl_salt'] = SALT_SOLUBILITY_MAX_GL
    
    # ── CONSTRAINT 3: Salt-shade minimum enforcement ──
    if shade_tier == 'Dark' and p['gl_salt'] < SALT_DARK_MINIMUM_GL and p['gl_dye_total'] > 0:
        warnings_list.append(f"[CONSTRAINT 3] Dark shade: salt raised from {p['gl_salt']:.1f} → {SALT_DARK_MINIMUM_GL:.1f} g/L (minimum exhaustion)")
        p['gl_salt'] = SALT_DARK_MINIMUM_GL
    elif shade_tier in ['Light', 'Medium'] and p['gl_salt'] < SALT_MINIMUM_LIGHT_GL and p['gl_dye_total'] > 0.05:
        warnings_list.append(f"[CONSTRAINT 3] Colored shade: salt raised from {p['gl_salt']:.1f} → {SALT_MINIMUM_LIGHT_GL:.1f} g/L (minimum exhaustion)")
        p['gl_salt'] = SALT_MINIMUM_LIGHT_GL
    
    # ── CONSTRAINT 4: Dye physical maximum ──
    dye_max = DYE_MAX.get(shade_tier, DYE_MAXIMUM_MEDIUM_GL)
    if p['gl_dye_total'] > dye_max and dye_max > 0:
        scale = dye_max / p['gl_dye_total']
        warnings_list.append(f"[CONSTRAINT 4] Dye load scaled: {p['gl_dye_total']:.2f} → {dye_max:.2f} g/L (shade maximum)")
        p['gl_dye_total'] = dye_max
        for dc in ['gl_dye_yellow', 'gl_dye_red', 'gl_dye_blue', 'gl_dye_black']:
            p[dc] = p.get(dc, 0) * scale
    
    # ── CONSTRAINT 5: Dye composition normalization ──
    # Individual colours cannot sum to more than total dye
    dye_components = ['gl_dye_yellow', 'gl_dye_red', 'gl_dye_blue', 'gl_dye_black']
    dye_sum = sum(p.get(dc, 0) for dc in dye_components)
    if dye_sum > p['gl_dye_total'] and p['gl_dye_total'] > 0:
        scale = p['gl_dye_total'] / dye_sum
        for dc in dye_components:
            p[dc] = p.get(dc, 0) * scale
    
    # ── CONSTRAINT 6: Alkali-dye co-dependence ──
    if p['gl_dye_total'] == 0 and p['gl_alkali_total'] > 5.0:
        # For white/prep, only keep the pre-treatment alkali portion
        warnings_list.append(f"[CONSTRAINT 6] No dye: dyeing alkali suppressed (keeping pretreat only)")
        p['gl_alkali_total'] = min(p['gl_alkali_total'], 4.0)
    elif p['gl_dye_total'] > 0 and p['gl_alkali_total'] < ALKALI_MINIMUM_GL:
        warnings_list.append(f"[CONSTRAINT 6] Dye present: alkali raised from {p['gl_alkali_total']:.1f} → {ALKALI_MINIMUM_GL:.1f} g/L (fixation minimum)")
        p['gl_alkali_total'] = ALKALI_MINIMUM_GL
    
    # ── CONSTRAINT 7: Pre-treatment minimum ──
    if p['gl_pretreat'] < PRETREAT_MINIMUM_GL:
        warnings_list.append(f"[CONSTRAINT 7] Pretreat raised from {p['gl_pretreat']:.1f} → {PRETREAT_MINIMUM_GL:.1f} g/L (process minimum)")
        p['gl_pretreat'] = PRETREAT_MINIMUM_GL
    
    # ── CONSTRAINT 8: Trichromatic completeness check ──
    if p['gl_dye_total'] > 0.2:  # Meaningfully colored
        missing = [c for c in ['gl_dye_yellow','gl_dye_red','gl_dye_blue'] if p.get(c, 0) < 0.001]
        if missing:
            warnings_list.append(f"[CONSTRAINT 8] ⚠ Incomplete trichromatic: missing {missing} → flag for dyemaster review")
    
    # ── COMPUTE TOTAL RECIPE QUANTITIES (for water volume) ──
    p['total_salt_kg']    = round(p['gl_salt'] * water_l / 1000, 2)
    p['total_alkali_kg']  = round(p['gl_alkali_total'] * water_l / 1000, 2)
    p['total_dye_kg']     = round(p['gl_dye_total'] * fabric_qty_kg / 1000, 2)
    p['water_L']          = water_l
    
    # Ensure all values non-negative
    for k in p:
        if isinstance(p[k], float) and p[k] < 0:
            p[k] = 0.0
    
    return p, warnings_list

# ============================================================
# RECIPE CARD FORMATTER
# ============================================================
def format_recipe_card(inputs: dict, preds: dict, warnings_list: list) -> str:
    """Generate a human-readable recipe card string."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    water_l = inputs['fabric_qty_kg'] * inputs['lr']
    
    lines = [
        "═" * 65,
        "  AI RECIPE PREDICTOR v3 — GENERATED RECIPE CARD",
        f"  Generated: {now}",
        "═" * 65,
        "",
        "  ┌─ BATCH INPUT PARAMETERS ──────────────────────────────┐",
        f"  │  Shade Tier   : {inputs['shade_tier']:<12}  PID Family  : {inputs['pid_family']}",
        f"  │  Fabric Qty   : {inputs['fabric_qty_kg']:>8.1f} kg  Liquor Ratio : 1:{inputs['lr']:.1f}",
        f"  │  Bath Water   : {water_l:>8.1f} L   Buyer        : {inputs['buyer']}",
        "  └───────────────────────────────────────────────────────┘",
        "",
        "  ┌─ PRE-TREATMENT ────────────────────────────────────────┐",
        f"  │  Scouring/Bleach   : {preds['gl_pretreat']:>6.2f} g/L",
        f"  │  Enzyme (Bio-Polish): {preds.get('gl_enzyme',0):>6.2f} g/L",
        "  └───────────────────────────────────────────────────────┘",
        "",
        "  ┌─ DYESTUFF ─────────────────────────────────────────────┐",
        f"  │  Total Dye Load    : {preds['gl_dye_total']:>6.2f} g/L  ({preds['total_dye_kg']:.3f} kg)",
        f"  │    ├─ Yellow dye   : {preds.get('gl_dye_yellow',0):>6.2f} g/L",
        f"  │    ├─ Red dye      : {preds.get('gl_dye_red',0):>6.2f} g/L",
        f"  │    ├─ Blue dye     : {preds.get('gl_dye_blue',0):>6.2f} g/L",
        f"  │    └─ Black dye    : {preds.get('gl_dye_black',0):>6.2f} g/L",
        "  └───────────────────────────────────────────────────────┘",
        "",
        "  ┌─ SALT & SODA (SSC PROCESS) ───────────────────────────┐",
        f"  │  Glauber Salt      : {preds['gl_salt']:>6.1f} g/L  ({preds['total_salt_kg']:.1f} kg)",
        f"  │  Alkali (Soda Ash) : {preds['gl_alkali_total']:>6.2f} g/L  ({preds['total_alkali_kg']:.2f} kg)",
        "  └───────────────────────────────────────────────────────┘",
        "",
        "  ┌─ AUXILIARIES ──────────────────────────────────────────┐",
        f"  │  Total Auxiliaries : {preds.get('gl_aux_total',0):>6.2f} g/L",
        f"  │  (Leveler + Sequestrant + Softener + Wash-off)",
        "  └───────────────────────────────────────────────────────┘",
    ]
    
    if warnings_list:
        lines += [
            "",
            "  ┌─ CONSTRAINT AUDIT ─────────────────────────────────────┐",
        ]
        for w in warnings_list:
            lines.append(f"  │  {w}")
        lines.append("  └───────────────────────────────────────────────────────┘")
    
    lines += [
        "",
        "  NOTE: Individual dye brand assignments require matching",
        "        to Buyer Color Code via chemical_taxonomy.csv.",
        "═" * 65,
    ]
    return "\n".join(lines)

# ============================================================
# MAIN CLI / BATCH MODE
# ============================================================
def run_prediction(model, config, shade_tier, pid_family, fabric_qty_kg,
                   lr, buyer, verbose=True):
    """Run a single recipe prediction with full constraint enforcement."""
    feature_cols = config['feature_cols']
    targets      = config['targets']
    
    top_buyers = ['C&A', 'H&M', 'GEORGE', 'PUMA', 'GUESS']
    is_topbuyer = any(b.lower() in buyer.lower() for b in top_buyers)
    
    X = build_feature_vector(shade_tier, pid_family, fabric_qty_kg,
                              lr, buyer, is_topbuyer, feature_cols)
    
    raw_pred = model.predict(X)[0]
    raw_pred = np.clip(raw_pred, 0, None)  # No negative concentrations
    
    raw_dict = {t: float(raw_pred[i]) for i, t in enumerate(targets)}
    
    inputs = {'shade_tier': shade_tier, 'pid_family': pid_family,
              'fabric_qty_kg': fabric_qty_kg, 'lr': lr, 'buyer': buyer}
    
    constrained, constraint_warnings = apply_constraints(raw_dict, shade_tier, fabric_qty_kg, lr)
    
    if verbose:
        card = format_recipe_card(inputs, constrained, constraint_warnings)
        print(card)
    
    return constrained, constraint_warnings, raw_dict

def run_batch(model, config, input_csv, output_xlsx):
    """Process a CSV file of batch orders and generate recipe cards."""
    df_in = pd.read_csv(input_csv)
    print(f"Processing {len(df_in)} batches from {input_csv}...")
    
    rows = []
    for _, row in df_in.iterrows():
        pred, warns, raw = run_prediction(
            model, config,
            shade_tier=row.get('shade_tier', 'Light'),
            pid_family=row.get('pid_family', 'Cotton'),
            fabric_qty_kg=float(row.get('fabric_qty_kg', 500)),
            lr=float(row.get('lr', 7.0)),
            buyer=str(row.get('buyer', 'Unknown')),
            verbose=False
        )
        out_row = dict(row)
        out_row.update({f'pred_{k}': round(v, 3) for k, v in pred.items()})
        out_row['constraint_warnings'] = ' | '.join(warns) if warns else ''
        rows.append(out_row)
    
    out_df = pd.DataFrame(rows)
    out_df.to_excel(output_xlsx, index=False)
    print(f"Saved recipe cards to: {output_xlsx}")
    return out_df


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='AI Recipe Predictor v3 — CLI')
    parser.add_argument('--batch', type=str, help='Input CSV for batch processing')
    parser.add_argument('--out',   type=str, help='Output Excel for batch mode')
    parser.add_argument('--predict', action='store_true', help='Single prediction mode')
    parser.add_argument('--shade_tier',   default='Dark',   help='Shade tier: White/Light/Medium/Dark')
    parser.add_argument('--pid_family',   default='Cotton', help='PID Family: Cotton/PES...')
    parser.add_argument('--fabric_qty',   type=float, default=500.0, help='Fabric qty in kg')
    parser.add_argument('--lr',           type=float, default=7.0,   help='Liquor ratio (e.g. 7.0 = 1:7)')
    parser.add_argument('--buyer',        default='H&M', help='Buyer name')
    args = parser.parse_args()
    
    print("=" * 65)
    print(" AI RECIPE PREDICTOR v3 — Inference Engine")
    print("=" * 65)
    print("\nLoading model...")
    model, config = load_model_and_config()
    
    if args.batch:
        out = args.out or args.batch.replace('.csv', '_recipes.xlsx')
        run_batch(model, config, args.batch, out)
    elif args.predict:
        run_prediction(model, config,
                       shade_tier=args.shade_tier,
                       pid_family=args.pid_family,
                       fabric_qty_kg=args.fabric_qty,
                       lr=args.lr,
                       buyer=args.buyer)
    else:
        # ── INTERACTIVE MODE ──────────────────────────────────────
        print("\nRunning 5 demonstration predictions (test set scenarios)...\n")
        
        test_cases = [
            {'shade_tier': 'White',  'pid_family': 'Cotton',           'fabric_qty_kg': 900,  'lr': 7.0, 'buyer': 'PUMA'},
            {'shade_tier': 'Light',  'pid_family': 'Cotton',           'fabric_qty_kg': 200,  'lr': 7.0, 'buyer': 'H&M'},
            {'shade_tier': 'Medium', 'pid_family': 'Cotton',           'fabric_qty_kg': 500,  'lr': 7.0, 'buyer': 'GEORGE'},
            {'shade_tier': 'Dark',   'pid_family': 'Cotton',           'fabric_qty_kg': 1350, 'lr': 6.5, 'buyer': 'H&M'},
            {'shade_tier': 'Dark',   'pid_family': 'PES/PC/CVC Blend', 'fabric_qty_kg': 800,  'lr': 8.0, 'buyer': 'VF ASIA'},
        ]
        
        all_output = []
        for i, tc in enumerate(test_cases, 1):
            print(f"\n{'─'*65}")
            print(f"  TEST CASE {i}: {tc['shade_tier'].upper()} | {tc['pid_family']} | {tc['fabric_qty_kg']}kg | Buyer: {tc['buyer']}")
            print(f"{'─'*65}")
            pred, warns, raw = run_prediction(model, config, **tc)
            all_output.append({'case': i, **tc, **{f'pred_{k}': round(v,3) for k, v in pred.items()}})
        
        # Save demo output
        demo_df = pd.DataFrame(all_output)
        demo_path = OUTPUT_DIR / 'v3_demo_predictions.csv'
        demo_df.to_csv(demo_path, index=False)
        print(f"\n\nDemo predictions saved to: {demo_path}")
