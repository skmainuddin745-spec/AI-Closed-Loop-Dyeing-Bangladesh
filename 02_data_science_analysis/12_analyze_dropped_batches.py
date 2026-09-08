import sqlite3
import os
import re
from collections import Counter
import csv
import random

BASE_DIR = r"E:\Downloads\01_Projects_and_Research\AI-driven closed-loop dyeing system for Bangladesh textiles"
OUT_DIR = os.path.join(BASE_DIR, "2026_Data_Science_Rigorous_Analysis")
DB_PATH = os.path.join(OUT_DIR, "extraction_checkpoint.db")

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

print("Fetching successful batch numbers to check for duplicates...")
c.execute("SELECT DISTINCT Batch_No FROM headers")
valid_batches = set(row[0] for row in c.fetchall() if row[0])
print("Total valid unique batches: {}".format(len(valid_batches)))

print("Fetching dropped files (zero_cost_or_empty, invalid, error)...")
c.execute("SELECT filepath, status FROM processed_files WHERE status IN ('zero_cost_or_empty', 'invalid', 'error')")
dropped_files = c.fetchall()
print("Total dropped files to analyze: {}".format(len(dropped_files)))

tag_re = re.compile(r'<[^>]+>')

def clean_text(html):
    text = tag_re.sub('\n', html)
    return '\n'.join([line.strip() for line in text.splitlines() if line.strip()])

def get_field(text, label):
    m = re.search(re.escape(label) + r"[^:]*:\s*([^\n]+)", text, re.IGNORECASE)
    if m:
        return m.group(1).split("||")[0].strip()
    return ""

def get_raw_field(text, label):
    m = re.search(re.escape(label) + r"[^:]*:\s*([^\n]+)", text, re.IGNORECASE)
    return m.group(1).strip() if m else ""

def parse_html_table(html):
    table_pattern = re.compile(r'<table[^>]*>(.*?)</table>', re.IGNORECASE | re.DOTALL)
    tr_pattern = re.compile(r'<tr[^>]*>(.*?)</tr>', re.IGNORECASE | re.DOTALL)
    
    tables_data = []
    for table_match in table_pattern.finditer(html):
        table_html = table_match.group(1)
        rows = []
        for tr_match in tr_pattern.finditer(table_html):
            tr_html = tr_match.group(1)
            parts = re.split(r'<(?:td|th)[^>]*>', tr_html, flags=re.IGNORECASE)
            cells = []
            for part in parts[1:]:
                cell_text = tag_re.sub(' ', part).strip()
                cell_text = re.sub(r'\s+', ' ', cell_text)
                cells.append(cell_text)
            if cells:
                rows.append(cells)
                
        if rows:
            header_idx = -1
            for i, r in enumerate(rows):
                joined = " ".join([c.lower() for c in r])
                if "item name" in joined and ("gl" in joined or "req" in joined or "issue" in joined):
                    header_idx = i
                    break
            
            if header_idx != -1:
                headers = [c.lower() for c in rows[header_idx]]
                table_rows = []
                for r in rows[header_idx+1:]:
                    if len(r) == len(headers):
                        row_data = {headers[i]: r[i] for i in range(len(headers))}
                        table_rows.append(row_data)
                    elif len(r) < len(headers):
                        row_data = {headers[i]: r[i] for i in range(len(r))}
                        table_rows.append(row_data)
                tables_data.append(table_rows)
    return tables_data


reasons = Counter()
duplicated_count = 0
unique_dropped_batches = set()

sample_size = min(len(dropped_files), 1000)
random.seed(42)
sample_files = random.sample(dropped_files, sample_size)

print("Rigorous Analysis on a sample of {} dropped files...".format(sample_size))

for i, (filepath, db_status) in enumerate(sample_files):
    if i % 5000 == 0 and i > 0:
        print("Processed {} files...".format(i))
        
    if db_status == 'error':
        reasons['File Read/Encoding Error'] += 1
        continue
        
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            html = f.read()
    except:
        reasons['File Read/Encoding Error'] += 1
        continue
        
    text = clean_text(html)
    batch_no = get_field(text, "Batch No")
    
    if not batch_no:
        reasons['Missing Batch Number'] += 1
        continue
        
    unique_dropped_batches.add(batch_no)
    
    if batch_no in valid_batches:
        duplicated_count += 1
        reasons['Duplicated Batch (Already in Valid Dataset)'] += 1
        continue
        
    tables = parse_html_table(html)
    if not tables:
        reasons['No Items Table Found (Empty Document)'] += 1
        continue
        
    has_items = False
    zero_qty = False
    zero_price = False
    
    for t_rows in tables:
        for row in t_rows:
            nm = ""
            req_qty = ""
            amount = ""
            
            for key, val in row.items():
                if "item name" in key: nm = val
                elif "req.qty" in key or "req" in key: req_qty = val
                elif "amount" in key: amount = val
                
            nm = nm.strip()
            if not nm or nm.lower().startswith("amount taka") or nm.lower() == "nan":
                continue
                
            has_items = True
            
            r_val = 0.0
            a_val = 0.0
            
            if req_qty:
                try: r_val = float(str(req_qty).replace(',', ''))
                except: pass
                
            if amount:
                try: a_val = float(str(amount).replace(',', '').strip())
                except: pass
                
            if r_val <= 0.0:
                zero_qty = True
            if a_val <= 0.0:
                zero_price = True
                
    if not has_items:
        reasons['Table exists but No Valid Item Names'] += 1
    elif zero_qty:
        reasons['Zero or Missing Required Quantity (Req_Qty_kg = 0)'] += 1
    elif zero_price:
        reasons['Zero or Missing Amount (Amount_Tk = 0)'] += 1
    else:
        reasons['Other Integrity Violation'] += 1

print("\n--- ANALYSIS RESULTS ---")
print("Analyzed Sample Size: {}".format(sample_size))
print("Total Unique Batch IDs in Sample: {}".format(len(unique_dropped_batches)))
print("Duplicated (Already Valid) in Sample: {} ({:.2f}%)".format(duplicated_count, (duplicated_count/sample_size)*100))

print("\nDetailed Drop Reasons:")
for reason, count in reasons.most_common():
    print("- {}: {} ({:.2f}%)".format(reason, count, (count/sample_size)*100))
    
conn.close()
