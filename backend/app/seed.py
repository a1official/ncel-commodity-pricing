from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from app.models.models import Base, Commodity, Variety, Market, State, District, Source, PriceRecord
from app.core.config import settings
from datetime import date, timedelta
import random

def seed_db():
    engine = create_engine(settings.get_database_url)
    # Drop and recreate for a clean state with new requested data
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    with Session(engine) as session:
        print("Seeding database with expanded commodity list...")
        
        # Sources
        sources = [
            Source(name="Agmarknet", source_type="Government"),
            Source(name="NFDB", source_type="Government"),
            Source(name="NCEL Intelligence Hub", source_type="Internal")
        ]
        session.add_all(sources)
        session.flush()

        # States & Markets with Geospatial Intelligence
        states_data = {
            "Delhi": [
                {"name": "Azadpur", "lat": 28.716, "lon": 77.175},
                {"name": "Okhla", "lat": 28.551, "lon": 77.273}
            ],
            "Maharashtra": [
                {"name": "Vashi", "lat": 19.071, "lon": 73.001},
                {"name": "Nashik", "lat": 19.997, "lon": 73.789},
                {"name": "Nagpur", "lat": 21.145, "lon": 79.088},
                {"name": "Pune", "lat": 18.520, "lon": 73.856}
            ],
            "Haryana": [
                {"name": "Karnal", "lat": 29.685, "lon": 76.990},
                {"name": "Panipat", "lat": 29.390, "lon": 76.963}
            ],
            "Gujarat": [
                {"name": "Unjha", "lat": 23.811, "lon": 72.392},
                {"name": "Gondal", "lat": 21.961, "lon": 70.792}
            ],
            "Andhra Pradesh": [
                {"name": "Guntur", "lat": 16.306, "lon": 80.436},
                {"name": "Kurnool", "lat": 15.822, "lon": 78.035}
            ],
            "Karnataka": [
                {"name": "Bangalore", "lat": 12.971, "lon": 77.594},
                {"name": "Haveri", "lat": 14.795, "lon": 75.402}
            ],
            "Tamil Nadu": [
                {"name": "Chennai", "lat": 13.082, "lon": 80.270},
                {"name": "Kochi Port", "lat": 9.931, "lon": 76.267}
            ]
        }
        
        all_markets = []
        for state_name, districts in states_data.items():
            state = State(name=state_name)
            session.add(state)
            session.flush()
            
            for mkt_info in districts:
                # Using City as District for seeding simplicity
                district = District(name=mkt_info["name"], state_id=state.id)
                session.add(district)
                session.flush()
                
                mkt = Market(
                    name=f"{mkt_info['name']} Mandi", 
                    district_id=district.id,
                    lat=mkt_info["lat"],
                    lon=mkt_info["lon"]
                )
                session.add(mkt)
                all_markets.append(mkt)
        session.flush()

        # Expanded Commodities & Varieties based on USER request
        com_data = [
            # 1. Rice
            {"name": "Basmati Rice", "category": "Grain", "varieties": ["Pusa 1121", "1509 Basmati", "CSR 30", "Traditional"]},
            {"name": "Non-Basmati White Rice", "category": "Grain", "varieties": ["IR 64", "Sona Masuri", "PR 126", "Swarna"]},
            
            # 2. Spices
            {"name": "Cumin (Jeera)", "category": "Spices", "varieties": ["Machine Cleaned", "Europe Quality", "Singapore Quality"]},
            {"name": "Turmeric", "category": "Spices", "varieties": ["Nizamabad Finger", "Salem", "Erode", "Rajapuri"]},
            {"name": "Red Chilli", "category": "Spices", "varieties": ["Teja", "Guntur Sannam", "334", "Byadgi"]},
            
            # 3. Fruits & Vegetables
            {"name": "Grapes", "category": "Vegetable", "varieties": ["Thomson Seedless", "Tas-A-Ganesh", "Flame Seedless"]},
            {"name": "Potato", "category": "Vegetable", "varieties": ["Jyoti", "Lauvkar", "Kufri", "Pukhraj"]},
            {"name": "Banana", "category": "Vegetable", "varieties": ["Grand Naine", "Robusta", "Yelakki", "Red Banana"]},
            {"name": "Onion", "category": "Vegetable", "varieties": ["Red Onion", "White Onion", "Garwa"]},
            {"name": "Tomato", "category": "Vegetable", "varieties": ["Hybrid", "Local", "Desi"]},
            {"name": "Pineapple", "category": "Vegetable", "varieties": ["Giant Kew", "Queen", "Mauritius"]},
            
            # 4. Marine Products
            {"name": "Shrimp", "category": "Marine", "varieties": ["Vannamei (Large)", "Black Tiger", "Scampi"]},
            {"name": "Trout", "category": "Marine", "varieties": ["Rainbow Trout", "Brown Trout"]},
            {"name": "Mackerel", "category": "Marine", "varieties": ["Indian Mackerel", "King Mackerel"]},
            {"name": "Tuna", "category": "Marine", "varieties": ["Yellowfin Tuna", "Skipjack", "Bigeye"]},
            
            # 5. Millets
            {"name": "Pearl Millet (Bajra)", "category": "Grain", "varieties": ["Hybrid", "Local"]},
            {"name": "Finger Millet (Ragi)", "category": "Grain", "varieties": ["Indaf", "GPU-28"]},
            {"name": "Foxtail Millet", "category": "Grain", "varieties": ["Local"]},
            {"name": "Sorghum (Jowar)", "category": "Grain", "varieties": ["Maldandi", "Hybrid"]},
            
            # 6. Groundnut
            {"name": "Groundnut", "category": "Oilseeds", "varieties": ["Bold", "Java", "G-20", "TJ-37"]},
            
            # 7. Maize (Makka)
            {"name": "Maize (Makka)", "category": "Grain", "varieties": ["Hybrid", "Local", "Pioneer"]}
        ]
        
        all_varieties = []
        for item in com_data:
            com = Commodity(name=item["name"], category=item["category"])
            session.add(com)
            session.flush()
            
            for v_name in item["varieties"]:
                var = Variety(name=v_name, commodity_id=com.id)
                session.add(var)
                all_varieties.append(var)
        session.flush()

        # Generate price discovery records for the last 15 days
        print(f"Generating price discovery for {len(all_varieties)} varieties...")
        for var in all_varieties:
            category = var.commodity.category
            
            # Category-specific price basis (Price per KG)
            if category == "Vegetable":
                # staples like Potato/Onion/Tomato are cheaper
                if any(k in var.commodity.name.lower() for k in ["potato", "onion", "tomato"]):
                    base_price_discovery = 6.0 + random.random() * 12.0 # 6-18 per KG
                    base_arrival = 5000 + random.random() * 15000 # High volume (MT)
                else:
                    base_price_discovery = 30.0 + random.random() * 100.0 # Grapes, Pineapple etc
                    base_arrival = 500 + random.random() * 2000
            elif category == "Grain":
                base_price_discovery = 22.0 + random.random() * 45.0
                if "basmati" in var.commodity.name.lower():
                    base_price_discovery = 120.0 + random.random() * 100.0 # Premium
                base_arrival = 1000 + random.random() * 5000
            elif category == "Spices":
                base_price_discovery = 150.0 + random.random() * 400.0
                base_arrival = 100 + random.random() * 500
            elif category == "Marine":
                base_price_discovery = 300.0 + random.random() * 700.0
                base_arrival = 200 + random.random() * 800
            else:
                base_price_discovery = 40.0 + random.random() * 100.0
                base_arrival = 300 + random.random() * 1000

            num_markets = random.randint(3, 5)
            selected_markets = random.sample(all_markets, num_markets)
            
            for mkt in selected_markets:
                for i in range(15):
                    price_date = date.today() - timedelta(days=i)
                    src = sources[1] if category == "Marine" else sources[0]
                    
                    # Daily modal fluctuation (within 5%)
                    daily_modal = base_price_discovery * (1 + (random.random() * 0.1 - 0.05))
                    arrival_vol = base_arrival * (1 + (random.random() * 0.4 - 0.2)) # More fluctuation in arrivals
                    
                    pr = PriceRecord(
                        date=price_date,
                        commodity_id=var.commodity_id,
                        variety_id=var.id,
                        market_id=mkt.id,
                        source_id=src.id,
                        min_price=daily_modal * 0.85 * 100, # Per quintal
                        max_price=daily_modal * 1.15 * 100,
                        modal_price=daily_modal * 100,
                        arrival_quantity=arrival_vol,
                        unit="QUINTAL" if category != "Marine" else "KG",
                        normalized_price_per_kg=daily_modal
                    )
                    session.add(pr)
        
        session.commit()
        print(f"Intelligence seeding complete. Database now contains {len(com_data)} commodities and {len(all_varieties)} varieties.")

if __name__ == "__main__":
    seed_db()
