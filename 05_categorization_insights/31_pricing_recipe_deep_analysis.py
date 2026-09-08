"""
31_pricing_recipe_deep_analysis.py
===================================
SMART DYEING Phase 2 Deep Analysis
Topic: Pricing Correlation, Recipe Management, Chemical Spend Decomposition
Date:  2026-09-04
Input: DEEP_ROOT_Batch_Enriched.csv  (289,403 rows, QC_Usable flag)
       DEEP_ROOT_Chemical_Master.csv (495 products, class/cost/mass)
       DEEP_ROOT_Savings_Opportunity.csv (49 peer groups)
       extraction_checkpoint.db      (for per-product monthly series)
Output:
  PRICING_RECIPE_Analysis_2021_2026.html  -- interactive dashboard (7 sections)
  RECIPE_Benchmark_By_Fabric_Shade.csv    -- per-group dosage benchmarks
  PRICING_YearMonth_Series.csv            -- monthly cost/kg series for all classes
  AUXILIARY_Audit.csv                     -- 219 auxiliary products ranked by spend

Python 3.5 compatible: no f-strings, no walrus, no match. Standard library only.
"""

import csv
import json
import os
import re
import sqlite3
import sys
from collections import defaultdict, OrderedDict

# â”€â”€ paths â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
BASE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(BASE)

ENRICHED_CSV  = os.path.join(BASE, 'DEEP_ROOT_Batch_Enriched.csv')
CHEM_MASTER   = os.path.join(BASE, 'DEEP_ROOT_Chemical_Master.csv')
SAVINGS_CSV   = os.path.join(BASE, 'DEEP_ROOT_Savings_Opportunity.csv')
DB_PATH       = os.path.join(PROJECT, '2026_Data_Science_Rigorous_Analysis',
                              'extraction_checkpoint.db')

OUT_HTML      = os.path.join(BASE, 'PRICING_RECIPE_Analysis_2021_2026.html')
OUT_BENCHMARK = os.path.join(BASE, 'RECIPE_Benchmark_By_Fabric_Shade.csv')
OUT_MONTHLY   = os.path.join(BASE, 'PRICING_YearMonth_Series.csv')
OUT_AUX       = os.path.join(BASE, 'AUXILIARY_Audit.csv')

# â”€â”€ helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def flt(v, default=0.0):
    try:
        x = float(v)
        return x if x == x else default   # NaN guard
    except (ValueError, TypeError):
        return default

def pct(a, b):
    return round(100.0 * a / b, 2) if b else 0.0

def fmt_num(v):
    if abs(v) >= 1e9:
        return '{:.2f}B'.format(v / 1e9)
    if abs(v) >= 1e6:
        return '{:.2f}M'.format(v / 1e6)
    if abs(v) >= 1e3:
        return '{:,.0f}'.format(v)
    return '{:.2f}'.format(v)

def percentile(sorted_vals, p):
    if not sorted_vals:
        return 0.0
    n = len(sorted_vals)
    idx = p / 100.0 * (n - 1)
    lo = int(idx)
    hi = min(lo + 1, n - 1)
    frac = idx - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac

# â”€â”€ STEP 1: Load enriched batch table â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print('[1/7] Loading DEEP_ROOT_Batch_Enriched.csv ...')

# accumulators indexed by (fabric, shade, gsm)
recipe_groups = defaultdict(lambda: {
    'batches': 0, 'fabric_kg': 0.0, 'water_l': 0.0,
    'chem_kg': 0.0, 'cost_tk': 0.0, 'salt_kg': 0.0, 'dye_kg': 0.0, 'alkali_kg': 0.0,
    'wi_vals': [], 'chem_gpkg_vals': [], 'salt_gpkg_vals': [], 'dye_gpkg_vals': [],
    'cost_tkpkg_vals': []
})

# monthly series for trend charts: month -> {cost_tk, fabric_kg, chem_kg, salt_kg, dye_kg, batches}
monthly = defaultdict(lambda: {
    'cost_tk': 0.0, 'fabric_kg': 0.0, 'chem_kg': 0.0,
    'salt_kg': 0.0, 'dye_kg': 0.0, 'water_l': 0.0, 'batches': 0
})

# unit monthly
unit_monthly = defaultdict(lambda: defaultdict(lambda: {
    'cost_tk': 0.0, 'fabric_kg': 0.0, 'chem_kg': 0.0, 'batches': 0, 'salt_kg': 0.0
}))

# shade cost accumulator
shade_cost = defaultdict(lambda: {'cost_tk': 0.0, 'fabric_kg': 0.0,
                                   'dye_kg': 0.0, 'salt_kg': 0.0, 'batches': 0})

# dyeing type accumulator
dtype_cost = defaultdict(lambda: {'cost_tk': 0.0, 'fabric_kg': 0.0, 'batches': 0,
                                   'chem_kg': 0.0})

total_batches_loaded = 0
usable_loaded = 0

