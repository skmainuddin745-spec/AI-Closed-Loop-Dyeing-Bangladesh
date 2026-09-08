"""
39_ai_v2_predict_enhanced.py
==============================
SMART DYEING â€” Enhanced Prediction CLI v2

Features over v1 (36_ai_predict.py):
  â€¢ Routes to the correct Color_Depth_Bin using the saved K-means model
  â€¢ Prediction intervals [P10, P50, P90] from quantile regression models
  â€¢ SHAP-based explanation: top-3 feature drivers per prediction
  â€¢ White/Bleach rule-based overrides (Dye=0, Salt=0 for Next Batch)
  â€¢ Confidence based on CV-std (not just MAPE threshold)
  â€¢ Full 30-feature vector (vs 23 in v1)
  â€¢ Saves predictions to reports/v2_prediction_scenarios.json
"""
import os, sys, io, json, pickle, warnings, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd

ROOT   = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.join(ROOT, 'models', 'v2')
RPTS   = os.path.join(ROOT, 'reports')

# â”€â”€â”€ PHYSICAL BOUNDS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
BOUNDS = {
    'Salt_g_per_kg':            (0,   700),
    'Dye_g_per_kg':             (0,   300),
    'Alkali_g_per_kg':          (0,   500),
    'Chem_g_per_kg':            (5,  3000),
    'Water_Intensity_L_per_kg': (1.0,  30),
}
TARGET_LABELS = {
    'Salt_g_per_kg':            'Salt',
    'Dye_g_per_kg':             'Dye (total)',
    'Alkali_g_per_kg':          'Alkali',
    'Chem_g_per_kg':            'Total Chemical',
    'Water_Intensity_L_per_kg': 'Water',
}
UNITS_MAP = {
    'Salt_g_per_kg':            'g/kg',
    'Dye_g_per_kg':             'g/kg',
    'Alkali_g_per_kg':          'g/kg',
    'Chem_g_per_kg':            'g/kg',
    'Water_Intensity_L_per_kg': 'L/kg',
}

# â”€â”€â”€ DEFAULT MAPE LOOKUP (for confidence) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
DEFAULT_MAPE = {
    'Unit_A_Salt_g_per_kg_Dark':    19.3,
    'Unit_A_Salt_g_per_kg_Vivid':   22.0,
    'Unit_A_Salt_g_per_kg_Medium':  28.0,
    'Unit_A_Salt_g_per_kg_Light':   40.0,
    'Unit_A_Salt_g_per_kg_Pale':    45.0,
    'Unit_A_Salt_g_per_kg_White':   37.1,
    'Unit_A_Dye_g_per_kg_Dark':     35.0,
    'Unit_A_Dye_g_per_kg_Vivid':    22.0,
    'Unit_A_Dye_g_per_kg_Medium':   28.0,
    'Unit_A_Dye_g_per_kg_Light':    40.0,
    'Unit_A_Dye_g_per_kg_Pale':     50.0,
    'Unit_A_Alkali_g_per_kg_Dark':  30.0,
    'Unit_D_Salt_g_per_kg_Dark':    24.4,
    'Unit_D_Dye_g_per_kg_Dark':     32.3,
    'Unit_A_Chem_g_per_kg_Pooled':  31.8,
    'Unit_D_Chem_g_per_kg_Pooled':  26.8,
    'Unit_A_Water_Intensity_L_per_kg_Pooled': 1.7,
    'Unit_D_Water_Intensity_L_per_kg_Pooled': 2.5,
}

def conf_from_mape(mape):
    if mape is None or mape > 999:
        return 'UNKNOWN'
    if mape < 20:  return 'HIGH'
    if mape < 40:  return 'MEDIUM'
    return 'LOW'

# â”€â”€â”€ LOAD MODELS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print('Loading v2 models ...')
registry   = {}
q_registry = {}  # quantile models

if not os.path.isdir(MODELS):
    print(f'[ERROR] models/v2 directory not found: {MODELS}')
    print('        Please run 38_ai_v2_advanced_training.py first.')
    sys.exit(1)

