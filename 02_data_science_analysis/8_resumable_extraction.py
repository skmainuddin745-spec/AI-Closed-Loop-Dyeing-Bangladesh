import os
import re
import sqlite3
import hashlib
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
import traceback

BASE_DIR = r"E:\Downloads\01_Projects_and_Research\AI-driven closed-loop dyeing system for Bangladesh textiles"
OUT_DIR = os.path.join(BASE_DIR, "2026_Data_Science_Rigorous_Analysis")
DB_PATH = os.path.join(OUT_DIR, "extraction_checkpoint.db")
HEADER_CSV = os.path.join(OUT_DIR, "Universal_Headers.csv")
LINES_CSV = os.path.join(OUT_DIR, "Universal_Lines.csv")

tag_re = re.compile(r'<[^>]+>')

def clean_text(html):
    text = tag_re.sub('\n', html)
    return '\n'.join([line.strip() for line in text.splitlines() if line.strip()])

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

def get_field(text, label):
    m = re.search(re.escape(label) + r"[^:]*:\s*([^\n]+)", text, re.IGNORECASE)
    if m:
        val = m.group(1).split("||")[0].strip()
        return val
    return ""

def get_raw_field(text, label):
    m = re.search(re.escape(label) + r"[^:]*:\s*([^\n]+)", text, re.IGNORECASE)
    return m.group(1).strip() if m else ""

def process_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            html = f.read()
            
        file_hash = hashlib.md5(html.encode('utf-8')).hexdigest()
        text = clean_text(html)
        
        batch_no = get_field(text, "Batch No")
        if not batch_no:
            return {"status": "invalid", "filepath": filepath}
            
        # Extract headers
        headers = {
            "Batch No": batch_no,
            "Prepare Date": get_field(text, "Prepare Date"),
            "Order No": get_field(text, "Order No"),
            "Buyer": get_field(text, "Buyer"),
            "Fabric Qty": get_field(text, "Fabric Qty"),
            "Water": get_field(text, "Water"),
            "Liquor Ratio": get_field(text, "Liquor Ratio"),
            "GSM": get_field(text, "GSM"),
            "Color Depth": get_field(text, "Color Depth"),
            "Fabric Type/Color": get_raw_field(text, "Fabric Type"),
            "Dyeing Type/Status": get_raw_field(text, "Dyeing Type"),
            "MC No": get_raw_field(text, "M/C No"),
            "Source_File": os.path.basename(filepath),
            "File_Hash": file_hash
        }
        
        lines = []
        valid_batch = True
        
        tables = parse_html_table(html)
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
                    
                if not req_qty and not amount:
                    continue
                    
                try:
                    r_val = float(str(req_qty).replace(',', ''))
                    if r_val <= 0.0: valid_batch = False
                except:
                    valid_batch = False
                    
                try:
                    a_str = str(amount).replace(',', '').strip()
                    if a_str:
                        a_val = float(a_str)
                        if a_val <= 0.0: valid_batch = False
                    else:
                        a_val = 0
                except:
                    valid_batch = False
                    
                if not valid_batch:
                    break
                    
                lines.append({
                    "Batch No": batch_no,
                    "Item_Name": nm,
                    "Req_Qty_kg": str(req_qty).replace(',', '').strip(),
                    "Amount_Tk": str(amount).replace(',', '').strip()
                })
            
            if not valid_batch:
                break
                
        if not lines or not valid_batch:
            return {"status": "zero_cost_or_empty", "filepath": filepath}
            
        return {
            "status": "success",
            "headers": headers,
            "lines": lines,
            "filepath": filepath
        }
    except Exception as e:
        return {"status": "error", "filepath": filepath}

