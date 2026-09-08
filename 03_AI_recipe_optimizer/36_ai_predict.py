"""
36_ai_predict.py  (v2 â€” stratified model routing)
====================================================
SMART DYEING â€” AI Recipe Recommendation CLI

Routing logic:
  Salt, Dye, Alkali  â†’ look up stratum-specific model (Unit_Target_ShadeLabel)
                        first; fall back to pooled model if stratum not trained.
  Total Chem, Water  â†’ pooled model only (shade-independent, low MAPE).

Usage:
  py -3.12 36_ai_predict.py         (runs 5 built-in scenarios + interactive mode)
"""

import os, sys, io, json, pickle, math, warnings
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
warnings.filterwarnings('ignore')
import numpy as np

ROOT   = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.join(ROOT, 'models')
RPTS   = os.path.join(ROOT, 'reports')
os.makedirs(RPTS, exist_ok=True)

# â”€â”€â”€ PHYSICAL BOUNDS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
BOUNDS = {
    'Salt_g_per_kg':            (0, 700),
    'Dye_g_per_kg':             (0, 300),
    'Alkali_g_per_kg':          (0, 500),
    'Chem_g_per_kg':            (5, 3000),
    'Water_Intensity_L_per_kg': (1.0, 30.0),
}

# â”€â”€â”€ OPERATOR AVERAGES (from V2 findings) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
OPERATOR_AVG = {
    'Unit_A': {'Salt_g_per_kg':316.0,'Dye_g_per_kg':32.0,'Alkali_g_per_kg':95.0,
            'Chem_g_per_kg':490.0,'Water_Intensity_L_per_kg':7.1},
    'Unit_D': {'Salt_g_per_kg':297.0,'Dye_g_per_kg':21.0,'Alkali_g_per_kg':80.0,
            'Chem_g_per_kg':430.0,'Water_Intensity_L_per_kg':7.8},
}

# â”€â”€â”€ SHADE LABEL MAP â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
SHADE_LABEL = {
    'Light/Medium Colored': 'Light',
    'Dark/Extra Dark':       'Dark',
    'White/Bleach':          'White',
}

# â”€â”€â”€ LOAD ALL MODELS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def load_all_models():
    """Load all .pkl files. Build two lookup dicts:
       pooled[unit_target]         â€” pooled (Water, Chem)
       stratified[unit_target_lbl] â€” shade-stratified (Salt, Dye, Alkali)
    """
    pooled     = {}
    stratified = {}

    if not os.path.exists(MODELS):
        raise FileNotFoundError(f'Models dir not found: {MODELS}\nRun 35_ai_train_pipeline.py first.')

    for fname in sorted(os.listdir(MODELS)):
        if not fname.endswith('.pkl'):
            continue
        path = os.path.join(MODELS, fname)
        with open(path, 'rb') as fh:
            meta = pickle.load(fh)

        unit = meta['unit']
        tgt  = meta['target']

        if 'shade_label' in meta:
            # Stratified model
            shade_lbl = meta['shade_label']
            key = f'{unit}_{tgt}_{shade_lbl}'
            if key not in stratified or meta['mape'] < stratified[key]['mape']:
                stratified[key] = meta
        else:
            # Pooled model
            key = f'{unit}_{tgt}'
            if key not in pooled or meta['mape'] < pooled[key]['mape']:
                pooled[key] = meta

    print(f'[Predict] Loaded {len(pooled)} pooled + {len(stratified)} stratified models')
    return pooled, stratified


# â”€â”€â”€ FEATURE BUILDER â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
GSM_ORD = {'Light (<150)': 1, 'Medium (150-249)': 2, 'Heavy (250+)': 3}
SHADE_CATS  = ['Dark/Extra Dark', 'Light/Medium Colored', 'White/Bleach']
FABRIC_CATS = ['Composite', 'Fleece/Heavy', 'Interlock', 'Lycra S/J',
               'Other', 'Pique', 'Rib Fabric', 'Single Jersey']
DTYPE_CATS  = ['DType_Finished', 'DType_Normal &a', 'DType_Normal ||',
               'DType_Re-proce', 'DType_Washdown']

