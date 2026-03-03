import requests
import json

try:
    response = requests.get("http://localhost:8000/api/v1/prices")
    data = response.json()
    if data:
        print(f"Latest price record date: {data[0].get('date')}")
        print(f"Total records returned: {len(data)}")
    else:
        print("No price records returned.")
except Exception as e:
    print(f"Error fetching prices: {e}")
