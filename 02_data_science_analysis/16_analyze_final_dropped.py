import sqlite3
import os
import re
from collections import Counter
import random

BASE_DIR = r"E:\Downloads\01_Projects_and_Research\AI-driven closed-loop dyeing system for Bangladesh textiles"
OUT_DIR = os.path.join(BASE_DIR, "2026_Data_Science_Rigorous_Analysis")
DB_PATH = os.path.join(OUT_DIR, "extraction_checkpoint.db")

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Get statuses of processed files
c.execute("SELECT status, COUNT(*) FROM processed_files GROUP BY status")
status_counts = c.fetchall()
print("--- DB STATUS BREAKDOWN ---")
for status, count in status_counts:
    print("{}: {}".format(status, count))

# Fetch dropped files
c.execute("SELECT filepath, status FROM processed_files WHERE status != 'success'")
dropped_files = c.fetchall()
print("\nTotal remaining dropped files: {}".format(len(dropped_files)))

tag_re = re.compile(r'<[^>]+>')
def clean_text(html):
    text = tag_re.sub('\n', html)
    return '\n'.join([line.strip() for line in text.splitlines() if line.strip()])

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
samples = {
    'Empty Document / No Tables': [],
    'Tables exist but NO Item Names': [],
    'All Items have 0 Qty or Price': [],
    'Read Error / Corrupted': [],
    'Missing Batch Number': []
}

sample_size = min(len(dropped_files), 2000)
random.seed(42)
sample_files = random.sample(dropped_files, sample_size)

print("\nRigorous Analysis on a sample of {} remaining dropped files...".format(sample_size))

for filepath, db_status in sample_files:
    filename = os.path.basename(filepath)
    if db_status == 'error':
        reasons['Read Error / Corrupted'] += 1
        if len(samples['Read Error / Corrupted']) < 3: samples['Read Error / Corrupted'].append(filename)
        continue
        
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            html = f.read()
    except:
        reasons['Read Error / Corrupted'] += 1
        if len(samples['Read Error / Corrupted']) < 3: samples['Read Error / Corrupted'].append(filename)
        continue
        
    text = clean_text(html)
    batch_match = re.search(r"Batch No[^:]*:\s*([^\n]+)", text, re.IGNORECASE)
    if not batch_match or not batch_match.group(1).split("||")[0].strip():
        reasons['Missing Batch Number'] += 1
        if len(samples['Missing Batch Number']) < 3: samples['Missing Batch Number'].append(filename)
        continue
        
    tables = parse_html_table(html)
    if not tables:
        reasons['Empty Document / No Tables'] += 1
        if len(samples['Empty Document / No Tables']) < 3: samples['Empty Document / No Tables'].append(filename)
        continue
        
    has_items = False
    all_zero = True
    
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
            if not nm or nm.lower().startswith("amount taka") or nm.lower() == "nan" or nm.startswith("Amount Taka"):
                continue
                
            has_items = True
            
            # Check if this line is valid
            is_line_valid = True
            try:
                r_val = float(str(req_qty).replace(',', ''))
                if r_val <= 0.0: is_line_valid = False
            except:
                is_line_valid = False
                
            try:
                a_str = str(amount).replace(',', '').strip()
                if a_str:
                    a_val = float(a_str)
                    if a_val <= 0.0: is_line_valid = False
                else:
                    is_line_valid = False
            except:
                is_line_valid = False
                
            if is_line_valid:
                all_zero = False
                
    if not has_items:
        reasons['Tables exist but NO Item Names'] += 1
        if len(samples['Tables exist but NO Item Names']) < 3: samples['Tables exist but NO Item Names'].append(filename)
    elif all_zero:
        reasons['All Items have 0 Qty or Price'] += 1
        if len(samples['All Items have 0 Qty or Price']) < 3: samples['All Items have 0 Qty or Price'].append(filename)
    else:
        reasons['Other Unhandled Issue'] += 1

print("\n--- DETAILED DROP REASONS ---")
for reason, count in reasons.most_common():
    print("- {}: {} ({:.2f}%)".format(reason, count, (count/sample_size)*100))
    print("  Samples: {}".format(', '.join(samples.get(reason, []))))

conn.close()
