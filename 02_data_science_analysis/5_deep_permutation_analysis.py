import os
import csv
from collections import defaultdict
import re

BASE_DIR = r"E:\Downloads\01_Projects_and_Research\AI-driven closed-loop dyeing system for Bangladesh textiles\2026_Data_Science_Rigorous_Analysis"
HEADER_FILE = os.path.join(BASE_DIR, "Universal_Headers.csv")
LINES_FILE = os.path.join(BASE_DIR, "Universal_Lines.csv")
OUTPUT_MD = os.path.join(BASE_DIR, "Universal_Permutation_Analysis.md")

def parse_float(val_str):
    try:
        return float(str(val_str).replace(',', '').strip())
    except:
        return 0.0

def categorize_fabric(fabric_str):
    f = str(fabric_str).lower()
    if not f: return "Unknown"
    if "cvc" in f or "poly" in f or "fleece" in f:
        return "Polyester/Blend"
    if "viscose" in f:
        return "Viscose"
    if "lycra" in f or "elastane" in f or "spandex" in f:
        return "Cotton-Elastane"
    if "rib" in f or "interlock" in f or "s/j" in f or "single jersey" in f or "cotton" in f:
        return "100% Cotton"
    return "Other"

def extract_mc(mc_str):
    s = str(mc_str).strip()
    return s if s else "Unknown"

def extract_dyeing_type(dtype_str):
    s = str(dtype_str).split("||")[0].strip()
    return s if s else "Unknown"

def categorize_gsm(gsm_str):
    s = str(gsm_str).strip()
    if not s: return "Unknown"
    
    # Extract all numbers
    nums = re.findall(r'\d+', s)
    if not nums: return "Unknown"
    
    avg_gsm = sum(float(n) for n in nums) / len(nums)
    if avg_gsm <= 150: return "Light (<=150)"
    if avg_gsm <= 220: return "Medium (151-220)"
    return "Heavy (>220)"

