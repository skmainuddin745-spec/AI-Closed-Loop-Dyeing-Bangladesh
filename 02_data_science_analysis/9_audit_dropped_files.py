import os
import re
import sqlite3
import random

BASE_DIR = r"E:\Downloads\01_Projects_and_Research\AI-driven closed-loop dyeing system for Bangladesh textiles"
OUT_DIR = os.path.join(BASE_DIR, "2026_Data_Science_Rigorous_Analysis")
DB_PATH = os.path.join(OUT_DIR, "extraction_checkpoint.db")

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
    th_td_pattern = re.compile(r'<(?:th|td)[^>]*>(.*?)</(?:th|td)>', re.IGNORECASE | re.DOTALL)
    
    tables_data = []
    for table_match in table_pattern.finditer(html):
        table_html = table_match.group(1)
        rows = []
        for tr_match in tr_pattern.finditer(table_html):
            tr_html = tr_match.group(1)
            cells = []
            for cell_match in th_td_pattern.finditer(tr_html):
                cell_html = cell_match.group(1)
                cell_text = tag_re.sub(' ', cell_html).strip()
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

if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT filepath FROM processed_files WHERE status='zero_cost_or_empty'")
    dropped_files = [r[0] for r in c.fetchall()]
    conn.close()
    
    print(f"Total dropped files: {len(dropped_files)}")
    
    # Audit a random sample of 5000 files
    sample = random.sample(dropped_files, min(5000, len(dropped_files)))
    
    stats = {
        "missing_headers": 0,
        "true_zero_cost": 0,
        "parser_failed": 0
    }
    
    parser_failed_examples = []
    
    for filepath in sample:
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                html = f.read()
                
            text = clean_text(html)
            
            # Check if it has all valid headers
            batch = get_field(text, "Batch No")
            date = get_field(text, "Prepare Date")
            order = get_field(text, "Order No")
            fab = get_raw_field(text, "Fabric Type")
            
            if not batch or not date or not order or not fab:
                stats["missing_headers"] += 1
                continue
                
            # It has valid headers! Let's see why the table parser failed.
            tables = parse_html_table(html)
            
            if not tables:
                stats["parser_failed"] += 1
                parser_failed_examples.append(filepath)
                continue
                
            has_chemicals = False
            has_zero = False
            
            for t_rows in tables:
                for row in t_rows:
                    nm = ""
                    req_qty = ""
                    amount = ""
                    for key, val in row.items():
                        if "item name" in key: nm = val
                        elif "req.qty" in key or "req" in key: req_qty = val
                        elif "amount" in key: amount = val
                        
                    if not nm or nm.lower().startswith("amount taka"): continue
                    if not req_qty and not amount: continue
                    
                    has_chemicals = True
                    try:
                        r_val = float(str(req_qty).replace(',', ''))
                        a_val = float(str(amount).replace(',', ''))
                        if r_val <= 0 or a_val <= 0:
                            has_zero = True
                    except:
                        has_zero = True
                        
            if not has_chemicals:
                stats["parser_failed"] += 1
                parser_failed_examples.append(filepath)
            elif has_zero:
                stats["true_zero_cost"] += 1
            else:
                print(f"WARNING: File {filepath} is perfectly valid but was dropped?!")
                
        except Exception as e:
            pass
            
    print("\n--- AUDIT RESULTS ON 5000 RANDOM DROPPED FILES ---")
    print(f"Files that were missing basic headers (junk/blank HTML templates): {stats['missing_headers']}")
    print(f"Files with valid headers but TRUE zero-cost chemicals (rightfully dropped per zero-bias rule): {stats['true_zero_cost']}")
    print(f"Files with valid headers where the table parser couldn't find chemicals (potential parser failure): {stats['parser_failed']}")
    
    if parser_failed_examples:
        print("\nExamples of parser failures (we must rescue these!):")
        for ex in parser_failed_examples[:5]:
            print(ex)