def build_features(spec, feature_names):
    row = {}
    row['Log_Fabric_Kg']  = math.log1p(max(float(spec.get('fabric_kg', 350)), 1))
    row['GSM_Ord']        = float(GSM_ORD.get(spec.get('gsm_cat', 'Medium (150-249)'), 2))
    row['LR']             = float(spec.get('liquor_ratio', 7.0))
    month = int(spec.get('month', 6))
    row['Month_sin']      = math.sin(2 * math.pi * month / 12)
    row['Month_cos']      = math.cos(2 * math.pi * month / 12)
    row['Year']           = float(spec.get('year', 2025))
    row['Recipe_Lines']   = float(spec.get('recipe_lines', 18))
    row['GSM_x_LogFab']   = row['GSM_Ord'] * row['Log_Fabric_Kg']
    shade = spec.get('shade', 'Light/Medium Colored')
    for s in SHADE_CATS:
        row['Shade_' + s] = 1.0 if s == shade else 0.0
    fab = spec.get('fabric_type', 'Single Jersey')
    if fab not in FABRIC_CATS: fab = 'Other'
    for fc in FABRIC_CATS:
        row['Fab_' + fc] = 1.0 if fc == fab else 0.0
    dtype_raw = spec.get('dyeing_type', 'Normal')
    for dc in DTYPE_CATS:
        row[dc] = 1.0 if dc.lower().startswith(('dtype_' + dtype_raw[:6]).lower()) else 0.0
    return np.array([row.get(f, 0.0) for f in feature_names]).reshape(1, -1)


# â”€â”€â”€ CORE PREDICT â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
TARGET_ORDER = ['Salt_g_per_kg','Dye_g_per_kg','Alkali_g_per_kg',
                'Chem_g_per_kg','Water_Intensity_L_per_kg']

# Which targets have stratified models
STRATIFIED_TARGETS = {'Salt_g_per_kg', 'Dye_g_per_kg', 'Alkali_g_per_kg'}

def predict_recipe(spec, pooled, stratified):
    unit      = spec.get('unit', 'Unit_A')
    fab_kg    = float(spec.get('fabric_kg', 350))
    shade     = spec.get('shade', 'Light/Medium Colored')
    shade_lbl = SHADE_LABEL.get(shade, 'Light')
    results   = {}

    for tgt in TARGET_ORDER:
        meta = None
        model_source = None

        if tgt in STRATIFIED_TARGETS:
            # Try stratified first
            strat_key = f'{unit}_{tgt}_{shade_lbl}'
            if strat_key in stratified:
                meta = stratified[strat_key]
                model_source = f'Stratified/{shade_lbl}'
        if meta is None:
            # Fall back to pooled
            pool_key = f'{unit}_{tgt}'
            if pool_key in pooled:
                meta = pooled[pool_key]
                model_source = 'Pooled'
        if meta is None:
            continue

        feats  = meta['features']
        X      = build_features(spec, feats)
        raw    = float(meta['model'].predict(X)[0])
        lo, hi = BOUNDS.get(tgt, (0, 9999))
        pred   = max(lo, min(hi, raw))
        clamped = pred != raw

        mape = meta['mape']
        conf = 'HIGH' if mape < 20 else ('MEDIUM' if mape < 40 else 'LOW')

        # Totals
        if 'Water' in tgt:
            total_val  = round(pred * fab_kg, 1)
            total_unit = 'L'
            unit_str   = 'L/kg'
        else:
            total_val  = round(pred * fab_kg / 1000, 2)
            total_unit = 'kg'
            unit_str   = 'g/kg'

        results[tgt] = {
            'value_per_kg': round(pred, 2),
            'total_val':    total_val,
            'unit_str':     unit_str,
            'total_unit':   total_unit,
            'model_type':   meta['model_type'],
            'model_source': model_source,
            'mape':         round(mape, 1),
            'confidence':   conf,
            'clamped':      clamped,
        }

    return results


# â”€â”€â”€ FORMATTED OUTPUT â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
TARGET_LABELS = {
    'Salt_g_per_kg':            'Salt          ',
    'Dye_g_per_kg':             'Dye (total)   ',
    'Alkali_g_per_kg':          'Alkali        ',
    'Chem_g_per_kg':            'Total Chemical',
    'Water_Intensity_L_per_kg': 'Water         ',
}
MONTH_NAMES = ['','Jan','Feb','Mar','Apr','May','Jun',
               'Jul','Aug','Sep','Oct','Nov','Dec']

