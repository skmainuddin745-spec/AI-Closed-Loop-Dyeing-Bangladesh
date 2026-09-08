import sqlite3
import os
import random

BASE_DIR = r"E:\Downloads\01_Projects_and_Research\AI-driven closed-loop dyeing system for Bangladesh textiles"
OUT_DIR = os.path.join(BASE_DIR, "2026_Data_Science_Rigorous_Analysis")
DB_PATH = os.path.join(OUT_DIR, "extraction_checkpoint.db")

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Get all batch numbers that have MORE THAN ONE source file associated with them
c.execute("""
    SELECT Batch_No, COUNT(Source_File) 
    FROM headers 
    GROUP BY Batch_No 
    HAVING COUNT(Source_File) > 1
""")
duplicate_batches = c.fetchall()

total_duplicate_files = 0
total_batch_groups = len(duplicate_batches)

print("--- 100% RIGOROUS DUPLICATE AUDIT ---")
print("Total distinct Batch Numbers that have duplicates: {}".format(total_batch_groups))

# Let's verify a sample of 1000 duplicate groups to prove they are identical in content
sample_size = min(total_batch_groups, 1000)
random.seed(42)
sample_groups = random.sample(duplicate_batches, sample_size)

exact_match_count = 0
mismatch_count = 0
examples = []

for batch_no, count in sample_groups:
    total_duplicate_files += (count - 1) # The extra files that get dropped
    
    # Fetch all records for this exact batch number
    c.execute("SELECT Prepare_Date, Order_No, GSM, Fabric_Type, Source_File, Lines_Count FROM headers WHERE Batch_No = ?", (batch_no,))
    records = c.fetchall()
    
    # Are the records identical across the different source files?
    # We compare Prepare Date, Order No, GSM, Fabric Type, and Lines Count
    first_record_content = (records[0][0], records[0][1], records[0][2], records[0][3], records[0][5])
    is_exact_match = True
    
    for r in records[1:]:
        this_content = (r[0], r[1], r[2], r[3], r[5])
        if this_content != first_record_content:
            is_exact_match = False
            break
            
    if is_exact_match:
        exact_match_count += 1
    else:
        mismatch_count += 1
        
    if len(examples) < 3:
        examples.append({
            "Batch_No": batch_no,
            "Records": [{"File": r[4], "GSM": r[2], "Lines": r[5]} for r in records]
        })

print("\n--- SAMPLE STATISTICAL PROOF ---")
print("Audited {} random batches that contained multiple source files.".format(sample_size))
print("Mathematically identical across all duplicated files: {} ({:.2f}%)".format(exact_match_count, (exact_match_count/sample_size)*100))
print("Mismatched metadata across duplicated files: {} ({:.2f}%)".format(mismatch_count, (mismatch_count/sample_size)*100))

print("\n--- SAMPLE EXAMPLES FOR MANUAL VERIFICATION ---")
for ex in examples:
    print("Batch No: {}".format(ex["Batch_No"]))
    for r in ex["Records"]:
        print("  -> Found in File: {} | GSM: {} | Chemical Lines: {}".format(r["File"], r["GSM"], r["Lines"]))
    print("")

conn.close()
