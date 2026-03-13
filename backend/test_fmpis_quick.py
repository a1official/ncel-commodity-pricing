import requests
import time
from datetime import datetime

def test_fmpis_single():
    api_url = "https://fmpisnfdb.in/prices/pricefilter"
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': 'https://fmpisnfdb.in/prices',
        'Origin': 'https://fmpisnfdb.in',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
    })
    
    print("Connecting to FMPIS...")
    try:
        session.get("https://fmpisnfdb.in/prices", timeout=10)
        print("Session established.")
        
        # Maharashtra
        params = {"serachbystate": 6, "searchBymarket": 691}
        print(f"Fetching Maharashtra data...")
        response = session.post(api_url, data=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            if 'aaData' in data:
                print(f"Success! Found {len(data['aaData'])} records.")
                for record in data['aaData'][:2]:
                    print(f"Species: {record.get('sepeciesname')}, Price: {record.get('medium')}")
            else:
                print("No data in response.")
        else:
            print(f"Error: {response.status_code}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_fmpis_single()