def print_recommendation(spec, results):
    unit      = spec.get('unit','Unit_A')
    fab       = spec.get('fabric_type','?')
    gsm       = spec.get('gsm_cat','?')
    shade     = spec.get('shade','?')
    fab_kg    = spec.get('fabric_kg',350)
    month     = int(spec.get('month',6))
    lr        = spec.get('liquor_ratio',7.0)
    op_avg    = OPERATOR_AVG.get(unit, {})
    month_str = MONTH_NAMES[month] if 1 <= month <= 12 else str(month)
    W = 68

    print()
    print('â”Œ' + 'â”€'*W + 'â”')
    print(f'â”‚  SMART DYEING â€” Optimal Recipe Recommendation{" "*(W-46)}â”‚')
    hdr = f'  {unit} Â· {fab} Â· {gsm[:12]} Â· {shade[:22]}'
    print(f'â”‚{hdr}{" "*(W-len(hdr))}â”‚')
    sub = f'  Fabric: {fab_kg} kg Â· Month: {month_str} Â· L:R = 1:{lr}'
    print(f'â”‚{sub}{" "*(W-len(sub))}â”‚')
    print('â”œ' + 'â”€'*W + 'â”¤')
    hdr2 = f'  {"Chemical":<18} {"Conc.":>10}  {"Total":>10}  {"vs Avg":>8}  {"Conf":>6}  {"Model":>12}'
    print(f'â”‚{hdr2}{" "*(W-len(hdr2))}â”‚')
    print('â”‚' + 'â”€'*W + 'â”‚')

    for tgt in TARGET_ORDER:
        if tgt not in results: continue
        r   = results[tgt]
        lbl = TARGET_LABELS.get(tgt, tgt[:14])
        val = f'{r["value_per_kg"]:.1f} {r["unit_str"]}'
        tot = f'{r["total_val"]:.1f} {r["total_unit"]}'
        op  = op_avg.get(tgt)
        diff_str = f'{(r["value_per_kg"]-op)/op*100:+.0f}%' if op and op > 0 else '  n/a'
        conf     = r['confidence']
        mtype    = r['model_type'][:8]
        clamp    = 'âš ' if r['clamped'] else ' '
        line = f'  {lbl:<18} {val:>10}  {tot:>10}  {diff_str:>8}  {conf:>6}  {mtype:>12} {clamp}'
        print(f'â”‚{line}{" "*(W-len(line))}â”‚')

    print('â”œ' + 'â”€'*W + 'â”¤')
    if 'Water_Intensity_L_per_kg' in results:
        wi    = results['Water_Intensity_L_per_kg']['value_per_kg']
        w_tot = wi * float(fab_kg)
        lr_theory = float(fab_kg) * float(lr)
        note = f'  Water: {w_tot:,.0f} L actual vs {lr_theory:,.0f} L theory (L:R {lr}:1)'
        print(f'â”‚{note}{" "*(W-len(note))}â”‚')
    foot = f'  MAPE range: {min(r["mape"] for r in results.values()):.1f}â€“{max(r["mape"] for r in results.values()):.1f}%'
    print(f'â”‚{foot}{" "*(W-len(foot))}â”‚')
    print('â””' + 'â”€'*W + 'â”˜')


# â”€â”€â”€ TEST SCENARIOS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
TEST_SPECS = [
    {'name': 'Unit_A Â· Single Jersey Â· Medium Â· Light/Medium Â· 350 kg Â· Jun',
     'unit':'Unit_A','fabric_type':'Single Jersey','gsm_cat':'Medium (150-249)',
     'shade':'Light/Medium Colored','fabric_kg':350.0,'liquor_ratio':7.0,'month':6,'year':2025},
    {'name': 'Unit_A Â· Fleece/Heavy Â· Heavy Â· Dark Â· 500 kg Â· Jan',
     'unit':'Unit_A','fabric_type':'Fleece/Heavy','gsm_cat':'Heavy (250+)',
     'shade':'Dark/Extra Dark','fabric_kg':500.0,'liquor_ratio':8.0,'month':1,'year':2025},
    {'name': 'Unit_A Â· Rib Fabric Â· Medium Â· White/Bleach Â· 200 kg Â· Mar',
     'unit':'Unit_A','fabric_type':'Rib Fabric','gsm_cat':'Medium (150-249)',
     'shade':'White/Bleach','fabric_kg':200.0,'liquor_ratio':7.0,'month':3,'year':2025},
    {'name': 'Unit_D Â· Lycra S/J Â· Light Â· Light/Medium Â· 150 kg Â· Aug',
     'unit':'Unit_D','fabric_type':'Lycra S/J','gsm_cat':'Light (<150)',
     'shade':'Light/Medium Colored','fabric_kg':150.0,'liquor_ratio':7.0,'month':8,'year':2025},
    {'name': 'Unit_D Â· Composite Â· Heavy Â· Dark Â· 800 kg Â· Dec',
     'unit':'Unit_D','fabric_type':'Composite','gsm_cat':'Heavy (250+)',
     'shade':'Dark/Extra Dark','fabric_kg':800.0,'liquor_ratio':8.0,'month':12,'year':2025},
]


