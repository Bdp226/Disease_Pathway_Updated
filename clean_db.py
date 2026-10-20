import sqlite3

def clean_db():
    conn = sqlite3.connect('disease_pathway.db')
    cur = conn.cursor()
    cur.execute("DELETE FROM pain_points WHERE description LIKE '%test%' OR description = 'test' OR description LIKE 'test%'")
    print(f"Deleted {cur.rowcount} fake pain points")
    conn.commit()
    conn.close()

if __name__ == '__main__':
    clean_db()