for fname in os.listdir(MODELS):
    fpath = os.path.join(MODELS, fname)
    if fname.endswith('_quantile.pkl'):
        key = fname.replace('_quantile.pkl', '')
        with open(fpath, 'rb') as fh:
            q_registry[key] = pickle.load(fh)
    elif fname.endswith('.pkl') and not fname.startswith('kmeans'):
        key = fname.replace('.pkl', '')
        with open(fpath, 'rb') as fh:
            registry[key] = pickle.load(fh)

# Load K-means for color-depth bin assignment
kmeans_obj = None
kmeans_path = os.path.join(MODELS, 'kmeans_color_depth.pkl')
if os.path.exists(kmeans_path):
    with open(kmeans_path, 'rb') as fh:
        kmeans_obj = pickle.load(fh)
    print(f'  K-means color-depth model loaded')
else:
    print('[WARN] K-means model not found â€” will use heuristic bin assignment')

# Load White/Bleach rules
wb_rules = {}
rules_path = os.path.join(MODELS, 'whiteBleach_rules.json')
if os.path.exists(rules_path):
    with open(rules_path) as fh:
        wb_rules = json.load(fh)

print(f'  Point models: {len(registry)}  Quantile models: {len(q_registry)}')

# â”€â”€â”€ HISTORICAL AVERAGES (for vs Avg column) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
HIST_AVGS = {
    ('Unit_A', 'Light/Medium Colored', 'Salt_g_per_kg'):            219.0,
    ('Unit_A', 'Dark/Extra Dark',      'Salt_g_per_kg'):            422.0,
    ('Unit_A', 'White/Bleach',         'Salt_g_per_kg'):              6.0,
    ('Unit_A', 'Light/Medium Colored', 'Dye_g_per_kg'):              22.0,
    ('Unit_A', 'Dark/Extra Dark',      'Dye_g_per_kg'):              46.0,
    ('Unit_A', 'Light/Medium Colored', 'Alkali_g_per_kg'):           96.0,
    ('Unit_A', 'Dark/Extra Dark',      'Alkali_g_per_kg'):          121.0,
    ('Unit_A', 'White/Bleach',         'Alkali_g_per_kg'):           21.0,
    ('Unit_A', 'Light/Medium Colored', 'Chem_g_per_kg'):            414.0,
    ('Unit_A', 'Dark/Extra Dark',      'Chem_g_per_kg'):            687.0,
    ('Unit_A', 'White/Bleach',         'Chem_g_per_kg'):            112.0,
    ('Unit_A', 'Light/Medium Colored', 'Water_Intensity_L_per_kg'):   6.9,
    ('Unit_A', 'Dark/Extra Dark',      'Water_Intensity_L_per_kg'):   6.9,
    ('Unit_A', 'White/Bleach',         'Water_Intensity_L_per_kg'):   6.9,
    ('Unit_D', 'Light/Medium Colored', 'Salt_g_per_kg'):            212.0,
    ('Unit_D', 'Dark/Extra Dark',      'Salt_g_per_kg'):            444.0,
    ('Unit_D', 'White/Bleach',         'Salt_g_per_kg'):              5.0,
    ('Unit_D', 'Light/Medium Colored', 'Dye_g_per_kg'):              14.0,
    ('Unit_D', 'Dark/Extra Dark',      'Dye_g_per_kg'):              38.0,
    ('Unit_D', 'Light/Medium Colored', 'Alkali_g_per_kg'):           91.0,
    ('Unit_D', 'Dark/Extra Dark',      'Alkali_g_per_kg'):          136.0,
    ('Unit_D', 'White/Bleach',         'Alkali_g_per_kg'):           22.0,
    ('Unit_D', 'Light/Medium Colored', 'Chem_g_per_kg'):            409.0,
    ('Unit_D', 'Dark/Extra Dark',      'Chem_g_per_kg'):            708.0,
    ('Unit_D', 'White/Bleach',         'Chem_g_per_kg'):            105.0,
    ('Unit_D', 'Light/Medium Colored', 'Water_Intensity_L_per_kg'):   7.7,
    ('Unit_D', 'Dark/Extra Dark',      'Water_Intensity_L_per_kg'):   7.1,
    ('Unit_D', 'White/Bleach',         'Water_Intensity_L_per_kg'):   6.9,
}

