import os
import re
import csv
import hashlib
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
import traceback

BASE_DIR = r"E:\Downloads\01_Projects_and_Research\AI-driven closed-loop dyeing system for Bangladesh textiles"
OUT_DIR = os.path.join(BASE_DIR, "2026_Data_Science_Rigorous_Analysis")
HEADER_CSV = os.path.join(OUT_DIR, "Universal_Headers.csv")
LINES_CSV = os.path.join(OUT_DIR, "Universal_Lines.csv")

tag_re = re.compile(r'<[^>]+>')

def clean_text(html):
    text = tag_re.sub('\n', html)
    return '\n'.join([line.strip() for line in text.splitlines() if line.strip()])

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
            return {"status": "invalid"}
            
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
            "MC No": get_raw_field(text, "M/C No")
        }
        
        # Chemical Lines extraction
        lines = []
        is_in_table = False
        valid_batch = True
        
        for line in text.splitlines():
            line = line.strip()
            if "Total Dyes :" in line or "Total Chemical :" in line:
                is_in_table = False
                continue
                
            if "Amount(Tk)" in line or "Req. Qty" in line:
                is_in_table = True
                continue
                
            if is_in_table:
                parts = line.split('\n') if '\n' in line else re.split(r'\s{2,}', line)
                if len(parts) >= 8:
                    qty = parts[6].replace(',', '').strip()
                    amt = parts[7].replace(',', '').strip()
                    
                    try:
                        q_val = float(qty)
                        a_val = float(amt)
                    except:
                        q_val = 0
                        a_val = 0
                        
                    if q_val <= 0 or a_val <= 0:
                        valid_batch = False
                        break
                        
                    lines.append({
                        "Batch No": batch_no,
                        "Item_Name": parts[2].strip(),
                        "Req_Qty_kg": qty,
                        "Amount_Tk": amt
                    })
                    
        if not lines or not valid_batch:
            return {"status": "zero_cost_or_empty"}
            
        return {
            "status": "success",
            "hash": file_hash,
            "headers": headers,
            "lines": lines,
            "filepath": filepath
        }
    except Exception as e:
        return {"status": "error"}

if __name__ == "__main__":
    if not os.path.exists(OUT_DIR):
        os.makedirs(OUT_DIR)
        
    print("Scanning entire directory for ALL .html files (ignoring prefix rules)...")
    all_html_files = []
    for root, dirs, files in os.walk(BASE_DIR):
        if "2026_Data_Science_Rigorous_Analysis" in root or ".obsidian" in root:
            continue
        for f in files:
            if f.endswith('.html'):
                all_html_files.append(os.path.join(root, f))
                
    print("Found {:,} absolute HTML files across the drive.".format(len(all_html_files)))
    
    unique_hashes = set()
    best_batches = {}
    
    stats = {
        "processed": 0,
        "duplicate_hash": 0,
        "zero_cost_dropped": 0,
        "invalid": 0,
        "errors": 0
    }
    
    print("Launching Universal Extraction across {} cores...".format(multiprocessing.cpu_count()))
    
    with ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
        futures = {executor.submit(process_file, fp): fp for fp in all_html_files}
        
        for future in as_completed(futures):
            stats["processed"] += 1
            if stats["processed"] % 10000 == 0:
                print("Processed {:,}/{:,} files...".format(stats["processed"], len(all_html_files)))
                
            res = future.result()
            
            if res["status"] == "error":
                stats["errors"] += 1
            elif res["status"] == "invalid":
                stats["invalid"] += 1
            elif res["status"] == "zero_cost_or_empty":
                stats["zero_cost_dropped"] += 1
            elif res["status"] == "success":
                f_hash = res["hash"]
                if f_hash in unique_hashes:
                    stats["duplicate_hash"] += 1
                    continue
                unique_hashes.add(f_hash)
                
                b_no = res["headers"]["Batch No"]
                # Keep batch with the highest number of valid chemical lines (most complete)
                if b_no not in best_batches or len(res["lines"]) > len(best_batches[b_no]["lines"]):
                    best_batches[b_no] = res
                    
    print("\nExtraction Complete! Resolving final metrics:")
    final_headers = []
    final_lines = []
    
    for b_no, data in best_batches.items():
        data["headers"]["Source_File"] = os.path.basename(data["filepath"])
        final_headers.append(data["headers"])
        final_lines.extend(data["lines"])
        
    print("Total Unique Mathematical Batches: {:,}".format(len(final_headers)))
    print("Total Extracted Chemical Line Items: {:,}".format(len(final_lines)))
    print("Zero-Cost Batches Algorithmicly Dropped: {:,}".format(stats["zero_cost_dropped"]))
    
    # Save datasets
    print("Saving to CSVs...")
    if final_headers:
        with open(HEADER_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(final_headers[0].keys()))
            writer.writeheader()
            writer.writerows(final_headers)
            
    if final_lines:
        with open(LINES_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(final_lines[0].keys()))
            writer.writeheader()
            writer.writerows(final_lines)
            
    print("Universal Dataset compilation 100% complete!")
