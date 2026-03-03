import sqlite3
import json

conn = sqlite3.connect('d:/ncel/backend/ncel_local.db')
cursor = conn.cursor()
cursor.execute("SELECT date, modal_price FROM price_records ORDER BY date DESC LIMIT 10")
rows = cursor.fetchall()
print("Top 10 records by date DESC:")
for row in rows:
    print(row)
conn.close()