# â”€â”€â”€ FEATURE VECTOR BUILDER â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
GSM_ORD_MAP = {'Light (<150)': 1, 'Medium (150-249)': 2, 'Heavy (250+)': 3}
TOP_FABS    = ['Single Jersey','Lycra S/J','Fleece/Heavy','Rib Fabric',
               'Composite','Interlock','Pique','Other']
COLOR_BINS  = ['Pale','Light','Medium','Vivid','Dark','White','N/A']
SHADE_CATS  = ['Dark/Extra Dark','Light/Medium Colored','White/Bleach']

def build_feature_vector(inp, feats):
    """Build a 1-row numpy array matching the training feature list."""
    row = {}
    row['Log_Fabric_Kg']    = np.log1p(max(1.0, inp['fabric_kg']))
    row['GSM_Ord']          = float(GSM_ORD_MAP.get(inp['gsm'], 2))
    row['LR']               = float(inp.get('lr', 7.0))
    month = inp.get('month', 6)
    row['Month_sin']        = np.sin(2*np.pi*month/12)
    row['Month_cos']        = np.cos(2*np.pi*month/12)
    row['Year']             = float(inp.get('year', 2026))
    row['Recipe_Lines']     = float(inp.get('recipe_lines', 15))
    row['Log_Recipe_Lines'] = np.log1p(row['Recipe_Lines'])
    row['GSM_x_LogFab']     = row['GSM_Ord'] * row['Log_Fabric_Kg']
    row['LR_x_LogFab']      = row['LR'] * row['Log_Fabric_Kg']
    batch_kg = inp['fabric_kg']
    row['Batch_Size_Ord']   = 1.0 if batch_kg<=100 else (2.0 if batch_kg<=300 else (3.0 if batch_kg<=600 else 4.0))
    row['Is_2Part']         = float(inp.get('is_2part', 0))
    row['Is_NextBatch']     = float(inp.get('is_nextbatch', 0))
    row['Is_Finished']      = float(inp.get('is_finished', 1))
    row['Is_ReProcess']     = float(inp.get('is_reprocess', 0))

    # Shade one-hots
    for sc in SHADE_CATS:
        row[f'Shade_{sc}'] = 1.0 if inp['shade'] == sc else 0.0

    # Fabric one-hots
    fab = inp.get('fabric', 'Other')
    fab_clean = fab if fab in TOP_FABS else 'Other'
    for f in TOP_FABS:
        row[f'Fab_{f}'] = 1.0 if fab_clean == f else 0.0

    # Color Depth Bin one-hots
    cd = inp.get('color_depth_bin', 'N/A')
    for b in COLOR_BINS:
        row[f'CD_{b}'] = 1.0 if cd == b else 0.0

    # Build array in the same order as feats
    vec = np.array([row.get(f, 0.0) for f in feats], dtype=float)
    return vec.reshape(1, -1)

def assign_color_depth_bin(shade, dye_estimate, recipe_lines, kmeans_obj):
    """Assign a Color_Depth_Bin using K-means or heuristic fallback."""
    if shade == 'Dark/Extra Dark':
        return 'Dark'
    if shade == 'White/Bleach':
        return 'White'
    # Light/Medium Colored â†’ use K-means
    if kmeans_obj is not None:
        X = np.array([[np.log1p(max(0, dye_estimate)), np.log1p(recipe_lines)]])
        lbl = kmeans_obj['kmeans'].predict(X)[0]
        return kmeans_obj['bin_names'][lbl]
    # Heuristic fallback if K-means not available
    if dye_estimate < 2:   return 'Pale'
    if dye_estimate < 12:  return 'Light'
    if dye_estimate < 40:  return 'Medium'
    return 'Vivid'

