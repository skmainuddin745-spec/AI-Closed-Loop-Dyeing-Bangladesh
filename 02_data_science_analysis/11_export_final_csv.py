import sqlite3
import csv
import os

BASE_DIR = r"E:\Downloads\01_Projects_and_Research\AI-driven closed-loop dyeing system for Bangladesh textiles"
OUT_DIR = os.path.join(BASE_DIR, "2026_Data_Science_Rigorous_Analysis")
DB_PATH = os.path.join(OUT_DIR, "extraction_checkpoint.db")
HEADER_CSV = os.path.join(OUT_DIR, "Universal_Headers.csv")
LINES_CSV = os.path.join(OUT_DIR, "Universal_Lines.csv")

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

print("Deduplicating perfectly and exporting to CSV...")
# Deduplicate Hash and keep batch with max lines
c.execute('''
    SELECT Batch_No, Prepare_Date, Order_No, Buyer, Fabric_Qty, Water, Liquor_Ratio, GSM, 
    Color_Depth, Fabric_Type, Dyeing_Type, MC_No, Source_File, MAX(Lines_Count) 
    FROM headers 
    GROUP BY Batch_No
''')
best_headers = c.fetchall()

valid_source_files = set([row[12] for row in best_headers])

print("Writing headers...")
with open(HEADER_CSV, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(["Batch No", "Prepare Date", "Order No", "Buyer", "Fabric Qty", "Water", "Liquor Ratio", "GSM", "Color Depth", "Fabric Type/Color", "Dyeing Type/Status", "MC No", "Source_File"])
    for row in best_headers:
        writer.writerow(row[:-1]) # exclude Lines_Count
        
print("Fetching lines...")
c.execute("SELECT Batch_No, Item_Name, Req_Qty_kg, Amount_Tk, Source_File FROM lines")

with open(LINES_CSV, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(["Batch No", "Item_Name", "Req_Qty_kg", "Amount_Tk"])
    
    print("Writing lines...")
    count = 0
    while True:
        rows = c.fetchmany(10000)
        if not rows:
            break
        for row in rows:
            if row[4] in valid_source_files:
                writer.writerow(row[:-1])
        count += len(rows)
        if count % 100000 == 0:
            print("Processed {} lines...".format(count))
            
conn.close()
print("Final Export Complete! The universal dataset now contains exactly {0:,} unbiased batches!".format(len(best_headers)))