def init_db():
    if not os.path.exists(OUT_DIR):
        os.makedirs(OUT_DIR)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS processed_files (filepath TEXT PRIMARY KEY, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS headers (
        Batch_No TEXT, Prepare_Date TEXT, Order_No TEXT, Buyer TEXT, 
        Fabric_Qty TEXT, Water TEXT, Liquor_Ratio TEXT, GSM TEXT, 
        Color_Depth TEXT, Fabric_Type TEXT, Dyeing_Type TEXT, MC_No TEXT, 
        Source_File TEXT, File_Hash TEXT, Lines_Count INTEGER
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS lines (
        Batch_No TEXT, Item_Name TEXT, Req_Qty_kg TEXT, Amount_Tk TEXT, Source_File TEXT
    )''')
    conn.commit()
    return conn

if __name__ == "__main__":
    conn = init_db()
    c = conn.cursor()
    
    # Load already processed files
    c.execute("SELECT filepath FROM processed_files")
    already_processed = set([row[0] for row in c.fetchall()])
    print("Found {:,} already processed files in the checkpoint DB.".format(len(already_processed)))

    print("Scanning directory for HTML files...")
    all_html_files = []
    for root, dirs, files in os.walk(BASE_DIR):
        if "2026_Data_Science_Rigorous_Analysis" in root or ".obsidian" in root:
            continue
        for f in files:
            if f.endswith('.html'):
                fp = os.path.join(root, f)
                if fp not in already_processed:
                    all_html_files.append(fp)
                
    print("Remaining files to process: {:,}".format(len(all_html_files)))
    
    if len(all_html_files) > 0:
        print("Launching Resumable Universal Extraction across {} cores...".format(multiprocessing.cpu_count()))
        
        batch_size = 5000
        processed_count = 0
        
        with ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
            futures = {executor.submit(process_file, fp): fp for fp in all_html_files}
            
            for future in as_completed(futures):
                res = future.result()
                fp = res["filepath"]
                status = res["status"]
                
                c.execute("INSERT OR REPLACE INTO processed_files (filepath, status) VALUES (?, ?)", (fp, status))
                
                if status == "success":
                    h = res["headers"]
                    lines_count = len(res["lines"])
                    # For performance in SQLite, we just insert all successes for now, and we will deduplicate in the final export
                    c.execute('''INSERT INTO headers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                        (h["Batch No"], h["Prepare Date"], h["Order No"], h["Buyer"], 
                         h["Fabric Qty"], h["Water"], h["Liquor Ratio"], h["GSM"], 
                         h["Color Depth"], h["Fabric Type/Color"], h["Dyeing Type/Status"], h["MC No"], 
                         h["Source_File"], h["File_Hash"], lines_count))
                         
                    for line in res["lines"]:
                        c.execute('''INSERT INTO lines VALUES (?, ?, ?, ?, ?)''',
                            (line["Batch No"], line["Item_Name"], line["Req_Qty_kg"], line["Amount_Tk"], h["Source_File"]))
                            
                processed_count += 1
                if processed_count % batch_size == 0:
                    conn.commit()
                    print("Processed {:,}/{:,} remaining files...".format(processed_count, len(all_html_files)))
                    
            conn.commit()
            
    print("\nExtraction Complete! Deduplicating and exporting to CSV...")
    import csv
    
    # Deduplicate Hash and keep batch with max lines
    c.execute('''
        SELECT Batch_No, Prepare_Date, Order_No, Buyer, Fabric_Qty, Water, Liquor_Ratio, GSM, 
        Color_Depth, Fabric_Type, Dyeing_Type, MC_No, Source_File, MAX(Lines_Count) 
        FROM headers 
        GROUP BY Batch_No
    ''')
    best_headers = c.fetchall()
    
    valid_source_files = set([row[12] for row in best_headers])
    
    with open(HEADER_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Batch No", "Prepare Date", "Order No", "Buyer", "Fabric Qty", "Water", "Liquor Ratio", "GSM", "Color Depth", "Fabric Type/Color", "Dyeing Type/Status", "MC No", "Source_File"])
        for row in best_headers:
            writer.writerow(row[:-1]) # exclude Lines_Count
            
    c.execute("SELECT Batch_No, Item_Name, Req_Qty_kg, Amount_Tk, Source_File FROM lines")
    all_lines = c.fetchall()
    
    with open(LINES_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Batch No", "Item_Name", "Req_Qty_kg", "Amount_Tk"])
        for row in all_lines:
            if row[4] in valid_source_files:
                writer.writerow(row[:-1])
                
    conn.close()
    print("Export Complete! Saved perfectly un-biased dataset to Universal_Headers.csv and Universal_Lines.csv.")