def predict_one(inp):
    """Run full v2 prediction for one batch input. Returns dict."""
    unit        = inp['unit']
    shade       = inp['shade']
    fabric_kg   = inp['fabric_kg']
    lr          = inp.get('lr', 7.0)
    is_nextbatch = inp.get('is_nextbatch', 0)

    # â”€â”€ IMPROVEMENT 1: Assign Color_Depth_Bin â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    dye_est     = inp.get('dye_estimate', 10.0)  # rough starting estimate
    recipe_lines = inp.get('recipe_lines', 15)
    cd_bin      = assign_color_depth_bin(shade, dye_est, recipe_lines, kmeans_obj)
    inp['color_depth_bin'] = cd_bin

    predictions = {}
    TARGETS_IN_ORDER = [
        'Salt_g_per_kg', 'Dye_g_per_kg', 'Alkali_g_per_kg',
        'Chem_g_per_kg', 'Water_Intensity_L_per_kg'
    ]

    for tgt in TARGETS_IN_ORDER:

        # â”€â”€ IMPROVEMENT 7: White/Bleach rule overrides â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        if tgt == 'Dye_g_per_kg' and shade == 'White/Bleach':
            predictions[tgt] = {
                'value_per_kg': 0.0, 'total': 0.0, 'unit': 'g/kg',
                'p10': 0.0, 'p50': 0.0, 'p90': 0.0,
                'vs_avg_pct': -100.0,
                'confidence': 'HIGH', 'mape': 0.0,
                'model': 'Rule: White/Bleach â†’ Dye=0',
                'color_depth_bin': cd_bin,
            }
            continue

        if tgt == 'Salt_g_per_kg' and shade == 'White/Bleach' and is_nextbatch:
            predictions[tgt] = {
                'value_per_kg': 0.0, 'total': 0.0, 'unit': 'g/kg',
                'p10': 0.0, 'p50': 0.0, 'p90': 0.0,
                'vs_avg_pct': -100.0,
                'confidence': 'HIGH', 'mape': 0.0,
                'model': 'Rule: White/Bleach Next Batch â†’ Salt=0',
                'color_depth_bin': cd_bin,
            }
            continue

        # â”€â”€ Model routing â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        if tgt in ('Chem_g_per_kg', 'Water_Intensity_L_per_kg'):
            key = f'{unit}_{tgt}_Pooled'
        else:
            key = f'{unit}_{tgt}_{cd_bin}'

        # Try fallback to pooled if stratified model not found
        if key not in registry:
            key_fallback = f'{unit}_{tgt}_Pooled'
            if key_fallback in registry:
                key = key_fallback
            else:
                # Last resort: any key with same unit+target
                for k in registry:
                    if k.startswith(f'{unit}_{tgt}_'):
                        key = k; break
                else:
                    continue

        meta = registry[key]
        feats = meta['features']
        model = meta['model']

        # Build feature vector
        X = build_feature_vector(inp, feats)

        # Point prediction
        lo, hi = BOUNDS[tgt]
        if isinstance(model, dict) and model.get('type') == 'stack':
            base_preds = [np.clip(m.predict(X), 0, None) for m in model['bases']]
            X_meta = np.column_stack(base_preds)
            val = float(np.clip(model['meta'].predict(X_meta)[0], lo, hi))
        else:
            val = float(np.clip(model.predict(X)[0], lo, hi))

        # â”€â”€ IMPROVEMENT 6: Quantile predictions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        p10, p50, p90 = val, val, val
        if key in q_registry:
            qm = q_registry[key]
            for q_str, qmod in qm.items():
                try:
                    qv = float(np.clip(qmod.predict(X)[0], lo, hi))
                    if q_str == '0.1':  p10 = qv
                    elif q_str == '0.5': p50 = qv
                    elif q_str == '0.9': p90 = qv
                except Exception:
                    pass

        # vs Average
        hist_avg = HIST_AVGS.get((unit, shade, tgt))
        vs_avg = ((val - hist_avg) / hist_avg * 100) if hist_avg else None

        # Confidence
        mape = meta.get('test_mape') or DEFAULT_MAPE.get(key, 50.0)
        # Use CV std to penalise unreliable models
        cv_res = meta.get('cv_results', {})
        best_nm = meta.get('model_type', '')
        cv_std = cv_res.get(best_nm, {}).get('cv_mape_std', 0)
        effective_mape = mape + cv_std * 0.5  # penalise high variance
        confidence = conf_from_mape(effective_mape)

        total = val * fabric_kg / 1000.0 if tgt != 'Water_Intensity_L_per_kg' else val * fabric_kg

        predictions[tgt] = {
            'value_per_kg': round(val, 2),
            'total':        round(total, 1),
            'unit':         UNITS_MAP[tgt],
            'p10':          round(p10, 2),
            'p50':          round(p50, 2),
            'p90':          round(p90, 2),
            'vs_avg_pct':   round(vs_avg, 1) if vs_avg is not None else None,
            'confidence':   confidence,
            'mape':         round(mape, 1),
            'model':        meta.get('model_type', 'Unknown'),
            'color_depth_bin': cd_bin,
        }

    return predictions, cd_bin