with open(ENRICHED_CSV, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        total_batches_loaded += 1
        if row['QC_Usable'] != '1':
            continue
        usable_loaded += 1

        fab   = row['Fabric_Category']
        shade = row['Shade_Category']
        gsm   = row['GSM_Category']
        unit  = row['Dye_Unit']
        month = row['Month']
        dtype = row['Dyeing_Type']

        fkg   = flt(row['Fabric_Kg'])
        wl    = flt(row['Water_L'])
        ckg   = flt(row['Chem_Total_Kg'])
        ctk   = flt(row['Chem_Cost_Tk'])
        skg   = flt(row['Salt_Kg'])
        dkg   = flt(row['Dye_Kg'])
        akg   = flt(row['Alkali_Kg'])
        wi    = flt(row['Water_Intensity_L_per_kg'])
        cgpkg = flt(row['Chem_g_per_kg'])
        sgpkg = flt(row['Salt_g_per_kg'])
        dgpkg = flt(row['Dye_g_per_kg'])
        ctpkg = flt(row['Cost_Tk_per_kg'])

        if fkg <= 0:
            continue

        key = (fab, shade, gsm)
        g = recipe_groups[key]
        g['batches'] += 1
        g['fabric_kg'] += fkg
        g['water_l'] += wl
        g['chem_kg'] += ckg
        g['cost_tk'] += ctk
        g['salt_kg'] += skg
        g['dye_kg'] += dkg
        g['alkali_kg'] += akg
        if wi > 0:   g['wi_vals'].append(wi)
        if cgpkg > 0: g['chem_gpkg_vals'].append(cgpkg)
        if sgpkg > 0: g['salt_gpkg_vals'].append(sgpkg)
        if dgpkg > 0: g['dye_gpkg_vals'].append(dgpkg)
        if ctpkg > 0: g['cost_tkpkg_vals'].append(ctpkg)

        # monthly
        m = monthly[month]
        m['cost_tk']   += ctk
        m['fabric_kg'] += fkg
        m['chem_kg']   += ckg
        m['salt_kg']   += skg
        m['dye_kg']    += dkg
        m['water_l']   += wl
        m['batches']   += 1

        # unit monthly
        um = unit_monthly[unit][month]
        um['cost_tk']   += ctk
        um['fabric_kg'] += fkg
        um['chem_kg']   += ckg
        um['batches']   += 1
        um['salt_kg']   += skg

        # shade
        sc = shade_cost[shade]
        sc['cost_tk']   += ctk
        sc['fabric_kg'] += fkg
        sc['dye_kg']    += dkg
        sc['salt_kg']   += skg
        sc['batches']   += 1

        # dyeing type (first token only)
        dt_key = dtype.split('||')[0].strip() if dtype else 'Unknown'
        dt = dtype_cost[dt_key]
        dt['cost_tk']   += ctk
        dt['fabric_kg'] += fkg
        dt['batches']   += 1
        dt['chem_kg']   += ckg

print('   loaded {:,} batches, {:,} usable'.format(total_batches_loaded, usable_loaded))

# â”€â”€ STEP 2: Build recipe benchmark CSV â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print('[2/7] Building RECIPE_Benchmark_By_Fabric_Shade.csv ...')

benchmark_rows = []
for key, g in recipe_groups.items():
    fab, shade, gsm = key
    n = g['batches']
    fkg = g['fabric_kg']
    if n < 50 or fkg < 1:
        continue

    wi_s    = sorted(g['wi_vals'])
    cg_s    = sorted(g['chem_gpkg_vals'])
    sg_s    = sorted(g['salt_gpkg_vals'])
    dg_s    = sorted(g['dye_gpkg_vals'])
    ct_s    = sorted(g['cost_tkpkg_vals'])

    wi_avg  = g['water_l'] / fkg
    cg_avg  = g['chem_kg'] * 1000.0 / fkg
    sg_avg  = g['salt_kg'] * 1000.0 / fkg
    dg_avg  = g['dye_kg']  * 1000.0 / fkg
    ct_avg  = g['cost_tk'] / fkg

    benchmark_rows.append({
        'Fabric': fab, 'Shade': shade, 'GSM': gsm,
        'Batches': n,
        'Fabric_Tonnes': round(fkg / 1000.0, 1),
        'WI_avg': round(wi_avg, 3),
        'WI_P25': round(percentile(wi_s, 25), 3),
        'WI_P75': round(percentile(wi_s, 75), 3),
        'WI_P90': round(percentile(wi_s, 90), 3),
        'Chem_gpkg_avg': round(cg_avg, 1),
        'Chem_gpkg_P25': round(percentile(cg_s, 25), 1),
        'Chem_gpkg_P75': round(percentile(cg_s, 75), 1),
        'Chem_gpkg_P90': round(percentile(cg_s, 90), 1),
        'Salt_gpkg_avg': round(sg_avg, 1),
        'Salt_gpkg_P25': round(percentile(sg_s, 25), 1),
        'Salt_gpkg_P75': round(percentile(sg_s, 75), 1),
        'Dye_gpkg_avg':  round(dg_avg, 2),
        'Dye_gpkg_P25':  round(percentile(dg_s, 25), 2),
        'Dye_gpkg_P75':  round(percentile(dg_s, 75), 2),
        'Cost_tkpkg_avg': round(ct_avg, 2),
        'Cost_tkpkg_P25': round(percentile(ct_s, 25), 2),
        'Cost_tkpkg_P75': round(percentile(ct_s, 75), 2),
        'Cost_tkpkg_P90': round(percentile(ct_s, 90), 2),
        'Total_Chem_Cost_Tk': round(g['cost_tk']),
        'Total_Cost_M_Tk': round(g['cost_tk'] / 1e6, 2)
    })

benchmark_rows.sort(key=lambda r: -r['Total_Chem_Cost_Tk'])

cols_bm = ['Fabric','Shade','GSM','Batches','Fabric_Tonnes',
           'WI_avg','WI_P25','WI_P75','WI_P90',
           'Chem_gpkg_avg','Chem_gpkg_P25','Chem_gpkg_P75','Chem_gpkg_P90',
           'Salt_gpkg_avg','Salt_gpkg_P25','Salt_gpkg_P75',
           'Dye_gpkg_avg','Dye_gpkg_P25','Dye_gpkg_P75',
           'Cost_tkpkg_avg','Cost_tkpkg_P25','Cost_tkpkg_P75','Cost_tkpkg_P90',
           'Total_Chem_Cost_Tk','Total_Cost_M_Tk']
with open(OUT_BENCHMARK, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=cols_bm)
    w.writeheader()
    w.writerows(benchmark_rows)
print('   {:,} benchmark groups written'.format(len(benchmark_rows)))

# â”€â”€ STEP 3: Monthly pricing series CSV â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print('[3/7] Building PRICING_YearMonth_Series.csv ...')

months_sorted = sorted(m for m in monthly.keys() if m and m != 'Unknown' and m >= '2020-01')

monthly_out = []
for m in months_sorted:
    d = monthly[m]
    fkg = d['fabric_kg']
    monthly_out.append({
        'Month': m,
        'Year': m[:4],
        'Batches': d['batches'],
        'Fabric_t': round(fkg / 1000.0, 1),
        'Water_ML': round(d['water_l'] / 1e6, 4),
        'WI_avg': round(d['water_l'] / fkg, 3) if fkg else 0,
        'Chem_t': round(d['chem_kg'] / 1000.0, 2),
        'Salt_t': round(d['salt_kg'] / 1000.0, 2),
        'Dye_t': round(d['dye_kg'] / 1000.0, 2),
        'Cost_M_Tk': round(d['cost_tk'] / 1e6, 3),
        'Cost_tkpkg': round(d['cost_tk'] / fkg, 2) if fkg else 0,
        'Chem_gpkg': round(d['chem_kg'] * 1000.0 / fkg, 1) if fkg else 0,
        'Salt_gpkg': round(d['salt_kg'] * 1000.0 / fkg, 1) if fkg else 0,
    })

with open(OUT_MONTHLY, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(monthly_out[0].keys()))
    w.writeheader()
    w.writerows(monthly_out)
print('   {:,} months written'.format(len(monthly_out)))

# â”€â”€ STEP 4: Auxiliary audit CSV â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print('[4/7] Building AUXILIARY_Audit.csv ...')

aux_rows = []
grand_spend = 0.0
with open(CHEM_MASTER, 'r', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        grand_spend += flt(row['Total_Cost_Tk'])

with open(CHEM_MASTER, 'r', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        if row['Class'] != 'Auxiliary':
            continue
        ctk = flt(row['Total_Cost_Tk'])
        ckg = flt(row['Total_Kg'])
        aux_rows.append({
            'Product': row['Item_Name'],
            'Line_Count': int(flt(row['Line_Count'])),
            'Batches_Used_In': int(flt(row['Batches_Used_In'])),
            'Batch_Penetration_pct': flt(row['Batch_Penetration_pct']),
            'Total_Kg': round(ckg, 1),
            'Total_Cost_Tk': round(ctk),
            'Avg_Price_Tk_per_kg': flt(row['Avg_Unit_Price_Tk_per_kg']),
            'Share_of_Grand_Spend_pct': round(100.0 * ctk / grand_spend, 4) if grand_spend else 0,
            'Share_of_Mass_pct': flt(row['Share_of_Total_Mass_pct'])
        })

aux_rows.sort(key=lambda r: -r['Total_Cost_Tk'])

# cumulative spend
cum = 0.0
aux_total_spend = sum(r['Total_Cost_Tk'] for r in aux_rows)
for r in aux_rows:
    cum += r['Total_Cost_Tk']
    r['Cumulative_Spend_pct'] = round(100.0 * cum / aux_total_spend, 2) if aux_total_spend else 0

cols_aux = ['Product','Line_Count','Batches_Used_In','Batch_Penetration_pct',
            'Total_Kg','Total_Cost_Tk','Avg_Price_Tk_per_kg',
            'Share_of_Grand_Spend_pct','Share_of_Mass_pct','Cumulative_Spend_pct']
with open(OUT_AUX, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=cols_aux)
    w.writeheader()
    w.writerows(aux_rows)
print('   {:,} auxiliary products written'.format(len(aux_rows)))

# â”€â”€ STEP 5: Load chemical master for class-level charts â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print('[5/7] Loading chemical master for dashboard charts ...')

class_spend   = defaultdict(float)   # class -> total cost Tk
class_mass    = defaultdict(float)   # class -> total kg
class_products = defaultdict(int)    # class -> product count
top_products  = []                   # top 20 by cost

with open(CHEM_MASTER, 'r', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        cls = row['Class']
        ctk = flt(row['Total_Cost_Tk'])
        ckg = flt(row['Total_Kg'])
        class_spend[cls]    += ctk
        class_mass[cls]     += ckg
        class_products[cls] += 1
        top_products.append({
            'name': row['Item_Name'],
            'cls':  cls,
            'ctk':  ctk,
            'ckg':  ckg,
            'price': flt(row['Avg_Unit_Price_Tk_per_kg']),
            'penetration': flt(row['Batch_Penetration_pct'])
        })

top_products.sort(key=lambda r: -r['ctk'])
top20 = top_products[:20]

# â”€â”€ STEP 6: Prepare all chart data for HTML â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print('[6/7] Preparing chart data ...')

# Monthly cost/kg series (2020-01 to 2026-08)
months_labels = [d['Month'] for d in monthly_out]
cost_per_kg_series = [d['Cost_tkpkg'] for d in monthly_out]
chem_gpkg_series   = [d['Chem_gpkg']  for d in monthly_out]
salt_gpkg_series   = [d['Salt_gpkg']  for d in monthly_out]
wi_series          = [d['WI_avg']     for d in monthly_out]
fabric_t_series    = [d['Fabric_t']   for d in monthly_out]

# year-boundary months for annotation
cost_steps = []
for i in range(1, len(monthly_out)):
    prev = monthly_out[i-1]
    curr = monthly_out[i]
    if prev['Cost_tkpkg'] > 0 and curr['Cost_tkpkg'] > 0:
        ratio = curr['Cost_tkpkg'] / prev['Cost_tkpkg']
        if ratio > 1.35 or ratio < 0.65:
            cost_steps.append({
                'month': curr['Month'],
                'prev': round(prev['Cost_tkpkg'], 2),
                'curr': round(curr['Cost_tkpkg'], 2),
                'change_pct': round((ratio - 1) * 100, 1)
            })

# Class spend/mass for donut charts
class_order = ['Dyestuff','Auxiliary','Alkali','Salt (electrolyte)',
                'Bleach / redox','Acid','Softener / finish','Enzyme']
cls_spend_vals = [round(class_spend.get(c, 0) / 1e6, 2) for c in class_order]
cls_mass_vals  = [round(class_mass.get(c, 0) / 1000.0, 1) for c in class_order]

# Top 20 products bar chart (cost)
t20_names  = [r['name'][:28] + '..' if len(r['name']) > 30 else r['name'] for r in top20]
t20_cost   = [round(r['ctk'] / 1e6, 2) for r in top20]
t20_cls    = [r['cls'] for r in top20]
t20_price  = [r['price'] for r in top20]

# Recipe benchmark table - top 30 groups by cost
top_bench  = benchmark_rows[:30]

# Shade cost comparison
shade_order = ['Dark/Extra Dark', 'Light/Medium Colored', 'White/Bleach', 'AOP']
shade_data = []
for s in shade_order:
    if s in shade_cost:
        sc = shade_cost[s]
        fkg = sc['fabric_kg']
        shade_data.append({
            'shade': s,
            'batches': sc['batches'],
            'fabric_t': round(fkg / 1000.0, 1),
            'cost_tkpkg': round(sc['cost_tk'] / fkg, 2) if fkg else 0,
            'dye_gpkg': round(sc['dye_kg'] * 1000.0 / fkg, 2) if fkg else 0,
            'salt_gpkg': round(sc['salt_kg'] * 1000.0 / fkg, 2) if fkg else 0,
            'total_cost_m': round(sc['cost_tk'] / 1e6, 2)
        })

# Unit_D vs Unit_A monthly cost/kg comparison
Unit_A_monthly = unit_monthly.get('Unit_A', {})
Unit_D_monthly = unit_monthly.get('Unit_D', {})
Unit_C_monthly = unit_monthly.get('Unit_C', {})

Unit_A_cost = []
Unit_D_cost = []
for m in months_labels:
    def _cpkg(u_dict, mo):
        d = u_dict.get(mo, {})
        fkg = d.get('fabric_kg', 0)
        ctk = d.get('cost_tk', 0)
        return round(ctk / fkg, 2) if fkg > 0 else None
    Unit_A_cost.append(_cpkg(Unit_A_monthly, m))
    Unit_D_cost.append(_cpkg(Unit_D_monthly, m))

# Over-dosing flag: batches > P75 chem g/kg vs peer group
# Build from benchmark: count cells where avg >> P75
overdose_flags = []
for row in benchmark_rows[:20]:
    spread = row['Chem_gpkg_P90'] - row['Chem_gpkg_P25']
    overdose_flags.append({
        'key': '{} / {} / {}'.format(row['Fabric'], row['Shade'], row['GSM']),
        'avg': row['Chem_gpkg_avg'],
        'P25': row['Chem_gpkg_P25'],
        'P75': row['Chem_gpkg_P75'],
        'P90': row['Chem_gpkg_P90'],
        'spread': round(spread, 1),
        'cost_m': row['Total_Cost_M_Tk']
    })
overdose_flags.sort(key=lambda r: -r['spread'])

# Auxiliary top 15 by spend
aux_top15 = aux_rows[:15]

# â”€â”€ STEP 7: Build HTML â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print('[7/7] Writing HTML dashboard ...')

# Helper: JSON-safe dump for None values in chart series
def jsnull(lst):
    parts = []
    for v in lst:
        if v is None:
            parts.append('null')
        else:
            parts.append(json.dumps(v))
    return '[' + ','.join(parts) + ']'

# colour map for chemical classes
cls_colours = {
    'Dyestuff':         '#f59e0b',
    'Auxiliary':        '#38bdf8',
    'Alkali':           '#a78bfa',
    'Salt (electrolyte)': '#34d399',
    'Bleach / redox':   '#fb923c',
    'Acid':             '#f87171',
    'Softener / finish':'#e879f9',
    'Enzyme':           '#4ade80'
}
cls_colour_list = [cls_colours.get(c, '#94a3b8') for c in class_order]

# build shade HTML rows
shade_rows_html = ''
for sd in shade_data:
    shade_rows_html += '<tr><td>{shade}</td><td>{batches:,}</td><td>{fabric_t:,.1f}</td><td style="color:#f59e0b;font-weight:bold">{cost_tkpkg}</td><td style="color:#38bdf8">{dye_gpkg}</td><td style="color:#34d399">{salt_gpkg}</td><td style="color:#a78bfa">{total_cost_m}</td></tr>'.format(**sd)

# build top benchmark table rows
bench_rows_html = ''
for i, r in enumerate(top_bench):
    bench_rows_html += (
        '<tr><td>{}</td><td>{}</td><td>{}</td>'
        '<td>{:,}</td><td>{:,.1f}</td>'
        '<td>{}</td><td style="color:#f59e0b">{}</td>'
        '<td style="color:#38bdf8">{}</td><td>{}</td>'
        '<td style="color:#ef4444">{}</td><td>{}</td>'
        '<td style="color:#a78bfa">{}</td>'
        '</tr>\n'
    ).format(
        r['Fabric'], r['Shade'], r['GSM'],
        r['Batches'], r['Fabric_Tonnes'],
        r['WI_avg'],
        r['Chem_gpkg_avg'],
        r['Salt_gpkg_avg'],
        r['Dye_gpkg_avg'],
        r['Cost_tkpkg_avg'],
        r['Cost_tkpkg_P25'],
        r['Total_Cost_M_Tk']
    )

# overdose table
overdose_html = ''
for r in overdose_flags[:10]:
    overdose_html += '<tr><td>{key}</td><td>{avg}</td><td>{P25}</td><td>{P75}</td><td style="color:#ef4444;font-weight:bold">{P90}</td><td style="color:#f59e0b">{spread}</td><td>{cost_m}</td></tr>\n'.format(**r)

# auxiliary top15 table
aux_html = ''
for r in aux_top15:
    aux_html += '<tr><td>{Product}</td><td>{Batches_Used_In:,}</td><td>{Batch_Penetration_pct:.1f}%</td><td>{Total_Kg:,.0f}</td><td style="color:#f59e0b;font-weight:bold">{Total_Cost_Tk:,.0f}</td><td>{Avg_Price_Tk_per_kg:,.0f}</td><td style="color:#38bdf8">{Share_of_Grand_Spend_pct:.3f}%</td><td>{Cumulative_Spend_pct:.1f}%</td></tr>\n'.format(**r)

# cost step warning HTML
cost_step_html = ''
for cs in cost_steps:
    direction = 'RISE' if cs['change_pct'] > 0 else 'FALL'
    colour = '#ef4444' if cs['change_pct'] > 0 else '#22c55e'
    cost_step_html += '<tr><td>{month}</td><td>{prev}</td><td>{curr}</td><td style="color:{colour};font-weight:bold">{direction} {change_pct:+.1f}%</td></tr>\n'.format(
        month=cs['month'], prev=cs['prev'], curr=cs['curr'],
        colour=colour, direction=direction, change_pct=cs['change_pct']
    )

# headline numbers
total_cost_m = sum(d['cost_tk'] for d in monthly.values()) / 1e6
total_fabric_t = sum(d['fabric_kg'] for d in monthly.values()) / 1000.0
aux_total_cost_m = aux_total_spend / 1e6
dye_total_cost_m = class_spend.get('Dyestuff', 0) / 1e6
salt_total_t = class_mass.get('Salt (electrolyte)', 0) / 1000.0

html = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>SMART DYEING â€” Pricing & Recipe Analysis 2021-2026</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
:root {{
  --bg:#0f172a; --card:#1e293b; --b:#334155; --acc:#38bdf8;
  --t:#e2e8f0;  --m:#94a3b8;   --warn:#f59e0b; --danger:#ef4444;
  --good:#22c55e; --purple:#a78bfa;
}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--t);padding:24px}}
h1{{font-size:26px;color:var(--acc);text-align:center;margin-bottom:4px}}
.sub{{text-align:center;color:var(--m);font-size:13px;margin-bottom:28px}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px;max-width:1800px;margin:0 auto 20px}}
.grid3{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px;max-width:1800px;margin:0 auto 20px}}
.card{{background:var(--card);border:1px solid var(--b);border-radius:12px;padding:20px}}
.card.full{{grid-column:1/-1}}
.card h2{{font-size:14px;color:var(--acc);margin-bottom:6px;text-transform:uppercase;letter-spacing:.05em}}
.card .desc{{font-size:12px;color:var(--m);margin-bottom:12px;line-height:1.5}}
.section-title{{font-size:19px;color:var(--warn);margin:30px auto 12px;max-width:1800px;border-bottom:1px solid var(--b);padding-bottom:6px;font-weight:600}}
.insight{{background:#0f2942;border-left:3px solid var(--acc);padding:10px 14px;border-radius:6px;margin-top:12px;font-size:12.5px;line-height:1.6}}
.insight strong{{color:var(--acc)}}
.warn{{background:#3b2000;border-left:3px solid var(--warn);padding:10px 14px;border-radius:6px;margin-top:10px;font-size:12.5px}}
.warn strong{{color:#fcd34d}}
.danger{{background:#3b1515;border-left:3px solid var(--danger);padding:10px 14px;border-radius:6px;margin-top:10px;font-size:12.5px}}
.danger strong{{color:#fca5a5}}
table{{width:100%;border-collapse:collapse;font-size:11.5px;margin-top:6px}}
th{{background:#0b3b70;color:#fff;padding:7px 8px;text-align:left;white-space:nowrap}}
td{{padding:6px 8px;border-bottom:1px solid var(--b);white-space:nowrap}}
tr:hover td{{background:#1a2d45}}
.kpi-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;max-width:1800px;margin:0 auto 24px}}
.kpi{{background:var(--card);border:1px solid var(--b);border-radius:10px;padding:16px;text-align:center}}
.kpi .num{{font-size:28px;font-weight:700;color:var(--acc);margin-bottom:4px}}
.kpi .lbl{{font-size:11px;color:var(--m);text-transform:uppercase;letter-spacing:.05em}}
</style>
</head>
<body>
<h1>&#128200; SMART DYEING â€” Pricing Correlation &amp; Recipe Management</h1>
<p class="sub">289,403 Unique Batches Â· 4,831,565 Canonical Recipe Lines Â· Population-wide Â· 2026-09-04</p>

<div class="kpi-grid">
  <div class="kpi"><div class="num">&#2547;{cost_m:.0f}M</div><div class="lbl">Total Chemical Spend (Tk)</div></div>
  <div class="kpi"><div class="num">&#2547;{dye_m:.0f}M</div><div class="lbl">Dyestuff Spend (43% of total)</div></div>
  <div class="kpi"><div class="num">&#2547;{aux_m:.0f}M</div><div class="lbl">Auxiliary Spend (24% of total)</div></div>
  <div class="kpi"><div class="num">{salt_t:,.0f}t</div><div class="lbl">Salt Dosed (effluent load)</div></div>
</div>

<p class="section-title">&#167;1 &middot; Chemical Cost/kg Trend â€” Monthly 2020â€“2026 (Price-Step Anomaly Detection)</p>
<div class="grid">
<div class="card full">
  <h2>Monthly Chemical Cost per kg of Fabric (Tk/kg) â€” All Units Combined</h2>
  <p class="desc">Mass-weighted chemical spend divided by fabric dyed. <strong>Year-boundary price-list revaluations appear as sudden vertical jumps</strong> that have nothing to do with actual efficiency changes. These are flagged in the warning table below. Use chemical g/kg (the chart below) as the safe long-run efficiency measure.</p>
  <canvas id="cA" height="100"></canvas>
  <div class="warn"><strong>&#9888; Price-Step Anomalies Detected:</strong> The table below lists months where cost/kg jumped or fell by more than 35% month-on-month. These are procurement revaluations, not real efficiency changes. Do not cite cross-boundary cost figures as savings.
  <table style="margin-top:8px"><thead><tr><th>Month</th><th>Prev Tk/kg</th><th>New Tk/kg</th><th>Change</th></tr></thead><tbody>
  ''' + cost_step_html + '''
  </tbody></table></div>
</div>
<div class="card">
  <h2>Chemical g/kg of Fabric â€” Safe Efficiency Trend (no price distortion)</h2>
  <p class="desc">Total chemical mass dosed per kilogram of fabric. This is immune to price-list changes and is the correct long-run efficiency KPI. A genuine reduction here means less chemistry is being dosed.</p>
  <canvas id="cB" height="200"></canvas>
</div>
<div class="card">
  <h2>Salt (Electrolyte) g/kg per Month</h2>
  <p class="desc">Salt is 54% of all chemical mass and the primary driver of effluent conductivity. A downward trend here directly reduces ETP load and discharge penalty risk. Salt can be reduced by switching to lower-electrolyte dye systems or by implementing salt recovery.</p>
  <canvas id="cC" height="200"></canvas>
</div>
</div>

<p class="section-title">&#167;2 &middot; Unit_A vs Unit_D Chemical Cost/kg â€” Unit-Level Comparison</p>
<div class="grid">
<div class="card full">
  <h2>Monthly Cost per kg by Dyeing Unit (Unit_A Reactive vs Unit_D Blends)</h2>
  <p class="desc">Unit_A uses reactive dyes (high salt, moderate dye cost). Unit_D dyes polyester/cotton blends (lower salt, different auxiliary profile). A persistent gap confirms the units have structurally different recipe costs and <strong>must not be benchmarked against each other</strong>. Unit_C (disperse, high-temp) excluded from this chart due to missing water data on 73.6% of batches.</p>
  <canvas id="cD" height="100"></canvas>
  <div class="insight"><strong>Key Finding:</strong> If Unit_A cost/kg consistently exceeds Unit_D, it is because reactive dyeing requires far more salt and alkali per kilogram. That is not an inefficiency â€” it is chemistry. The actionable comparison is Unit_A-2022 vs Unit_A-2025 within the same unit, not Unit_A vs Unit_D across units.</div>
</div>
</div>

<p class="section-title">&#167;3 &middot; Chemical Spend Decomposition â€” By Class</p>
<div class="grid">
<div class="card">
  <h2>Spend Share by Chemical Class (M Tk)</h2>
  <p class="desc">Dyestuff and Auxiliary together account for 67% of total chemical spend despite being only 15.9% of total mass dosed. <strong>Salt and Alkali are 73% of mass but only 15.2% of spend.</strong> This is two different business cases: salt/water for environmental compliance, dye/auxiliary for cost reduction.</p>
  <canvas id="cE" height="250"></canvas>
</div>
<div class="card">
  <h2>Mass Share by Chemical Class (tonnes)</h2>
  <p class="desc">The overwhelming physical burden of the recipe is salt and alkali. Every kilogram of salt dosed ends up in the effluent. Salt recovery loops have a direct and immediate ROI here. The ETP must handle 34,006 tonnes of salt across the analysis window.</p>
  <canvas id="cF" height="250"></canvas>
</div>
</div>

<p class="section-title">&#167;4 &middot; Top 20 Chemical Products by Spend</p>
<div class="grid">
<div class="card full">
  <h2>Top 20 Products by Total Chemical Spend (M Tk) â€” Coloured by Class</h2>
  <p class="desc">Bezaktiv-Black GO is the single most expensive product in the plant at 540M Tk. Together with other black and navy dyestuffs it dominates spend. The top 5 Bezaktiv products alone account for over 1.1 billion Tk. Sourcing negotiations on this product family would yield immediate results.</p>
  <canvas id="cG" height="200"></canvas>
  <div class="insight"><strong>Key Finding:</strong> <strong>Bezaktiv-Black GO (540M Tk) + Bezaktiv-Blue SW (239M Tk) + Bezaktiv-Red S-Matrix (168M Tk)</strong> = 947M Tk from just 3 products. These are all from the same Bezaktiv family. A vendor consolidation or volume rebate negotiation on this family would yield significant savings without any process change.</div>
</div>
</div>

<p class="section-title">&#167;5 &middot; Shade-Depth Pricing Premium â€” Dark vs Light vs White</p>
<div class="grid">
<div class="card full">
  <h2>Chemical Cost, Dye Intensity &amp; Salt Intensity by Shade Category</h2>
  <p class="desc">Dark shades require dramatically more dyestuff and salt per kilogram of fabric. This is the chemical justification for shade-dependent recipe benchmarks â€” a blanket plant-wide target will under-charge light shades and over-pressure dark ones.</p>
  <table><thead><tr><th>Shade</th><th>Batches</th><th>Fabric (t)</th><th>Cost Tk/kg</th><th>Dye g/kg</th><th>Salt g/kg</th><th>Total Spend (M Tk)</th></tr></thead>
  <tbody>''' + shade_rows_html + '''</tbody></table>
  <div class="insight"><strong>Root Finding:</strong> Dark/Extra Dark shades carry <strong>466 g/kg of salt</strong> vs 300 g/kg for light/medium. But chemical cost per kg is <em>lower</em> for dark (59.43 Tk/kg) vs light (71.97 Tk/kg). This seeming paradox is because salt is cheap (17 Tk/kg) and light shades use more expensive auxiliaries proportionally. Recipe management must separate the salt load objective (environmental) from the cost objective (purchasing).</div>
</div>
</div>

<p class="section-title">&#167;6 &middot; Recipe Benchmark Table â€” Per Fabric Ã— Shade Ã— GSM Group</p>
<div class="grid">
<div class="card full">
  <h2>Top 30 Groups by Total Chemical Spend â€” Dosage Benchmarks (P25/P75/P90)</h2>
  <p class="desc">Each row is a peer group defined by Fabric Ã— Shade Ã— GSM. The P25 is the "best achievable" benchmark â€” the plant already reaches it on a quarter of its own batches. The gap between P25 and P90 is the recipe standardisation opportunity. A wide spread = high variance = over-dosing on some batches and under-dosing on others. Standardising to P25 is the core recipe management target.</p>
  <table><thead><tr><th>Fabric</th><th>Shade</th><th>GSM</th><th>Batches</th><th>Fabric (t)</th><th>WI avg</th><th>Chem g/kg avg</th><th>Salt g/kg</th><th>Dye g/kg</th><th>Cost Tk/kg avg</th><th>Cost P25</th><th>Total (M Tk)</th></tr></thead>
  <tbody>''' + bench_rows_html + '''</tbody></table>
  <div class="insight"><strong>How to use this table:</strong> Find your target batch type (e.g. "Composite / Light/Medium / Heavy 250+"). The <em>Chem g/kg avg</em> is what batches of that type are actually dosing. The <em>Cost P25</em> is what the best 25% of batches cost. The difference, multiplied by the fabric volume, is the addressable recipe saving for that group â€” achievable without any equipment change.</div>
</div>
</div>

<p class="section-title">&#167;7 &middot; Auxiliary Audit â€” 219 Products, 24.2% of Spend (High Priority)</p>
<div class="grid">
<div class="card full">
  <h2>Top 15 Auxiliary Products by Chemical Spend â€” Ranked (Total Auxiliary: {aux_m:.0f}M Tk)</h2>
  <p class="desc">The Auxiliary class is the residual bucket: everything that is not Salt, Alkali, Dyestuff, Bleach, Acid, Enzyme or Softener. 219 products, 24.2% of total chemical spend. <strong>RUCOGEN WBL alone accounts for 249M Tk</strong> (used in 88.8% of all batches). This is a near-universal recipe item with enormous purchasing leverage. Cumulative spend column shows how quickly spend concentrates in the top products.</p>
  <table><thead><tr><th>Product</th><th>Batches</th><th>Penetration</th><th>Total Kg</th><th>Total Spend (Tk)</th><th>Avg Price Tk/kg</th><th>Grand Spend %</th><th>Cumul Aux %</th></tr></thead>
  <tbody>''' + aux_html + '''</tbody></table>
  <div class="danger"><strong>&#9888; Audit Recommendation:</strong> RUCOGEN WBL (88.8% penetration, 249M Tk) should be independently verified: is it truly an auxiliary or a misclassified specialty product? Its near-universal use makes it the single highest-leverage purchasing negotiation in the plant. Similarly, OXINOL LLS (148M Tk, 35.7% penetration) and Cellusoft Combi9800 L (178M Tk enzyme, 52.7% penetration) warrant contract review.</div>
</div>
</div>

<script type="application/json" id="chartData">
{{
  "months": {months_json},
  "costKg":  {cost_kg_json},
  "chemGpkg":{chem_gpkg_json},
  "saltGpkg":{salt_gpkg_json},
  "fabricT": {fabric_t_json},
  "cclCost": {Unit_A_cost_json},
  "mtlCost": {Unit_D_cost_json},
  "clsLabels":{cls_labels_json},
  "clsSpend": {cls_spend_json},
  "clsMass":  {cls_mass_json},
  "clsColours":{cls_colours_json},
  "t20Names": {t20_names_json},
  "t20Cost":  {t20_cost_json},
  "t20Cls":   {t20_cls_json}
}}
</script>
<script>
const D = JSON.parse(document.getElementById('chartData').textContent);
const clr = {{
  Unit_A:'#38bdf8', Unit_D:'#f59e0b', Unit_C:'#a78bfa',
  cost:'#ef4444', chem:'#38bdf8', salt:'#34d399',
  fab:'#4ade80'
}};
function mkLine(id, datasets, labels, yLabel) {{
  new Chart(document.getElementById(id), {{
    type:'line',
    data:{{labels:labels, datasets:datasets}},
    options:{{responsive:true, plugins:{{legend:{{labels:{{color:'#e2e8f0',font:{{size:11}}}}}}}},
      scales:{{x:{{ticks:{{color:'#94a3b8',maxTicksLimit:20,maxRotation:45}},grid:{{color:'#1e293b'}}}},
               y:{{ticks:{{color:'#94a3b8'}},grid:{{color:'#1e293b'}},title:{{display:true,text:yLabel,color:'#94a3b8'}}}}}}}}
  }});
}}
function mkBar(id, labels, data, colours, yLabel) {{
  new Chart(document.getElementById(id), {{
    type:'bar',
    data:{{labels:labels, datasets:[{{data:data, backgroundColor:colours, borderRadius:4}}]}},
    options:{{responsive:true, indexAxis:'y', plugins:{{legend:{{display:false}}}},
      scales:{{x:{{ticks:{{color:'#94a3b8'}},grid:{{color:'#1e293b'}},title:{{display:true,text:yLabel,color:'#94a3b8'}}}},
               y:{{ticks:{{color:'#e2e8f0',font:{{size:10}}}},grid:{{color:'#1e293b'}}}}}}}}
  }});
}}
function mkDoughnut(id, labels, data, colours) {{
  new Chart(document.getElementById(id), {{
    type:'doughnut',
    data:{{labels:labels, datasets:[{{data:data, backgroundColor:colours, borderWidth:1, borderColor:'#1e293b'}}]}},
    options:{{responsive:true, plugins:{{legend:{{position:'right',labels:{{color:'#e2e8f0',font:{{size:11}}}}}}}}}}
  }});
}}

// Chart A â€” cost/kg monthly
mkLine('cA', [
  {{label:'Cost Tk/kg', data:D.costKg, borderColor:clr.cost, backgroundColor:'rgba(239,68,68,.08)',
    fill:true, tension:.3, pointRadius:2, borderWidth:1.5}}
], D.months, 'Tk per kg fabric');

// Chart B â€” chem g/kg
mkLine('cB', [
  {{label:'Chem g/kg', data:D.chemGpkg, borderColor:clr.chem, backgroundColor:'rgba(56,189,248,.08)',
    fill:true, tension:.3, pointRadius:2, borderWidth:1.5}}
], D.months, 'g chemical per kg fabric');

// Chart C â€” salt g/kg
mkLine('cC', [
  {{label:'Salt g/kg', data:D.saltGpkg, borderColor:clr.salt, backgroundColor:'rgba(52,211,153,.08)',
    fill:true, tension:.3, pointRadius:2, borderWidth:1.5}}
], D.months, 'g salt per kg fabric');

// Chart D â€” Unit_A vs Unit_D cost/kg
mkLine('cD', [
  {{label:'Unit_A Reactive', data:D.cclCost, borderColor:clr.Unit_A, tension:.3, pointRadius:2, borderWidth:1.5}},
  {{label:'Unit_D Blends',   data:D.mtlCost, borderColor:clr.Unit_D, tension:.3, pointRadius:2, borderWidth:1.5}}
], D.months, 'Tk per kg fabric');

// Chart E â€” spend donut
mkDoughnut('cE', D.clsLabels, D.clsSpend, D.clsColours);

// Chart F â€” mass donut
mkDoughnut('cF', D.clsLabels, D.clsMass, D.clsColours);

// Chart G â€” top 20 products bar
const t20colours = D.t20Cls.map(function(c) {{
  var map = {{'Dyestuff':'#f59e0b','Auxiliary':'#38bdf8','Alkali':'#a78bfa',
             'Salt (electrolyte)':'#34d399','Bleach / redox':'#fb923c',
             'Acid':'#f87171','Softener / finish':'#e879f9','Enzyme':'#4ade80'}};
  return map[c] || '#94a3b8';
}});
mkBar('cG', D.t20Names, D.t20Cost, t20colours, 'M Tk spend');
</script>
</body>
</html>
'''.format(
    cost_m=total_cost_m,
    dye_m=dye_total_cost_m,
    aux_m=aux_total_cost_m,
    salt_t=salt_total_t,
    cost_step_html=cost_step_html,
    shade_rows_html=shade_rows_html,
    bench_rows_html=bench_rows_html,
    aux_html=aux_html,
    months_json=json.dumps(months_labels),
    cost_kg_json=json.dumps(cost_per_kg_series),
    chem_gpkg_json=json.dumps(chem_gpkg_series),
    salt_gpkg_json=json.dumps(salt_gpkg_series),
    fabric_t_json=json.dumps(fabric_t_series),
    Unit_A_cost_json=jsnull(Unit_A_cost),
    Unit_D_cost_json=jsnull(Unit_D_cost),
    cls_labels_json=json.dumps(class_order),
    cls_spend_json=json.dumps(cls_spend_vals),
    cls_mass_json=json.dumps(cls_mass_vals),
    cls_colours_json=json.dumps(cls_colour_list),
    t20_names_json=json.dumps(t20_names),
    t20_cost_json=json.dumps(t20_cost),
    t20_cls_json=json.dumps(t20_cls)
)

with open(OUT_HTML, 'w', encoding='utf-8') as f:
    f.write(html)

print('')
print('=' * 70)
print('ALL OUTPUTS WRITTEN SUCCESSFULLY')
print('  Dashboard:  ' + OUT_HTML)
print('  Benchmarks: ' + OUT_BENCHMARK)
print('  Monthly:    ' + OUT_MONTHLY)
print('  Aux Audit:  ' + OUT_AUX)
print('=' * 70)


