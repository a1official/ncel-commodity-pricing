import sqlite3

conn = sqlite3.connect('d:/ncel/backend/ncel_local.db')
cursor = conn.cursor()
cursor.execute("SELECT date, COUNT(*) FROM price_records GROUP BY date ORDER BY date DESC")
rows = cursor.fetchall()
print("Record counts per date:")
for row in rows:
    print(row)
conn.close()