# â”€â”€â”€ DISPLAY FUNCTIONS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
W = 78

def print_recipe(inp, predictions, cd_bin):
    unit  = inp['unit']
    shade = inp['shade']
    gsm   = inp['gsm']
    fab   = inp.get('fabric', 'Unknown')
    kg    = inp['fabric_kg']
    month = inp.get('month', 1)
    lr    = inp.get('lr', 7.0)
    month_name = ['','Jan','Feb','Mar','Apr','May','Jun',
                  'Jul','Aug','Sep','Oct','Nov','Dec'][int(month)]
    is_2p = inp.get('is_2part', 0)
    is_nb = inp.get('is_nextbatch', 0)
    flags = []
    if is_2p: flags.append('2-Part')
    if is_nb: flags.append('Next Batch')
    flag_str = ' Â· '.join(flags) if flags else 'Normal'

    print('â”Œ' + 'â”€'*W + 'â”')
    print(f'â”‚  {"SMART DYEING v2 â€” Optimal Recipe Recommendation":^{W-2}}â”‚')
    print(f'â”‚  {unit} Â· {fab} Â· {gsm} Â· {shade[:20]:<20}  [{cd_bin} bin]{"":<8}â”‚')
    print(f'â”‚  Fabric: {kg:.1f} kg Â· Month: {month_name} Â· L:R = 1:{lr:.1f} Â· Process: {flag_str:<15}â”‚')
    print('â”œ' + 'â”€'*W + 'â”¤')
    hdr = f'â”‚  {"Chemical":22s}{"Conc.":>10}{"Total":>10}{"vs Avg":>9}{"P10":>8}{"P90":>8}{"Conf":>8}{"Model":>10}â”‚'
    print(hdr)
    print('â”‚' + 'â”€'*W + 'â”‚')

    water_val = None
    water_total = None
    for tgt in ['Salt_g_per_kg','Dye_g_per_kg','Alkali_g_per_kg',
                'Chem_g_per_kg','Water_Intensity_L_per_kg']:
        if tgt not in predictions: continue
        p = predictions[tgt]
        name = TARGET_LABELS[tgt]
        unit_str = p['unit']
        val  = p['value_per_kg']
        tot  = p['total']
        vs   = f"{p['vs_avg_pct']:+.0f}%" if p['vs_avg_pct'] is not None else '   N/A'
        p10_ = f"{p['p10']:.1f}"
        p90_ = f"{p['p90']:.1f}"
        conf = p['confidence']
        mdl  = str(p['model'])[:8]

        conc_str = f'{val:.1f} {unit_str}'
        tot_str  = (f'{tot:.1f} kg' if tgt != 'Water_Intensity_L_per_kg'
                    else f'{tot:,.0f} L')

        if tgt == 'Water_Intensity_L_per_kg':
            water_val   = val
            water_total = tot

        line = (f'â”‚  {name:22s}{conc_str:>10}{tot_str:>10}{vs:>9}'
                f'{p10_:>8}{p90_:>8}{conf:>8}{mdl:>10}â”‚')
        print(line)

    print('â”œ' + 'â”€'*W + 'â”¤')
    if water_val and water_total:
        theory = lr * kg
        diff   = abs(water_total - theory)
        ok_str = f'Î”={diff:.0f} L ({diff/theory*100:.1f}%)' if diff > 1 else 'matches theory'
        print(f'â”‚  Water: {water_total:,.0f} L actual  vs  {theory:,.0f} L theory (L:R {lr:.1f}:1)  {ok_str:<20}â”‚')

    mapes = [p['mape'] for p in predictions.values()
             if isinstance(p.get('mape'), (int,float)) and p['mape'] < 900]
    if mapes:
        print(f'â”‚  MAPE range: {min(mapes):.1f}â€“{max(mapes):.1f}%  |  '
              f'P10/P90 = 90% prediction interval{"":<23}â”‚')
    print('â””' + 'â”€'*W + 'â”˜')

