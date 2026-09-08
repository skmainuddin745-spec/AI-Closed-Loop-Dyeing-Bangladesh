import os
import sqlite3
import re
from datetime import datetime
from collections import defaultdict
import csv

BASE_DIR = r"E:\Downloads\01_Projects_and_Research\AI-driven closed-loop dyeing system for Bangladesh textiles"
DB_PATH = os.path.join(BASE_DIR, "2026_Data_Science_Rigorous_Analysis", "extraction_checkpoint.db")
LAYOUT_FILE = os.path.join(BASE_DIR, "SMART_DYEING_Machine_Layout.html")
OUT_DIR = os.path.join(BASE_DIR, "2026-09-03_Categorization_Insights")

# --- 1. PARSE MACHINE LAYOUT ---
machine_map = {}
with open(LAYOUT_FILE, 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

# Regex to extract <text class="mid">Mc X</text> ... <text class="mnm">...</text> ... <text class="mcap">...</text>
# We can just find them in order since they are grouped in <g> tags
g_tags = re.findall(r'<g>.*?</g>', html, re.DOTALL)
for g in g_tags:
    mc_match = re.search(r'class="mid"[^>]*>Mc\s*([^<]+)<', g)
    mnm_match = re.search(r'class="mnm"[^>]*>([^<]+)<', g)
    mcap_match = re.search(r'class="mcap"[^>]*>(\d+)\s*kg<', g)
    
    if mc_match and mcap_match:
        mc = mc_match.group(1).strip()
        brand = mnm_match.group(1).strip() if mnm_match else "Unknown"
        cap = int(mcap_match.group(1).strip())
        machine_map[mc] = {"brand": brand, "capacity": cap}

# --- 2. CATEGORIZATION FUNCTIONS ---
def categorize_fabric(raw_fabric):
    f = raw_fabric.split('||')[0].strip().upper()
    if not f: return "Unknown"
    
    if "S/J" in f or "SINGLE JERSEY" in f:
        if "RIB" in f or "FLEECE" in f or "TERRY" in f: return "Composite (Jersey + Other)"
        if "L S/J" in f or "LYCRA" in f: return "Lycra Single Jersey"
        return "Single Jersey"
    elif "RIB" in f:
        return "Rib Fabric"
    elif "INTERLOCK" in f:
        return "Interlock"
    elif "FLEECE" in f or "BRUSHBACK" in f or "TERRY" in f:
        return "Fleece / Heavy"
    elif "PIQUE" in f or "PK" in f or "LACOSTE" in f:
        return "Pique / Lacoste"
    return "Other"

def categorize_gsm(raw_gsm):
    if not raw_gsm or raw_gsm.strip() == "00" or raw_gsm.strip() == "0": return "Unknown"
    
    # Extract all numbers and find the max
    nums = re.findall(r'\d+', raw_gsm)
    if not nums: return "Unknown"
    
    max_gsm = max(int(n) for n in nums)
    if max_gsm < 150: return "Lightweight (<150)"
    elif max_gsm <= 249: return "Mediumweight (150-249)"
    else: return "Heavyweight (250+)"

def categorize_shade(raw_color):
    c = str(raw_color).upper()
    if not c or c == "NAN": return "Unknown"
    if "WHITE" in c or "BLEACH" in c or "DANCER" in c or "SNOW" in c: return "White/Bleach"
    if "BLACK" in c or "NAVY" in c or "DARK" in c: return "Dark/Extra Dark"
    if "AOP" in c: return "AOP (All Over Print)"
    return "Colored (Light/Medium)"

def clean_float(val):
    try:
        return float(re.sub(r'[^\d.]', '', str(val)))
    except:
        return 0.0

# --- 3. EXECUTE ENGINE ---
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

print("Fetching batch data...")
c.execute("""
    SELECT Batch_No, Prepare_Date, Fabric_Qty, Water, Liquor_Ratio, GSM, 
           Fabric_Type, Color_Depth, Dyeing_Type, MC_No 
    FROM headers
    GROUP BY Batch_No
""")
rows = c.fetchall()

# Aggregators
month_time_series = defaultdict(lambda: {"batches": 0, "kg": 0.0, "Unit_A": 0, "Unit_D": 0, "Unit_C": 0})
permutation_matrix = defaultdict(int)
machine_stats = defaultdict(lambda: {"batches": 0, "water": 0.0, "lr": 0.0})

print("Categorizing {} batches...".format(len(rows)))

for row in rows:
    batch_no, prep_date, f_qty, water, lr, gsm, fabric, color, dye_type, mc_no = row
    
    # Prefix / Dye Class
    if batch_no.startswith("Unit_A"): prefix = "Unit_A (Reactive)"
    elif batch_no.startswith("Unit_D"): prefix = "Unit_D (Blends)"
    elif batch_no.startswith("Unit_C"): prefix = "Unit_C (Disperse)"
    else: prefix = "Other"
    
    # Standardize
    fab_cat = categorize_fabric(fabric)
    gsm_cat = categorize_gsm(gsm)
    shade_cat = categorize_shade(color)
    
    # Floats
    f_qty_val = clean_float(f_qty)
    water_val = clean_float(water)
    lr_val = clean_float(lr)
    
    # Time Series (YYYY-MM)
    date_match = re.search(r'(\d{2}-\w{3}-\d{4}|\d{4}-\d{2}-\d{2})', str(prep_date))
    month_key = "Unknown"
    if date_match:
        raw_d = date_match.group(1)
        try:
            if "-" in raw_d and raw_d[2] == "-":
                dt = datetime.strptime(raw_d, "%d-%b-%Y")
            else:
                dt = datetime.strptime(raw_d, "%Y-%m-%d")
            month_key = dt.strftime("%Y-%m")
        except: pass
        
    month_time_series[month_key]["batches"] += 1
    month_time_series[month_key]["kg"] += f_qty_val
    if "Unit_A" in prefix: month_time_series[month_key]["Unit_A"] += 1
    if "Unit_D" in prefix: month_time_series[month_key]["Unit_D"] += 1
    if "Unit_C" in prefix: month_time_series[month_key]["Unit_C"] += 1
    
    # Permutation Matrix
    perm_key = "{} | {} | {} | {}".format(prefix, fab_cat, gsm_cat, shade_cat)
    permutation_matrix[perm_key] += 1
    
    # Machine Correlation
    mc_clean = str(mc_no).split('-')[0].strip() # Clean "23-B" to "23" if needed, though they are mostly just ints
    if mc_clean in machine_map:
        m_key = "Mc {} ({}kg - {})".format(mc_clean, machine_map[mc_clean]["capacity"], machine_map[mc_clean]["brand"])
        machine_stats[m_key]["batches"] += 1
        machine_stats[m_key]["water"] += water_val
        if lr_val > 0:
            machine_stats[m_key]["lr"] += lr_val

print("Writing reports to {}...".format(OUT_DIR))

# 1. Permutation Matrix
with open(os.path.join(OUT_DIR, "Permutation_Matrix.md"), 'w', encoding='utf-8') as f:
    f.write("# Master Permutation Matrix\n\n")
    f.write("| Prefix | Fabric Category | GSM Category | Shade Category | Total Batches |\n")
    f.write("| :--- | :--- | :--- | :--- | :--- |\n")
    for k, v in sorted(permutation_matrix.items(), key=lambda x: x[1], reverse=True):
        parts = k.split(' | ')
        f.write("| {} | {} | {} | {} | {:,} |\n".format(parts[0], parts[1], parts[2], parts[3], v))
        
# 2. Time Series
with open(os.path.join(OUT_DIR, "Time_Series_2021_2026.csv"), 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(["Month", "Total_Batches", "Total_Fabric_Kg", "Unit_A_Count", "Unit_D_Count", "Unit_C_Count"])
    for m in sorted(month_time_series.keys()):
        d = month_time_series[m]
        writer.writerow([m, d["batches"], round(d["kg"],2), d["Unit_A"], d["Unit_D"], d["Unit_C"]])

# 3. Machine Stats
with open(os.path.join(OUT_DIR, "Machine_Utilization.md"), 'w', encoding='utf-8') as f:
    f.write("# Machine Utilization & Average Consumptions\n\n")
    f.write("| Machine | Total Batches Processed | Avg Water (L) | Avg Liquor Ratio |\n")
    f.write("| :--- | :--- | :--- | :--- |\n")
    for m, d in sorted(machine_stats.items(), key=lambda x: x[1]["batches"], reverse=True):
        avg_w = d["water"] / d["batches"] if d["batches"] > 0 else 0
        avg_lr = d["lr"] / d["batches"] if d["batches"] > 0 else 0
        f.write("| {} | {:,} | {:.2f} | 1:{:.2f} |\n".format(m, d["batches"], avg_w, avg_lr))

print("Categorization engine finished successfully!")
conn.close()



