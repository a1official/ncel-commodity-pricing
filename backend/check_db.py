import sqlite3
import os

db_path = 'ncel_local.db'
if not os.path.exists(db_path):
    print(f"Error: {db_path} not found")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print(f"Tables: {tables}")

for table_tuple in tables:
    table = table_tuple[0]
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    print(f"Table {table}: {count} records")

# Sample from market table if exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name='market' OR name='markets')")
market_table = cursor.fetchone()
if market_table:
    table_name = market_table[0]
    cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
    print(f"\nSample from {table_name}:")
    for row in cursor.fetchall():
        print(row)
else:
    print("\nNo market table found.")

conn.close()
