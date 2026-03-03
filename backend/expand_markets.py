import sqlite3

def add_markets():
    conn = sqlite3.connect('ncel_local.db')
    cursor = conn.cursor()

    # Get existing names to avoid duplicates
    cursor.execute("SELECT name FROM markets")
    existing_markets = {row[0] for row in cursor.fetchall()}

    # New markets with lat/lon for coverage
    new_markets = [
        ("Amritsar", 31.634, 74.872, "Punjab"),
        ("Ludhiana", 30.901, 75.857, "Punjab"),
        ("Lucknow", 26.846, 80.946, "Uttar Pradesh"),
        ("Varanasi", 25.317, 82.973, "Uttar Pradesh"),
        ("Patna", 25.594, 85.137, "Bihar"),
        ("Kolkata", 22.572, 88.363, "West Bengal"),
        ("Guwahati", 26.115, 91.708, "Assam"),
        ("Bhopal", 23.259, 77.412, "Madhya Pradesh"),
        ("Indore", 22.719, 75.857, "Madhya Pradesh"),
        ("Jaipur", 26.912, 75.787, "Rajasthan"),
        ("Surat", 21.170, 72.831, "Gujarat"),
        ("Ahmedabad", 23.022, 72.571, "Gujarat"),
        ("Visakhapatnam", 17.686, 83.218, "Andhra Pradesh"),
        ("Vijayawada", 16.506, 80.648, "Andhra Pradesh"),
        ("Mysore", 12.295, 76.639, "Karnataka"),
        ("Coimbatore", 11.016, 76.955, "Tamil Nadu"),
        ("Madurai", 9.925, 78.119, "Tamil Nadu"),
        ("Thiruvananthapuram", 8.524, 76.936, "Kerala"),
        ("Raipur", 21.251, 81.629, "Chhattisgarh"),
        ("Bhubaneswar", 20.296, 85.824, "Odisha")
    ]

    # Map state to state_id (assuming they exist or using a default)
    # For now, I'll just use the district_id = 1 (or any existing)
    # Actually, I should check districts table.
    cursor.execute("SELECT id FROM districts LIMIT 1")
    dist_id = cursor.fetchone()[0]

    count = 0
    for name, lat, lon, state in new_markets:
        market_name = f"{name} Mandi"
        if market_name not in existing_markets:
            cursor.execute(
                "INSERT INTO markets (name, district_id, lat, lon) VALUES (?, ?, ?, ?)",
                (market_name, dist_id, lat, lon)
            )
            count += 1

    conn.commit()
    conn.close()
    print(f"Added {count} new markets.")

if __name__ == "__main__":
    add_markets()
