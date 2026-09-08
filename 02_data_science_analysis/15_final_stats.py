import sqlite3
import os

DB_PATH = r"E:\Downloads\01_Projects_and_Research\AI-driven closed-loop dyeing system for Bangladesh textiles\2026_Data_Science_Rigorous_Analysis\extraction_checkpoint.db"

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

c.execute("SELECT COUNT(DISTINCT Batch_No) FROM headers")
total_unique = c.fetchone()[0]

c.execute("SELECT COUNT(DISTINCT Batch_No) FROM headers WHERE Batch_No LIKE 'Unit_A%'")
Unit_A_count = c.fetchone()[0]

c.execute("SELECT COUNT(DISTINCT Batch_No) FROM headers WHERE Batch_No LIKE 'Unit_C%'")
Unit_C_count = c.fetchone()[0]

c.execute("SELECT COUNT(DISTINCT Batch_No) FROM headers WHERE Batch_No LIKE 'Unit_D%'")
Unit_D_count = c.fetchone()[0]

other = total_unique - (Unit_A_count + Unit_C_count + Unit_D_count)

print("Total Final Unique Batches: {}".format(total_unique))
print("Unit_A: {} ({:.2f}%)".format(Unit_A_count, (Unit_A_count/total_unique)*100 if total_unique else 0))
print("Unit_C: {} ({:.2f}%)".format(Unit_C_count, (Unit_C_count/total_unique)*100 if total_unique else 0))
print("Unit_D: {} ({:.2f}%)".format(Unit_D_count, (Unit_D_count/total_unique)*100 if total_unique else 0))
print("Other: {} ({:.2f}%)".format(other, (other/total_unique)*100 if total_unique else 0))

conn.close()