# â”€â”€â”€ MAIN â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
if __name__ == '__main__':
    print('=' * 70)
    print('SMART DYEING â€” AI Recipe Prediction System  (v2 Â· Stratified Models)')
    print('=' * 70)

    try:
        pooled, stratified = load_all_models()
    except FileNotFoundError as e:
        print(f'ERROR: {e}')
        sys.exit(1)

    print(f'\nPooled models ({len(pooled)}):')
    for k,m in sorted(pooled.items()):
        print(f'  {k:45s}  MAPE={m["mape"]:5.1f}%  [{m["model_type"]}]')
    print(f'\nStratified models ({len(stratified)}):')
    for k,m in sorted(stratified.items()):
        print(f'  {k:50s}  MAPE={m["mape"]:5.1f}%  [{m["model_type"]}]')

    print()
    print('=' * 70)
    print('RUNNING 5 STANDARD TEST SCENARIOS')
    print('=' * 70)

    scenario_outputs = []
    for i, spec in enumerate(TEST_SPECS, 1):
        print(f'\n[Scenario {i}] {spec["name"]}')
        results = predict_recipe(spec, pooled, stratified)
        print_recommendation(spec, results)
        scenario_outputs.append({
            'scenario': i,
            'name': spec['name'],
            'input': {k:v for k,v in spec.items() if k != 'name'},
            'predictions': {
                tgt: {kk:vv for kk,vv in r.items() if kk != 'model'}
                for tgt, r in results.items()
            }
        })

    # Save JSON output
    out_path = os.path.join(RPTS, 'prediction_scenarios.json')
    with open(out_path, 'w', encoding='utf-8') as fh:
        json.dump(scenario_outputs, fh, indent=2, ensure_ascii=False)
    print(f'\n[Saved] {out_path}')
    print()
    print('=' * 70)
    print('INTERACTIVE MODE â€” Type "exit" to quit, Enter = use default')
    print('=' * 70)

    UNITS_LIST  = ['Unit_A', 'Unit_D']
    FABRIC_LIST = ['Single Jersey','Rib Fabric','Composite','Lycra S/J',
                   'Fleece/Heavy','Interlock','Pique','Other']
    GSM_LIST    = ['Light (<150)','Medium (150-249)','Heavy (250+)']
    SHADE_LIST  = ['Light/Medium Colored','Dark/Extra Dark','White/Bleach']

    def ask(prompt, default, choices=None):
        val = input(f'  {prompt} [{default}]: ').strip()
        if not val: return default
        if val.lower() == 'exit': sys.exit(0)
        if choices:
            if val in choices: return val
            if val.isdigit() and 1 <= int(val) <= len(choices):
                return choices[int(val)-1]
            print(f'    Options: {", ".join(f"{i+1}={c}" for i,c in enumerate(choices))}')
            return default
        try: return type(default)(val)
        except: return val

    while True:
        print()
        unit   = ask(f'Unit {[f"{i+1}={u}" for i,u in enumerate(UNITS_LIST)]}', 'Unit_A', UNITS_LIST)
        fabric = ask(f'Fabric {[f"{i+1}={f[:8]}" for i,f in enumerate(FABRIC_LIST)]}', 'Single Jersey', FABRIC_LIST)
        gsm    = ask(f'GSM {[f"{i+1}={g[:6]}" for i,g in enumerate(GSM_LIST)]}', 'Medium (150-249)', GSM_LIST)
        shade  = ask(f'Shade {[f"{i+1}={s[:5]}" for i,s in enumerate(SHADE_LIST)]}', 'Light/Medium Colored', SHADE_LIST)
        fab_kg = ask('Fabric weight (kg)', 350.0)
        lr     = ask('Liquor ratio (e.g. 7)', 7.0)
        month  = ask('Month (1-12)', 6)
        year   = ask('Year', 2025)

        spec = {'unit':unit,'fabric_type':fabric,'gsm_cat':gsm,'shade':shade,
                'fabric_kg':float(fab_kg),'liquor_ratio':float(lr),
                'month':int(month),'year':int(year)}
        results = predict_recipe(spec, pooled, stratified)
        print_recommendation(spec, results)

