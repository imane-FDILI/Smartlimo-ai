from app.database import SessionLocal
from app.models import Vehicle

FLEET = [
    {"name": "Sedan", "capacity": 3, "luggage": 3, "price_per_km": 2.5},
    {"name": "Executive SUV", "capacity": 6, "luggage": 6, "price_per_km": 3.5},
    {"name": "Premium SUV", "capacity": 6, "luggage": 8, "price_per_km": 4.0},
    {"name": "Transit VAN", "capacity": 14, "luggage": 14, "price_per_km": 4.5},
    {"name": "Sprinter VAN", "capacity": 11, "luggage": 12, "price_per_km": 5.0},
]

def seed():
    db = SessionLocal()
    try:
        for v in FLEET:
            existing = db.query(Vehicle).filter(Vehicle.name == v["name"]).first()
            if not existing:
                db.add(Vehicle(**v))
        db.commit()
        print("Flotte inseree :", db.query(Vehicle).count(), "vehicules")
    finally:
        db.close()

if __name__ == "__main__":
    seed()