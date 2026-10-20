import sqlite3
import os

db_path = r'C:\Users\z005b8nt\Downloads\Digitization-of-Disease-Pathways-main (1)-20260724T044225Z-1-001\Digitization-of-Disease-Pathways-main (1)\disease_pathway.db'
if not os.path.exists(db_path):
    print("Path does not exist!")
else:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    # Delete 'test' pain point and any others that are obviously fake
    cur.execute("DELETE FROM pain_points WHERE description = 'test' OR description = 'test2' OR description = 'test 3'")
    print(f"Deleted {cur.rowcount} fake pain points")
    
    conn.commit()
    conn.close()
