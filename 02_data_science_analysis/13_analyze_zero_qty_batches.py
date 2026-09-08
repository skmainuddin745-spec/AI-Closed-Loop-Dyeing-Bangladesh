import sqlite3
import os
import re
import random

BASE_DIR = r"E:\Downloads\01_Projects_and_Research\AI-driven closed-loop dyeing system for Bangladesh textiles"
OUT_DIR = os.path.join(BASE_DIR, "2026_Data_Science_Rigorous_Analysis")
DB_PATH = os.path.join(OUT_DIR, "extraction_checkpoint.db")

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Get valid batches to check for uniqueness
c.execute("SELECT DISTINCT Batch_No FROM headers")
valid_batches = set(row[0] for row in c.fetchall() if row[0])

# Get dropped files that were 'zero_cost_or_empty' (which represents the 75.5%)
c.execute("SELECT filepath FROM processed_files WHERE status='zero_cost_or_empty'")
dropped_files = [row[0] for row in c.fetchall()]

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

# Analyze a robust random sample of 2,000 files to give highly accurate statistical representations
sample_size = min(len(dropped_files), 2000)
random.seed(42)
sample_files = random.sample(dropped_files, sample_size)

stats = {
    'total_analyzed': sample_size,
    'unique_to_dropped': 0, # not in valid dataset
    'duplicate_of_valid': 0, # already in valid dataset
    'Unit_A_count': 0,
    'Unit_C_count': 0,
    'Unit_D_count': 0,
    'other_count': 0,
    'has_gsm': 0,
    'has_fabric_type': 0,
    'samples': []
}

unique_batch_tracker = set()

for i, filepath in enumerate(sample_files):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            html = f.read()
    except:
        continue
        
    text = clean_text(html)
    batch_no = get_field(text, "Batch No")
    gsm = get_field(text, "GSM")
    fabric_type = get_raw_field(text, "Fabric Type")
    
    if not batch_no:
        continue
        
    # Uniqueness check
    if batch_no in valid_batches:
        stats['duplicate_of_valid'] += 1
    else:
        # It's unique relative to the valid dataset. Is it unique within the dropped dataset?
        if batch_no not in unique_batch_tracker:
            stats['unique_to_dropped'] += 1
            unique_batch_tracker.add(batch_no)
            
            # Count prefixes only for truly unique batches
            if batch_no.startswith('Unit_A'): stats['Unit_A_count'] += 1
            elif batch_no.startswith('Unit_C'): stats['Unit_C_count'] += 1
            elif batch_no.startswith('Unit_D'): stats['Unit_D_count'] += 1
            else: stats['other_count'] += 1
            
            # Check metadata presence
            if gsm and gsm.strip() and gsm.lower() != 'nan':
                stats['has_gsm'] += 1
            if fabric_type and fabric_type.strip() and fabric_type.lower() != 'nan':
                stats['has_fabric_type'] += 1
                
            # Collect 5 random unique samples
            if len(stats['samples']) < 5:
                stats['samples'].append({
                    'file': os.path.basename(filepath),
                    'batch': batch_no,
                    'gsm': gsm,
                    'fabric': fabric_type
                })

print("--- RIGOROUS ANALYSIS OF 75.50% (ZERO QTY) SUBSET ---")
print("Analyzed Sample Size: {}".format(stats['total_analyzed']))
print("Actually Unique Batches (Not in final dataset & distinct): {} ({:.2f}%)".format(
    stats['unique_to_dropped'], (stats['unique_to_dropped']/stats['total_analyzed'])*100))
print("Duplicates of Valid Dataset: {} ({:.2f}%)".format(
    stats['duplicate_of_valid'], (stats['duplicate_of_valid']/stats['total_analyzed'])*100))

if stats['unique_to_dropped'] > 0:
    print("\n--- PREFIX BREAKDOWN OF UNIQUE DROPPED BATCHES ---")
    print("Unit_A: {:.2f}%".format((stats['Unit_A_count'] / stats['unique_to_dropped']) * 100))
    print("Unit_C: {:.2f}%".format((stats['Unit_C_count'] / stats['unique_to_dropped']) * 100))
    print("Unit_D: {:.2f}%".format((stats['Unit_D_count'] / stats['unique_to_dropped']) * 100))
    print("Other: {:.2f}%".format((stats['other_count'] / stats['unique_to_dropped']) * 100))

    print("\n--- METADATA INTEGRITY OF UNIQUE DROPPED BATCHES ---")
    print("Has GSM mentioned: {:.2f}%".format((stats['has_gsm'] / stats['unique_to_dropped']) * 100))
    print("Has Fabric Type mentioned: {:.2f}%".format((stats['has_fabric_type'] / stats['unique_to_dropped']) * 100))

    print("\n--- SAMPLES FOR MANUAL VERIFICATION ---")
    for s in stats['samples']:
        print("File: {} | Batch: {} | GSM: {} | Fabric: {}".format(s['file'], s['batch'], s['gsm'], s['fabric']))

conn.close()