if __name__ == "__main__":
    print("Loading line cost data...")
    batch_costs = defaultdict(lambda: {"cost_tk": 0.0, "qty_kg": 0.0})
    with open(LINES_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            b = row.get("Batch No")
            if not b: continue
            batch_costs[b]["cost_tk"] += parse_float(row.get("Amount_Tk"))
            batch_costs[b]["qty_kg"] += parse_float(row.get("Req_Qty_kg"))
            
    print("Cross-referencing permutations...")
    # Key: (Fabric, DyeingType, MC, GSM)
    perms = defaultdict(lambda: {"batches": 0, "water": 0.0, "fabric_qty": 0.0, "cost_tk": 0.0, "chem_qty_kg": 0.0})
    
    valid_count = 0
    with open(HEADER_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            b = row.get("Batch No")
            if not b or b not in batch_costs: continue
            
            fabric = parse_float(row.get("Fabric Qty"))
            if fabric <= 0: continue
            
            water = parse_float(row.get("Water"))
            
            fab_cat = categorize_fabric(row.get("Fabric Type/Color"))
            dtype_cat = extract_dyeing_type(row.get("Dyeing Type/Status"))
            mc_cat = extract_mc(row.get("MC No"))
            gsm_cat = categorize_gsm(row.get("GSM"))
            
            pkey = (fab_cat, dtype_cat, mc_cat, gsm_cat)
            
            perms[pkey]["batches"] += 1
            perms[pkey]["fabric_qty"] += fabric
            perms[pkey]["water"] += water
            perms[pkey]["cost_tk"] += batch_costs[b]["cost_tk"]
            perms[pkey]["chem_qty_kg"] += batch_costs[b]["qty_kg"]
            valid_count += 1

    print("Found {} unique combinatorial permutations across {} valid batches.".format(len(perms), valid_count))

    # Calculate metrics and filter out permutations with < 5 batches (to ensure statistical relevance)
    analyzed_perms = []
    for k, v in perms.items():
        if v["batches"] < 5: continue
        
        avg_cost = v["cost_tk"] / v["fabric_qty"]
        avg_water = v["water"] / v["fabric_qty"]
        avg_chem = v["chem_qty_kg"] / v["fabric_qty"]
        
        analyzed_perms.append({
            "key": k,
            "batches": v["batches"],
            "fabric": v["fabric_qty"],
            "cost_per_kg": avg_cost,
            "water_per_kg": avg_water,
            "chem_per_kg": avg_chem
        })
        
    print("Filtered down to {} statistically significant permutations (>= 5 batches).".format(len(analyzed_perms)))
    
    # Sort for best and worst
    # Best cost efficiency
    best_cost = sorted(analyzed_perms, key=lambda x: x["cost_per_kg"])[:15]
    # Worst cost efficiency
    worst_cost = sorted(analyzed_perms, key=lambda x: x["cost_per_kg"], reverse=True)[:15]
    
    md = []
    md.append("# Root-Level Combinatorial Analysis")
    md.append("This report examines every unique permutation of **Fabric Type x Dyeing Process x Machine No x GSM** across the verified core dataset of {} unbiased batches.\n".format(valid_count))
    
    md.append("## 1. Top 15 Most Efficient Operational Combinations")
    md.append("These specific combinations represent the absolute highest profitability and operational efficiency in the factory. They should be prioritized for max loading.")
    md.append("| Fabric Type | Dyeing Type | Machine No | GSM Class | Batches | Cost/kg (Tk) | Water/kg (L) | Chem/kg (kg) |")
    md.append("|---|---|---|---|---|---|---|---|")
    for p in best_cost:
        md.append("| {} | {} | {} | {} | {:,} | **{:,.2f}** | {:,.2f} | {:,.3f} |".format(
            p["key"][0], p["key"][1], p["key"][2], p["key"][3], p["batches"], p["cost_per_kg"], p["water_per_kg"], p["chem_per_kg"]
        ))
        
    md.append("\n## 2. Top 15 Most Wasteful / Expensive Combinations")
    md.append("These combinations represent catastrophic profitability bleed. Reworks or specific machine-fabric mismatches heavily inflate chemical and water load.")
    md.append("| Fabric Type | Dyeing Type | Machine No | GSM Class | Batches | Cost/kg (Tk) | Water/kg (L) | Chem/kg (kg) |")
    md.append("|---|---|---|---|---|---|---|---|")
    for p in worst_cost:
        md.append("| {} | {} | {} | {} | {:,} | **{:,.2f}** | {:,.2f} | {:,.3f} |".format(
            p["key"][0], p["key"][1], p["key"][2], p["key"][3], p["batches"], p["cost_per_kg"], p["water_per_kg"], p["chem_per_kg"]
        ))

    # Dyeing Type Analysis
    dtype_agg = defaultdict(lambda: {"cost": 0.0, "qty": 0.0, "batches": 0})
    for p in analyzed_perms:
        dt = p["key"][1]
        dtype_agg[dt]["cost"] += p["cost_per_kg"] * p["fabric"]
        dtype_agg[dt]["qty"] += p["fabric"]
        dtype_agg[dt]["batches"] += p["batches"]
        
    md.append("\n## 3. The Rework Penalty Matrix")
    md.append("Aggregating strictly by Dyeing Type reveals the true financial penalty of non-'Normal' procedures.")
    md.append("| Dyeing Process | Total Batches | True Cost/kg (Tk) |")
    md.append("|---|---|---|")
    for dt, data in sorted(dtype_agg.items(), key=lambda x: x[1]["cost"]/x[1]["qty"] if x[1]["qty"]>0 else 0):
        c_kg = data["cost"]/data["qty"] if data["qty"] > 0 else 0
        md.append("| {} | {:,} | **{:,.2f}** |".format(dt, data["batches"], c_kg))

    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
        
    print("Combinatorial Analysis Complete! Generated: {}".format(OUTPUT_MD))