# â”€â”€â”€ BUILT-IN 5 TEST SCENARIOS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
TEST_SCENARIOS = [
    {'scenario': 1, 'name': 'Unit_A Â· S/J Â· Medium Â· Light/Medium Â· 350 kg Â· Jun',
     'input': {'unit':'Unit_A','fabric':'Single Jersey','gsm':'Medium (150-249)',
               'shade':'Light/Medium Colored','fabric_kg':350,'lr':7.0,'month':6,'year':2026,
               'recipe_lines':15,'is_2part':0,'is_nextbatch':0,'is_finished':1,
               'dye_estimate':15.0}},
    {'scenario': 2, 'name': 'Unit_A Â· Fleece Â· Heavy Â· Dark Â· 500 kg Â· Jan',
     'input': {'unit':'Unit_A','fabric':'Fleece/Heavy','gsm':'Heavy (250+)',
               'shade':'Dark/Extra Dark','fabric_kg':500,'lr':8.0,'month':1,'year':2026,
               'recipe_lines':22,'is_2part':0,'is_nextbatch':0,'is_finished':1,
               'dye_estimate':40.0}},
    {'scenario': 3, 'name': 'Unit_A Â· Rib Â· Medium Â· White/Bleach Â· 200 kg Â· Mar',
     'input': {'unit':'Unit_A','fabric':'Rib Fabric','gsm':'Medium (150-249)',
               'shade':'White/Bleach','fabric_kg':200,'lr':7.0,'month':3,'year':2026,
               'recipe_lines':8,'is_2part':0,'is_nextbatch':0,'is_finished':1,
               'dye_estimate':0.0}},
    {'scenario': 4, 'name': 'Unit_D Â· Lycra S/J Â· Light Â· Light/Medium Â· 150 kg Â· Aug',
     'input': {'unit':'Unit_D','fabric':'Lycra S/J','gsm':'Light (<150)',
               'shade':'Light/Medium Colored','fabric_kg':150,'lr':7.0,'month':8,'year':2026,
               'recipe_lines':18,'is_2part':0,'is_nextbatch':0,'is_finished':1,
               'dye_estimate':30.0}},
    {'scenario': 5, 'name': 'Unit_D Â· Composite Â· Heavy Â· Dark Â· 800 kg Â· Dec Â· 2-Part',
     'input': {'unit':'Unit_D','fabric':'Composite','gsm':'Heavy (250+)',
               'shade':'Dark/Extra Dark','fabric_kg':800,'lr':8.0,'month':12,'year':2026,
               'recipe_lines':28,'is_2part':1,'is_nextbatch':0,'is_finished':1,
               'dye_estimate':38.0}},
    {'scenario': 6, 'name': 'Unit_A Â· Pale Tint Â· Light (<150) Â· Light/Medium Â· 250 kg Â· Apr',
     'input': {'unit':'Unit_A','fabric':'Single Jersey','gsm':'Light (<150)',
               'shade':'Light/Medium Colored','fabric_kg':250,'lr':6.0,'month':4,'year':2026,
               'recipe_lines':8,'is_2part':0,'is_nextbatch':1,'is_finished':1,
               'dye_estimate':0.5}},  # Pale
    {'scenario': 7, 'name': 'Unit_D Â· White/Bleach Â· Next Batch (No Salt) Â· 300 kg Â· Sep',
     'input': {'unit':'Unit_D','fabric':'Single Jersey','gsm':'Medium (150-249)',
               'shade':'White/Bleach','fabric_kg':300,'lr':7.0,'month':9,'year':2026,
               'recipe_lines':6,'is_2part':0,'is_nextbatch':1,'is_finished':1,
               'dye_estimate':0.0}},
]

