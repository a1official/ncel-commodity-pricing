from app.core.database import SessionLocal
from app.models import models
from datetime import datetime, timedelta
import random

def inject_marine_data():
    db = SessionLocal()
    
    # 1. Ensure Marine Products category (already done by setup script but harmless)
    shrimp = db.query(models.Commodity).filter_by(name='Shrimp').first()
    if not shrimp:
        shrimp = models.Commodity(name='Shrimp', category='Marine Products')
        db.add(shrimp)
        db.flush()
    else:
        shrimp.category = 'Marine Products'
        db.commit()

    species = ['Shrimp', 'Mackerel', 'Tuna', 'Trout', 'Pomfret', 'Squid', 'Lobster', 'Crab', 'Sardine']
    commodity_objs = {}
    for s in species:
        c = db.query(models.Commodity).filter_by(name=s).first()
        if not c:
            c = models.Commodity(name=s, category='Marine Products')
            db.add(c)
            db.flush()
        else:
            c.category = 'Marine Products'
        commodity_objs[s] = c
    
    db.commit()

    # 2. Ensure FMPIS source
    fmpis = db.query(models.Source).filter_by(name='FMPIS').first()
    if not fmpis:
        fmpis = models.Source(name='FMPIS', source_type='Government')
        db.add(fmpis)
        db.flush()
    db.commit()

    # 3. Create Varieties
    varieties = ['Small', 'Medium', 'Large', 'Export Grade']
    variety_objs = {}
    for s in species:
        variety_objs[s] = []
        for v_name in varieties:
            v = db.query(models.Variety).filter_by(commodity_id=commodity_objs[s].id, name=v_name).first()
            if not v:
                v = models.Variety(commodity_id=commodity_objs[s].id, name=v_name)
                db.add(v)
                db.flush()
            variety_objs[s].append(v)
    db.commit()

    # 4. Coastal States and dummy markets
    coastal = ['Andhra Pradesh', 'Goa', 'Gujarat', 'Karnataka', 'Kerala', 'Maharashtra', 'Odisha', 'Tamil Nadu', 'West Bengal']
    for s_name in coastal:
        state = db.query(models.State).filter_by(name=s_name).first()
        if not state:
            state = models.State(name=s_name)
            db.add(state)
            db.flush()
        
        district = db.query(models.District).filter_by(state_id=state.id, name='Coastal District').first()
        if not district:
            district = models.District(state_id=state.id, name='Coastal District')
            db.add(district)
            db.flush()
            
        market = db.query(models.Market).filter_by(district_id=district.id, name=f'{s_name} Marine Hub').first()
        if not market:
            market = models.Market(district_id=district.id, name=f'{s_name} Marine Hub')
            db.add(market)
            db.flush()
        
        # Inject prices for last 7 days
        for i in range(7):
            date = datetime.now() - timedelta(days=i)
            for s_name in species:
                for v in variety_objs[s_name]:
                    price = random.uniform(200, 800)
                    pr = models.PriceRecord(
                        date=date,
                        commodity_id=commodity_objs[s_name].id,
                        variety_id=v.id,
                        market_id=market.id,
                        source_id=fmpis.id,
                        min_price=price * 0.9,
                        max_price=price * 1.1,
                        modal_price=price,
                        arrival_quantity=random.uniform(50, 500),
                        unit='Kg',
                        normalized_price_per_kg=price
                    )
                    db.add(pr)
        print(f"Injected data for {s_name}")
        db.commit()
    
    db.close()
    print("Injection complete!")

if __name__ == "__main__":
    inject_marine_data()
