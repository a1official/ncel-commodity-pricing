import sqlite3
from datetime import datetime

conn = sqlite3.connect('d:/ncel/backend/ncel_local.db')
cursor = conn.cursor()
cursor.execute("SELECT MAX(date) FROM price_records")
max_date = cursor.fetchone()[0]
print(f"Latest record date: {max_date}")
conn.close()
