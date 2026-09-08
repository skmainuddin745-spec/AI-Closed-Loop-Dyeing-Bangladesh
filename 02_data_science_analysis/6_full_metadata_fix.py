import os
import csv
import re
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing

BASE_DIR = r"E:\Downloads\01_Projects_and_Research\AI-driven closed-loop dyeing system for Bangladesh textiles"
OUT_DIR = os.path.join(BASE_DIR, "2026_Data_Science_Rigorous_Analysis")
HEADER_FILE = os.path.join(OUT_DIR, "Updated_AI_dataset_2021-2026_Headers.csv")

tag_re = re.compile(r'<[^>]+>')

def clean_text(html):
    text = tag_re.sub('\n', html)
    return '\n'.join([line.strip() for line in text.splitlines() if line.strip()])

def parse_metadata(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            html = f.read()
    except:
        return {"filepath": filepath, "status": "error"}

    text = clean_text(html)
    mc = ""
    dye = ""
    
    m_mc = re.search(r"M/C No[^:]*:\s*([^\n]+)", text, re.IGNORECASE)
    if m_mc: mc = m_mc.group(1).strip()
        
    m_dye = re.search(r"Dyeing Type[^:]*:\s*([^\n]+)", text, re.IGNORECASE)
    if m_dye: dye = m_dye.group(1).strip()
        
    return {"filepath": filepath, "mc": mc, "dye": dye, "status": "success"}

if __name__ == "__main__":
    headers = []
    target_files = set()
    with open(HEADER_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            headers.append(row)
            target_files.add(row["Source_File"])
            
    abs_paths = {}
    for root, dirs, files in os.walk(BASE_DIR):
        if "2026_Data_Science_Rigorous_Analysis" in root or ".obsidian" in root:
            continue
        for f in files:
            if f in target_files:
                abs_paths[f] = os.path.join(root, f)
                
    paths_to_process = list(abs_paths.values())
    updates = {}
    
    with ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
        futures = {executor.submit(parse_metadata, fp): fp for fp in paths_to_process}
        for future in as_completed(futures):
            res = future.result()
            if res["status"] == "success":
                updates[os.path.basename(res["filepath"])] = {"mc": res["mc"], "dye": res["dye"]}
                
    for row in headers:
        sf = row["Source_File"]
        if sf in updates:
            row["MC No"] = updates[sf]["mc"]
            row["Dyeing Type/Status"] = updates[sf]["dye"]
            
    with open(HEADER_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(headers[0].keys()))
        writer.writeheader()
        writer.writerows(headers)
        
    print("Full Metadata Fix Complete!")
