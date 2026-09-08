import os
import csv
import sqlite3
import re
from datetime import datetime

BASE_DIR = r"E:\Downloads\01_Projects_and_Research\AI-driven closed-loop dyeing system for Bangladesh textiles"
DB_PATH = os.path.join(BASE_DIR, "2026_Data_Science_Rigorous_Analysis", "extraction_checkpoint.db")
OUT_CSV = os.path.join(BASE_DIR, "2026-09-03_Categorization_Insights", "MASTER_289403_BATCHES_2021_2026.csv")

def cat_fabric(f):
    f=str(f).split('||')[0].strip().upper()
    if 'S/J' in f or 'SINGLE JERSEY' in f:
        if 'RIB' in f or 'FLEECE' in f: return 'Composite'
        if 'L S/J' in f or 'LYCRA' in f: return 'Lycra S/J'
        return 'Single Jersey'
    if 'RIB' in f:    return 'Rib Fabric'
    if 'INTERLOCK' in f: return 'Interlock'
    if 'FLEECE' in f or 'TERRY' in f or 'BRUSHBACK' in f: return 'Fleece/Heavy'
    if 'PIQUE' in f or ' PK' in f or 'LACOSTE' in f: return 'Pique'
    return 'Other'

def cat_gsm(g):
    nums=re.findall(r'\d+',str(g))
    if not nums: return 'Unknown'
    m=max(int(n) for n in nums)
    if m<150: return 'Light (<150)'
    if m<=249: return 'Medium (150-249)'
    return 'Heavy (250+)'

def cat_shade(c):
    c=str(c).upper()
    if 'WHITE' in c or 'BLEACH' in c: return 'White/Bleach'
    if 'BLACK' in c or 'NAVY' in c or 'DARK' in c: return 'Dark/Extra Dark'
    if 'AOP' in c: return 'AOP'
    return 'Light/Medium Colored'

def parse_date(d):
    raw=re.search(r'(\d{2}-\w{3}-\d{4}|\d{4}-\d{2}-\d{2})',str(d))
    if not raw: return None
    s=raw.group(1)
    try:
        if s[2]=='-': return datetime.strptime(s,'%d-%b-%Y')
        return datetime.strptime(s,'%Y-%m-%d')
    except: return None

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute("""SELECT Batch_No, Prepare_Date, Fabric_Qty, Water, Liquor_Ratio, 
                    Fabric_Type, GSM, Color_Depth, MC_No, Dyeing_Type 
             FROM headers GROUP BY Batch_No""")
rows = c.fetchall()

print("Dumping {:,} rows to CSV...".format(len(rows)))

with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(["Batch_No", "Prepare_Date", "Month", "Year", "Dye_Unit_Class", 
                     "Fabric_Category", "GSM_Category", "Shade_Category", 
                     "Fabric_Qty_kg", "Water_Liters", "Liquor_Ratio_1_to_X", 
                     "Machine_No", "Dyeing_Type_Code", 
                     "Raw_Fabric_String", "Raw_GSM_String", "Raw_Color_String"])
    
    count = 0
    for row in rows:
        batch, prep_date, f_qty, water, lr, fab, gsm, color, mc, dyeing_type = row
        
        # Parse date for Month/Year
        dt = parse_date(prep_date)
        month_str = dt.strftime("%Y-%m") if dt else "Unknown"
        year_str = str(dt.year) if dt else "Unknown"
        
        # Categorize
        unit = 'Unit_A' if batch.startswith('Unit_A') else ('Unit_C' if batch.startswith('Unit_C') else ('Unit_D' if batch.startswith('Unit_D') else 'Other'))
        f_cat = cat_fabric(fab)
        g_cat = cat_gsm(gsm)
        s_cat = cat_shade(color)
        
        writer.writerow([
            batch, prep_date, month_str, year_str, unit,
            f_cat, g_cat, s_cat,
            f_qty, water, lr,
            mc, dyeing_type,
            fab, gsm, color
        ])
        count += 1

print("Successfully exported {:,} unique batches to: {}".format(count, OUT_CSV))
conn.close()

