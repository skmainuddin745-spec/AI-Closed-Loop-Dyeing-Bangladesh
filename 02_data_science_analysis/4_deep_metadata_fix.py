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
    except Exception as e:
        return {"filepath": filepath, "status": "error"}

    text = clean_text(html)
    
    # Robust extraction for Fabric and Depth
    fabric = ""
    depth = ""
    
    m_fab = re.search(r"Fabric Type[^:]*:\s*([^\n]+)", text, re.IGNORECASE)
    if m_fab: 
        fabric = m_fab.group(1).strip()
        
    m_dep = re.search(r"Color Depth[^:]*:\s*([^\n]+)", text, re.IGNORECASE)
    if m_dep: 
        depth = m_dep.group(1).strip()
        
    return {"filepath": filepath, "fabric": fabric, "depth": depth, "status": "success"}

if __name__ == "__main__":
    print("Loading Header file to identify 47,403 verified batches...")
    
    headers = []
    target_files = set()
    with open(HEADER_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            headers.append(row)
            target_files.add(row["Source_File"])
            
    print("Found {} unique target basenames. Scanning disk...".format(len(target_files)))
    
    abs_paths = {}
    for root, dirs, files in os.walk(BASE_DIR):
        if "2026_Data_Science_Rigorous_Analysis" in root or ".obsidian" in root:
            continue
        for f in files:
            if f in target_files:
                abs_paths[f] = os.path.join(root, f)
                
    print("Matched {} absolute paths for re-extraction.".format(len(abs_paths)))
    
    paths_to_process = list(abs_paths.values())
    updates = {}
    
    print("Extracting detailed metadata across {} cores...".format(multiprocessing.cpu_count()))
    
    with ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
        futures = {executor.submit(parse_metadata, fp): fp for fp in paths_to_process}
        processed = 0
        for future in as_completed(futures):
            processed += 1
            if processed % 5000 == 0:
                print("Extracted {}/{}...".format(processed, len(paths_to_process)))
            res = future.result()
            if res["status"] == "success":
                updates[os.path.basename(res["filepath"])] = {"fabric": res["fabric"], "depth": res["depth"]}
                
    print("Applying updates to headers...")
    updated_count = 0
    for row in headers:
        sf = row["Source_File"]
        if sf in updates:
            row["Fabric Type/Color"] = updates[sf]["fabric"]
            row["Color Depth"] = updates[sf]["depth"]
            updated_count += 1
            
    print("Successfully updated {} rows. Saving to disk...".format(updated_count))
    
    with open(HEADER_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(headers[0].keys()))
        writer.writeheader()
        writer.writerows(headers)
        
    print("Metadata Fix Complete! Overwritten Updated_AI_dataset_2021-2026_Headers.csv.")
