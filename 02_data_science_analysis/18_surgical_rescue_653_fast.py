import sqlite3
import os
import re
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing

BASE_DIR = r"E:\Downloads\01_Projects_and_Research\AI-driven closed-loop dyeing system for Bangladesh textiles"
OUT_DIR = os.path.join(BASE_DIR, "2026_Data_Science_Rigorous_Analysis")
DB_PATH = os.path.join(OUT_DIR, "extraction_checkpoint.db")

tag_re = re.compile(r'<[^>]+>')
def clean_text(html):
    text = tag_re.sub('\n', html)
    return '\n'.join([line.strip() for line in text.splitlines() if line.strip()])

def get_field(text, label):
    m = re.search(re.escape(label) + r"[^:]*:\s*([^\n]+)", text, re.IGNORECASE)
    if m: return m.group(1).split("||")[0].strip()
    return ""

def get_raw_field(text, label):
    m = re.search(re.escape(label) + r"[^:]*:\s*([^\n]+)", text, re.IGNORECASE)
    return m.group(1).strip() if m else ""

def aggressive_float(s):
    cleaned = re.sub(r'[^\d.]', '', str(s))
    try:
        return float(cleaned)
    except:
        return 0.0

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
            if cells: rows.append(cells)
                
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


def process_surgical(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            html = f.read()
            
        tables = parse_html_table(html)
        if not tables: return {"status": "skip", "filepath": filepath}
        
        import hashlib
        file_hash = hashlib.md5(html.encode('utf-8')).hexdigest()
        text = clean_text(html)
        
        batch_no = get_field(text, "Batch No")
        if not batch_no: return {"status": "skip", "filepath": filepath}
        
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
                    
                r_val = aggressive_float(req_qty)
                a_val = aggressive_float(amount)
                
                if r_val > 0.0 or a_val > 0.0:
                    lines.append({
                        "Batch No": batch_no,
                        "Item_Name": nm,
                        "Req_Qty_kg": str(r_val),
                        "Amount_Tk": str(a_val)
                    })
                    
        if lines:
            return {"status": "success", "filepath": filepath, "headers": headers, "lines": lines}
            
        return {"status": "skip", "filepath": filepath}
    except Exception as e:
        return {"status": "error", "filepath": filepath}

if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("SELECT filepath FROM processed_files WHERE status != 'success'")
    dropped_files = [row[0] for row in c.fetchall()]
    
    print("Initiating MULTI-CORE Surgical Rescue on {} files...".format(len(dropped_files)))
    
    rescued = 0
    processed = 0
    
    with ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
        futures = {executor.submit(process_surgical, fp): fp for fp in dropped_files}
        
        for future in as_completed(futures):
            res = future.result()
            processed += 1
            
            if res["status"] == "success":
                rescued += 1
                c.execute("UPDATE processed_files SET status='success' WHERE filepath=?", (res["filepath"],))
                h = res["headers"]
                lines_count = len(res["lines"])
                c.execute('''INSERT INTO headers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                    (h["Batch No"], h["Prepare Date"], h["Order No"], h["Buyer"], 
                     h["Fabric Qty"], h["Water"], h["Liquor Ratio"], h["GSM"], 
                     h["Color Depth"], h["Fabric Type/Color"], h["Dyeing Type/Status"], h["MC No"], 
                     h["Source_File"], h["File_Hash"], lines_count))
                     
                for line in res["lines"]:
                    c.execute('''INSERT INTO lines VALUES (?, ?, ?, ?, ?)''',
                        (line["Batch No"], line["Item_Name"], line["Req_Qty_kg"], line["Amount_Tk"], h["Source_File"]))
                        
            if processed % 5000 == 0:
                conn.commit()
                print("Processed {} / {} files. Rescued: {}".format(processed, len(dropped_files), rescued))
                
    conn.commit()
    print("\nSurgical Rescue Complete! Forcibly extracted {} batches!".format(rescued))
    conn.close()
