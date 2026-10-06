import os
import sqlite3
import re
import csv
from collections import defaultdict
from datetime import datetime

BASE_DIR = r"E:\Downloads\01_Projects_and_Research\AI-driven closed-loop dyeing system for Bangladesh textiles"
DB_PATH = os.path.join(BASE_DIR, "2026_Data_Science_Rigorous_Analysis", "extraction_checkpoint.db")
OUT_DIR = os.path.join(BASE_DIR, "2026-09-03_Categorization_Insights")

def categorize_fabric(f):
    f = str(f).split('||')[0].strip().upper()
    if "S/J" in f or "SINGLE JERSEY" in f:
        if "RIB" in f or "FLEECE" in f: return "Composite"
        if "L S/J" in f or "LYCRA" in f: return "Lycra S/J"
        return "Single Jersey"
    elif "RIB" in f: return "Rib Fabric"
    elif "INTERLOCK" in f: return "Interlock"
    elif "FLEECE" in f or "BRUSHBACK" in f or "TERRY" in f: return "Fleece/Heavy"
    elif "PIQUE" in f or "PK" in f or "LACOSTE" in f: return "Pique"
    return "Other"

def categorize_gsm(g):
    nums = re.findall(r'\d+', str(g))
    if not nums: return "Unknown"
    m = max(int(n) for n in nums)
    if m < 150: return "Light (<150)"
    if m <= 249: return "Medium (150-249)"
    return "Heavy (250+)"

def categorize_shade(c):
    c = str(c).upper()
    if "WHITE" in c or "BLEACH" in c: return "White/Bleach"
    if "BLACK" in c or "NAVY" in c or "DARK" in c: return "Dark/Extra Dark"
    if "AOP" in c: return "AOP"
    return "Light/Medium Colored"

def clean_float(val):
    try: return float(re.sub(r'[^\d.]', '', str(val)))
    except: return 0.0

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute("""
    SELECT Batch_No, Prepare_Date, Fabric_Qty, Water, Liquor_Ratio, Fabric_Type, GSM, Color_Depth
    FROM headers GROUP BY Batch_No
""")
rows = c.fetchall()

# Aggregators
monthwise_permutations = defaultdict(lambda: {"count": 0, "kg": 0.0, "water": 0.0})

for row in rows:
    batch, prep_date, f_qty, water, lr, fab, gsm, color = row
    
    # Strictly Filter for 2021-2026 Month
    date_match = re.search(r'(\d{2}-\w{3}-\d{4}|\d{4}-\d{2}-\d{2})', str(prep_date))
    month_key = None
    if date_match:
        raw_d = date_match.group(1)
        try:
            if "-" in raw_d and raw_d[2] == "-": dt = datetime.strptime(raw_d, "%d-%b-%Y")
            else: dt = datetime.strptime(raw_d, "%Y-%m-%d")
            year = dt.year
            if 2021 <= year <= 2026:
                month_key = dt.strftime("%Y-%m")
        except: pass
    
    if not month_key:
        continue # Skip anything outside 2021-2026
        
    dye_class = "Reactive (Unit_A)" if batch.startswith("Unit_A") else ("Disperse (Unit_C)" if batch.startswith("Unit_C") else ("Blends (Unit_D)" if batch.startswith("Unit_D") else "Other"))
    f_cat = categorize_fabric(fab)
    g_cat = categorize_gsm(gsm)
    s_cat = categorize_shade(color)
    
    f_qty_val = clean_float(f_qty)
    w_val = clean_float(water)
    
    # Permutation Key: Month | Dye Class | Fabric | GSM | Shade
    perm_key = (month_key, dye_class, f_cat, g_cat, s_cat)
    
    monthwise_permutations[perm_key]["count"] += 1
    monthwise_permutations[perm_key]["kg"] += f_qty_val
    monthwise_permutations[perm_key]["water"] += w_val

out_csv = os.path.join(OUT_DIR, "Monthwise_InDepth_Permutations_2021_2026.csv")
with open(out_csv, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(["Month", "Dye_Class", "Fabric_Category", "GSM_Category", "Shade_Category", "Total_Batches", "Total_Fabric_Kg", "Total_Water_Liters"])
    
    # Sort chronologically by month, then by highest volume
    sorted_items = sorted(monthwise_permutations.items(), key=lambda x: (x[0][0], -x[1]["count"]))
    
    for k, v in sorted_items:
        writer.writerow([
            k[0], k[1], k[2], k[3], k[4],
            v["count"], round(v["kg"], 2), round(v["water"], 2)
        ])

print("Strict 2021-2026 Monthwise Permutation matrix generated at:", out_csv)
conn.close()