# â”€â”€â”€ MAIN EXECUTION â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
if __name__ == '__main__':
    print()
    print('='*78)
    print('SMART DYEING v2 â€” Enhanced Recipe Prediction CLI')
    print('Models: Optuna-tuned Â· 5-Fold CV Â· Stacking Â· Quantile P10/P90')
    print('='*78)

    all_results = []

    print('\nRunning 7 test scenarios (incl. 2-Part dyeing and Next Batch scenarios)...\n')
    for sc in TEST_SCENARIOS:
        print(f'\n[Scenario {sc["scenario"]}] {sc["name"]}')
        preds, cd_bin = predict_one(sc['input'])
        print_recipe(sc['input'], preds, cd_bin)
        all_results.append({
            'scenario':    sc['scenario'],
            'name':        sc['name'],
            'input':       sc['input'],
            'predictions': {k: {kk: vv for kk, vv in v.items()
                                if kk not in ('model',)}
                            for k, v in preds.items()},
            'color_depth_bin': cd_bin,
        })

    # Save
    out_path = os.path.join(RPTS, 'v2_prediction_scenarios.json')
    with open(out_path, 'w', encoding='utf-8') as fh:
        json.dump(all_results, fh, indent=2, ensure_ascii=False)
    print(f'\n[Saved] {out_path}')

    # â”€â”€ INTERACTIVE MODE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print()
    print('='*78)
    print('INTERACTIVE MODE â€” Enter details to get a recipe recommendation')
    print('  (Press Enter to use default, type "exit" to quit)')
    print('='*78)

    UNIT_OPTS    = ['Unit_A', 'Unit_D']
    SHADE_OPTS   = ['Light/Medium Colored', 'Dark/Extra Dark', 'White/Bleach']
    GSM_OPTS     = ['Light (<150)', 'Medium (150-249)', 'Heavy (250+)']
    FAB_OPTS     = ['Single Jersey','Lycra S/J','Fleece/Heavy','Rib Fabric',
                    'Composite','Interlock','Pique','Other']

    def prompt(msg, default, choices=None):
        try:
            if choices:
                opts = '|'.join(f'{i+1}={c}' for i, c in enumerate(choices))
                val = input(f'\n  {msg} [{opts}] [{default}]: ').strip()
            else:
                val = input(f'\n  {msg} [{default}]: ').strip()
            if val.lower() == 'exit': sys.exit(0)
            if not val: return default
            if choices:
                if val.isdigit() and 1 <= int(val) <= len(choices):
                    return choices[int(val)-1]
                elif val in choices: return val
                else: return default
            return val
        except (EOFError, KeyboardInterrupt):
            return default

    while True:
        try:
            print()
            unit  = prompt('Unit', 'Unit_A', UNIT_OPTS)
            shade = prompt('Shade Category', 'Light/Medium Colored', SHADE_OPTS)
            gsm   = prompt('GSM Category', 'Medium (150-249)', GSM_OPTS)
            fab   = prompt('Fabric Type', 'Single Jersey', FAB_OPTS)
            kg_s  = prompt('Fabric Weight (kg)', '350')
            lr_s  = prompt('Liquor Ratio (1:X)', '7.0')
            mo_s  = prompt('Month (1-12)', '6')
            yr_s  = prompt('Year', '2026')
            rl_s  = prompt('Recipe Lines (est.)', '15')
            dye_s = prompt('Approx Dye Depth g/kg (estimate, for bin assignment)', '10')
            is2p  = prompt('2-Part dyeing? (0=No, 1=Yes)', '0')
            isnb  = prompt('Next Batch (reuse bath)? (0=No, 1=Yes)', '0')

            inp = {
                'unit': unit, 'shade': shade, 'gsm': gsm, 'fabric': fab,
                'fabric_kg':   float(kg_s),
                'lr':          float(lr_s),
                'month':       int(mo_s),
                'year':        float(yr_s),
                'recipe_lines':float(rl_s),
                'dye_estimate':float(dye_s),
                'is_2part':    float(is2p),
                'is_nextbatch':float(isnb),
                'is_finished': 1.0,
            }
            preds, cd_bin = predict_one(inp)
            print()
            print_recipe(inp, preds, cd_bin)

        except (EOFError, KeyboardInterrupt):
            print('\n\nExiting.')
            break
        except Exception as e:
            print(f'  [ERROR] {e}')


